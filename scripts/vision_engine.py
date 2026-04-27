import os
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

import cv2
import numpy as np
import pytesseract
from ultralytics import YOLO

from recognition.models import AccessPermit, BlackList, Camera, DetectedPlate, Vehicle


class PlateRecognizer:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    @staticmethod
    def order_points(pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    @staticmethod
    def correct_plate_text(text):
        text = text.upper()

        replacements = {
            "О": "O",
            "А": "A",
            "В": "B",
            "Е": "E",
            "Н": "H",
            "К": "K",
            "М": "M",
            "Р": "P",
            "С": "C",
            "Т": "T",
            "Х": "X",
            "І": "I",
            "Ї": "I",
            "Й": "I",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)

        text = re.sub(r"[^A-Z0-9]", "", text)
        pattern_search = re.search(r"[A-Z]{2}\d{4}[A-Z]{2}", text)
        if pattern_search:
            print(f"[FIX] Знайдено шаблон всередині шуму: {pattern_search.group(0)}")
            return pattern_search.group(0)

        text = text.replace("0", "O")
        text = text.replace("O", "0", 1) if re.match(r"[A-Z]{2}O\d", text) else text

        match = re.search(r"^[A-Z]{2}\d{4}[A-Z]{2}$", text)
        if match:
            return match.group(0)

        return "Невпізнано"

    def recognize_plate(self, img):
        if img is None:
            print("[DEBUG] Помилка: Зображення не отримано")
            return "Невпізнано", 0

        print(f"\n[START] Аналіз нового фото. Розмір: {img.shape[1]}x{img.shape[0]}")
        results = self.model(img, verbose=False)
        recognized_texts = []

        if len(results[0].boxes) == 0:
            print("[DEBUG] YOLO: Номерний знак не знайдено на фото")

        for i, box in enumerate(results[0].boxes):
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            print(f"[DEBUG] Box {i}: Знайдено зону номера (Conf: {conf:.2f})")

            plate = img[y1:y2, x1:x2]
            gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                c = max(contours, key=cv2.contourArea)
                rect = cv2.minAreaRect(c)
                print(f"[DEBUG] Box {i}: Кут нахилу номера: {rect[2]}°")

                box_pts = cv2.boxPoints(rect).astype(np.float32)
                box_pts_sorted = self.order_points(box_pts)

                width = int(rect[1][0])
                height = int(rect[1][1])
                if width < height:
                    width, height = height, width
                    dst_pts = np.array(
                        [
                            [0, 0],
                            [width - 1, 0],
                            [width - 1, height - 1],
                            [0, height - 1],
                        ],
                        dtype="float32",
                    )
                    M = cv2.getPerspectiveTransform(
                        box_pts_sorted[[1, 0, 3, 2]], dst_pts
                    )
                else:
                    dst_pts = np.array(
                        [
                            [0, 0],
                            [width - 1, 0],
                            [width - 1, height - 1],
                            [0, height - 1],
                        ],
                        dtype="float32",
                    )
                    M = cv2.getPerspectiveTransform(box_pts_sorted, dst_pts)

                plate_corrected = cv2.warpPerspective(plate, M, (width, height))
                print(f"[DEBUG] Box {i}: Перспективу вирівняно")
            else:
                print(
                    f"[DEBUG] Box {i}: Контури не знайдено, використовується оригінальний кріп"
                )
                plate_corrected = plate

            plate_gray = cv2.cvtColor(plate_corrected, cv2.COLOR_BGR2GRAY)
            plate_resized = cv2.resize(
                plate_gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC
            )
            plate_invert = cv2.bitwise_not(plate_resized)

            config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            text_normal = pytesseract.image_to_string(
                plate_invert, config=config
            ).strip()
            print(f"[DEBUG] Box {i}: OCR (Direct): '{text_normal}'")

            plate_flip = cv2.flip(plate_invert, 1)
            text_flip = pytesseract.image_to_string(plate_flip, config=config).strip()
            print(f"[DEBUG] Box {i}: OCR (Flipped): '{text_flip}'")

            best_text = text_normal if len(text_normal) >= len(text_flip) else text_flip
            best_text = self.correct_plate_text(best_text)
            print(f"[DEBUG] Box {i}: Результат після валідації: '{best_text}'")

            if best_text != "Невпізнано":
                recognized_texts.append((best_text, conf))

        if not recognized_texts:
            print("[FINISH] Номер не розпізнано жодним методом")
            return "Невпізнано", 0

        recognized_texts.sort(key=lambda x: x[1], reverse=True)
        print(f"[FINISH] Найкращий результат: {recognized_texts[0][0]}")
        return recognized_texts[0]


class VisionEngine:
    def __init__(
        self, video_name=None, live_dict=None, cache_dict=None, model_name="best.pt", frame_step=10
    ):
        self.video_name = video_name
        self.live_dict = live_dict
        self.cache_dict = cache_dict

        model_path = os.path.join(settings.BASE_DIR, "ai_models", model_name)
        self.model = YOLO(model_path)

        self.recognizer = PlateRecognizer(self.model)

        self.frame_step = frame_step
        self.best_results = {}

    def analyze_single_photo(self, image_file, save_to_archive=True):
        """Аналізує фото. Зберігає в Архів тільки якщо save_to_archive=True"""
        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return {"error": "Не вдалося прочитати зображення"}

        plate_text, conf = self.recognizer.recognize_plate(img)

        if plate_text == "Невпізнано":
            return {
                "plate_text": "",
                "confidence": 0,
                "is_known": False,
                "owner_name": "Не розпізнано",
                "owner_phone": "---",
                "can_edit": True,
                "message": "ШІ не зміг прочитати текст. Введіть номер вручну.",
            }

        vehicle = Vehicle.objects.filter(plate_text=plate_text).first()
        is_known = bool(vehicle)
        owner_name = "Невідомий"
        owner_phone = "---"

        if vehicle:
            if vehicle.employee:
                owner_name = (
                    f"{vehicle.employee.first_name} {vehicle.employee.last_name}"
                )
                owner_phone = vehicle.employee.phone
            else:
                owner_name = "Службове авто (без водія)"
        if save_to_archive:
            try:
                camera_obj, _ = Camera.objects.get_or_create(
                    name="Джерело: Фото-завантаження"
                )

                new_rec = DetectedPlate(
                    camera=camera_obj,
                    plate_text=plate_text,
                    confidence=conf,
                    vehicle=vehicle,
                )

                _, buffer = cv2.imencode(".jpg", img)
                content = ContentFile(buffer.tobytes())

                filename = f"{plate_text}_photo_{timezone.now().strftime('%H%M%S')}.jpg"
                new_rec.image.save(filename, content, save=True)

                print(
                    f"[ARCHIVE] Успішно збережено в архів: {plate_text} (Джерело: Фото)"
                )
            except Exception as e:
                print(f"[ERROR] Не вдалося зберегти фото в архів: {e}")
        else:
            print(f"[SKIP] Гість — фото НЕ зберігається в архів: {plate_text}")

        return {
            "plate_text": plate_text,
            "confidence": round(conf, 2),
            "is_known": is_known,
            "owner_name": owner_name,
            "owner_phone": owner_phone,
            "can_edit": True,
            "message": (
                "Увага: низька точність. Перевірте номер!"
                if conf < 0.8
                else "Розпізнано успішно"
            ),
        }

    def check_access(self, plate_text):
        try:
            if BlackList.objects.filter(plate_text=plate_text).exists():
                return "blocked", "ОБ'ЄКТ ЗАБЛОКОВАНО"

            vehicle = Vehicle.objects.filter(plate_text=plate_text).first()
            if vehicle:
                permit = AccessPermit.objects.filter(
                    vehicle=vehicle, is_allowed=True
                ).first()
                if permit and (
                    not permit.end_date or permit.end_date >= timezone.now().date()
                ):
                    name = (
                        vehicle.employee.last_name
                        if hasattr(vehicle, "employee") and vehicle.employee
                        else "Співробітник"
                    )
                    return "allowed", f"ДОЗВОЛЕНО: {name}"
                return "denied", "ЗАБОРОНЕНО: Немає дозволу"

            return "guest", "ГІСТЬ (НЕВІДОМИЙ)"
        except Exception as e:
            print(f"[ERROR] Помилка БД: {e}")
            return "guest", "Помилка бази даних"

    def run(self):
        video_path = os.path.join(settings.BASE_DIR, "videos", self.video_name)
        cap = cv2.VideoCapture(video_path)
        frame_id = 0
        was_auto_saved = False

        while cap.isOpened() and not was_auto_saved:
            ret, frame = cap.read()
            if not ret or frame_id > 800:
                break

            if frame_id % self.frame_step == 0:
                plate_text, conf = self.recognizer.recognize_plate(frame)
                if plate_text != "Невпізнано":

                    if conf >= 0.8:
                        self._auto_save_record(frame, plate_text, conf)
                        was_auto_saved = True
                        break

                    if self.live_dict is not None:
                        self.live_dict[self.video_name] = {
                            "plate": plate_text,
                            "conf": conf,
                            "needs_confirmation": False,
                            "is_finished": False,
                            "message": "Аналізую... шукаю чіткий кадр",
                        }

                    if (
                        plate_text not in self.best_results
                        or conf > self.best_results[plate_text]["conf"]
                    ):
                        _, buffer = cv2.imencode(".jpg", frame)
                        self.best_results[plate_text] = {
                            "conf": conf,
                            "image_content": ContentFile(buffer.tobytes()),
                            "timestamp": timezone.now(),
                        }

            frame_id += 1

        cap.release()
        if not was_auto_saved:
            self.finalize()

    def _auto_save_record(self, frame, plate_text, conf):
        """Внутрішній метод для миттєвого збереження в БД"""
        camera_obj, _ = Camera.objects.get_or_create(name=f"Камера: {self.video_name}")
        vehicle_obj = Vehicle.objects.filter(plate_text=plate_text).first()

        new_rec = DetectedPlate(
            camera=camera_obj,
            plate_text=plate_text,
            confidence=conf,
            vehicle=vehicle_obj,
        )
        _, buffer = cv2.imencode(".jpg", frame)
        content = ContentFile(buffer.tobytes())
        filename = f"{plate_text}_{timezone.now().strftime('%H%M%S')}.jpg"
        new_rec.image.save(filename, content, save=True)

        if self.live_dict is not None:
            self.live_dict[self.video_name] = {
                "plate": plate_text,
                "conf": conf,
                "needs_confirmation": False,
                "is_finished": True,
                "message": f"✅ АВТО-ПРОПУСК: {plate_text}",
            }

    def finalize(self):
        """Фіналізація результатів відео-сесії"""
        try:
            if not self.best_results:
                if self.live_dict is not None:
                    self.live_dict.pop(self.video_name, None)
                return

            top_plate, top_data = sorted(
                self.best_results.items(), key=lambda x: x[1]["conf"], reverse=True
            )[0]

            conf = top_data["conf"]
            status, msg = self.check_access(top_plate)
            vehicle_obj = Vehicle.objects.filter(plate_text=top_plate).first()

            if conf >= 0.8:
                # Авто-збереження
                camera_obj, _ = Camera.objects.get_or_create(
                    name=f"Камера: {self.video_name}"
                )
                new_rec = DetectedPlate.objects.create(
                    camera=camera_obj,
                    plate_text=top_plate,
                    confidence=conf,
                    vehicle=vehicle_obj,
                )
                new_rec.image.save(
                    f"{top_plate}_auto.jpg", top_data["image_content"], save=True
                )

                if self.live_dict is not None:
                    self.live_dict[self.video_name] = {
                        "plate": top_plate,
                        "conf": conf,
                        "needs_confirmation": False,
                        "message": f"✅ АВТО-ПРОПУСК: {top_plate}",
                    }
            else:
                # Ручне підтвердження
                if self.cache_dict is not None:
                    self.cache_dict[self.video_name] = top_data
                if self.live_dict is not None:
                    self.live_dict[self.video_name] = {
                        "plate": top_plate,
                        "conf": conf,
                        "access_type": status,
                        "needs_confirmation": True,
                        "message": f"⚠️ Низька точність ({int(conf * 100)}%). Перевірте!",
                    }
        except Exception as e:
            print(f"[ERROR] Фіналізація: {e}")

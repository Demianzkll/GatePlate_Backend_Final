from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Camera, Department, DetectedPlate, Employee, Vehicle


class RecognitionModelTests(TestCase):
    def setUp(self):
        # Створюємо базові дані для тестів моделей
        self.department = Department.objects.create(name="IT Відділ")
        self.employee = Employee.objects.create(
            first_name="Іван", last_name="Іванов", department=self.department
        )
        self.user = User.objects.create_user(username="guest_user", password="123")

    def test_vehicle_str_for_employee(self):
        """Перевірка правильного відображення авто, що належить працівнику"""
        vehicle = Vehicle.objects.create(plate_text="BC1234AA", employee=self.employee)
        self.assertEqual(str(vehicle), "BC1234AA (Іванов Іван)")

    def test_vehicle_str_for_guest(self):
        """Перевірка правильного відображення авто, що належить гостю"""
        vehicle = Vehicle.objects.create(
            plate_text="KA9999BB",
            created_by=self.user,
            owner_first_name="Петро",
            owner_last_name="Петренко",
        )
        self.assertEqual(str(vehicle), "KA9999BB (Петренко Петро)")

    def test_detected_plate_is_known_property(self):
        """Перевірка property is_known моделі DetectedPlate"""
        vehicle = Vehicle.objects.create(plate_text="BC1234AA", employee=self.employee)
        camera = Camera.objects.create(name="Вхід", stream_url="rtsp://test")

        # Відомий номер
        detection_known = DetectedPlate.objects.create(
            camera=camera, plate_text="BC1234AA", confidence=0.95, vehicle=vehicle
        )
        # Невідомий номер (немає зв'язку з vehicle)
        detection_unknown = DetectedPlate.objects.create(
            camera=camera, plate_text="XX0000XX", confidence=0.90
        )

        self.assertTrue(detection_known.is_known)
        self.assertFalse(detection_unknown.is_known)


# ==========================================
# 2. ТЕСТУВАННЯ API ТА ПРАВ ДОСТУПУ (Views)
# ==========================================
class RecognitionAPITests(APITestCase):
    def setUp(self):
        # Створюємо групи доступу
        self.admin_group = Group.objects.create(name="Administrators")
        self.guest_group = Group.objects.create(name="Guests")

        # Створюємо користувача-адміністратора
        self.admin_user = User.objects.create_user(
            username="admin", password="password"
        )
        self.admin_user.groups.add(self.admin_group)

        # Створюємо звичайного користувача (гостя)
        self.guest_user = User.objects.create_user(
            username="guest", password="password"
        )
        self.guest_user.groups.add(self.guest_group)

        # Створюємо авто для тестування ендпоінту check_plate
        self.vehicle = Vehicle.objects.create(
            plate_text="AI7777KI", owner_first_name="Олег", owner_last_name="Олегов"
        )

    def test_check_plate_success(self):
        """Тест: Авторизований користувач може перевірити існуючий номер"""
        self.client.force_authenticate(user=self.guest_user)

        # URL для @action check_plate у ViewSet зазвичай формується так: <basename>-<action_name>
        url = reverse("vehicle-check-plate")
        response = self.client.get(
            url, {"plate": "ai7777ki "}
        )  # Передаємо з малим регістром і пробілом

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["access"])
        self.assertEqual(response.data["message"], "АВТОПРОПУСК ДОЗВОЛЕНО")
        self.assertEqual(
            response.data["data"]["plate_text"], "AI7777KI"
        )  # Має бути нормалізовано

    def test_check_plate_not_found(self):
        """Тест: Перевірка номера, якого немає в базі"""
        self.client.force_authenticate(user=self.guest_user)
        url = reverse("vehicle-check-plate")
        response = self.client.get(url, {"plate": "XX0000XX"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["access"])

    def test_staff_permission_granted(self):
        """Тест: Користувач з групи Administrators має доступ до списку працівників"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("employees-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_permission_denied_for_guest(self):
        """Тест: Звичайний користувач отримує помилку доступу (403) до списку працівників"""
        self.client.force_authenticate(user=self.guest_user)
        url = reverse("employees-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

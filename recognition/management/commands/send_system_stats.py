"""
Django management command: send_system_stats

Reads real-time CPU / RAM usage via psutil and broadcasts
metrics to the ``system_stats`` Channels group every second.

Usage
-----
    python manage.py send_system_stats

The command runs an infinite loop and must be stopped with Ctrl+C.

Notes
-----
* ``fps``, ``latency``, ``is_active``, ``confidence`` are currently
  simulated with plausible random values.  Replace the placeholders
  in ``_get_ai_metrics()`` once your YOLOv8 pipeline exposes real stats.
* ``cpu`` and ``ram`` come straight from ``psutil`` — these are
  real system values.
"""

import random
import time

import psutil
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand

GROUP_NAME = "system_stats"


class Command(BaseCommand):
    help = "Broadcast real-time system metrics to WebSocket clients every second"

    def handle(self, *args, **options):
        channel_layer = get_channel_layer()
        self.stdout.write(self.style.SUCCESS(
            "[send_system_stats] Broadcasting started. Press Ctrl+C to stop."
        ))

        try:
            while True:
                data = self._collect_metrics()

                async_to_sync(channel_layer.group_send)(
                    GROUP_NAME,
                    {
                        "type": "system.stats.update",
                        "data": data,
                    },
                )

                self.stdout.write(
                    f"  fps={data['fps']:.1f}  cpu={data['cpu']:.1f}%  "
                    f"ram={data['ram']:.1f}%  latency={data['latency']:.0f}ms  "
                    f"active={data['is_active']}  conf={data['confidence']:.2f}"
                )

                time.sleep(1)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n[send_system_stats] Stopped."))

    # ──────────────────────────────────────────────
    def _collect_metrics(self) -> dict:
        """
        Gather system metrics.

        CPU and RAM are real (psutil).
        AI-related fields are simulated — swap them for your
        actual YOLOv8 pipeline stats when available.
        """
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        ai = self._get_ai_metrics()

        return {
            "fps": ai["fps"],
            "latency": ai["latency"],
            "cpu": cpu,
            "ram": ram,
            "is_active": ai["is_active"],
            "confidence": ai["confidence"],
        }

    @staticmethod
    def _get_ai_metrics() -> dict:
        """
        Return AI-pipeline metrics.

        ▸ TODO: Replace the random values below with real stats from
          your YOLOv8 inference loop once it exposes them (e.g. via
          a shared dict, Redis, or an in-process queue).
        """
        is_active = random.random() > 0.15  # ~85 % chance the model is busy

        if is_active:
            fps = round(random.uniform(22, 32), 1)
            latency = round(random.uniform(25, 55), 1)
            confidence = round(random.uniform(0.82, 0.98), 2)
        else:
            fps = 0.0
            latency = 0.0
            confidence = 0.0

        return {
            "fps": fps,
            "latency": latency,
            "is_active": is_active,
            "confidence": confidence,
        }

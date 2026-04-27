"""
WebSocket consumer for real-time system statistics.

Clients connect to  ws://<host>/ws/system-stats/
and receive JSON frames every second:

    {
        "fps": 28.5,
        "cpu": 42.3,
        "ram": 61.7,
        "latency": 35,
        "is_active": true,
        "confidence": 0.94
    }

The consumer spawns an internal asyncio loop that reads
system metrics via psutil and pushes them directly to the
WebSocket — no external process or Redis required.
"""

import asyncio
import json
import random

import psutil
from channels.generic.websocket import AsyncWebsocketConsumer


class SystemStatsConsumer(AsyncWebsocketConsumer):
    """Sends system metrics to the connected client every second."""

    async def connect(self):
        await self.accept()
        self._running = True
        # Prime psutil so the first cpu_percent() call returns a real value
        psutil.cpu_percent(interval=None)
        self._task = asyncio.ensure_future(self._send_loop())

    async def disconnect(self, close_code):
        self._running = False
        self._task.cancel()

    async def _send_loop(self):
        """Collect and send metrics every second."""
        try:
            while self._running:
                data = self._collect_metrics()
                await self.send(text_data=json.dumps(data))
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    # ──────────────────────────────────────────────
    @staticmethod
    def _collect_metrics() -> dict:
        """
        Gather system metrics.

        CPU and RAM are real (psutil).
        AI-related fields are simulated — swap them for your
        actual YOLOv8 pipeline stats when available.
        """
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        ai = SystemStatsConsumer._get_ai_metrics()

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

        TODO: Replace the random values below with real stats from
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

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
system metrics via psutil and real AI pipeline data,
then pushes them directly to the WebSocket.
"""

import asyncio
import json

import psutil
from channels.generic.websocket import AsyncWebsocketConsumer

from recognition.ai_metrics import ai_metrics


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

        CPU and RAM come from psutil (real).
        AI metrics come from the shared ai_metrics singleton,
        which is updated in real-time by the VisionEngine.
        """
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        ai = ai_metrics.snapshot()

        return {
            "fps": ai["fps"],
            "latency": ai["latency"],
            "cpu": cpu,
            "ram": ram,
            "is_active": ai["is_active"],
            "confidence": ai["confidence"],
        }

"""
Thread-safe shared AI metrics for real-time system monitoring.

Updated by VisionEngine during frame processing.
Read by SystemStatsConsumer (WebSocket) to send to frontend.
"""

import threading


class AIMetrics:
    """Thread-safe container for AI pipeline metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "is_active": False,
            "fps": 0.0,
            "latency": 0.0,
            "confidence": 0.0,
        }

    def update(self, **kwargs):
        """Update one or more metric values atomically."""
        with self._lock:
            for key, value in kwargs.items():
                if key in self._data:
                    self._data[key] = value

    def reset(self):
        """Reset all metrics to idle state."""
        with self._lock:
            self._data = {
                "is_active": False,
                "fps": 0.0,
                "latency": 0.0,
                "confidence": 0.0,
            }

    def snapshot(self) -> dict:
        """Return a copy of the current metrics."""
        with self._lock:
            return self._data.copy()


# Global singleton — import this in VisionEngine and consumers
ai_metrics = AIMetrics()

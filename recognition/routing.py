"""WebSocket URL routing for the recognition app."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/system-stats/$", consumers.SystemStatsConsumer.as_asgi()),
]

# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from reminder import consumer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simplecrm.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter([
        path("ws/reminders/", consumer.ReminderConsumer.as_asgi()),
        # Define more WebSocket routes if needed
    ]),
})

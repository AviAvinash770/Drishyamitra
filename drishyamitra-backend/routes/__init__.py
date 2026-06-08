"""Drishyamitra route blueprints."""

from routes.auth import bp as auth_bp
from routes.photos import bp as photos_bp
from routes.faces import bp as faces_bp
from routes.albums import bp as albums_bp
from routes.chat import bp as chat_bp
from routes.analytics import bp as analytics_bp

__all__ = [
    "auth_bp",
    "photos_bp",
    "faces_bp",
    "albums_bp",
    "chat_bp",
    "analytics_bp",
]

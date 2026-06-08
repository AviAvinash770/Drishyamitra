"""
Drishyamitra Backend — Flask Application Entrypoint
====================================================
Agentic AI-powered photo management system.

Starts the Flask server, registers all blueprints, initialises the database,
and seeds default albums so the frontend can display them immediately.
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env BEFORE anything references os.environ
# ---------------------------------------------------------------------------
load_dotenv()


def create_app(test_config=None):
    """Application factory — builds and configures the Flask app."""

    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────
    from config import Config
    app.config.from_object(Config)
    if test_config is not None:
        app.config.from_mapping(test_config)

    # ── CORS — allow React dev server (port 3000) ─────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Database ───────────────────────────────────────────────────────────
    from database.db import db
    db.init_app(app)

    # ── Ensure upload directory exists ─────────────────────────────────────
    upload_dir = app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # ── Register Blueprints ────────────────────────────────────────────────
    from routes.auth import bp as auth_bp
    from routes.photos import bp as photos_bp
    from routes.faces import bp as faces_bp
    from routes.albums import bp as albums_bp
    from routes.chat import bp as chat_bp
    from routes.analytics import bp as analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(faces_bp)
    app.register_blueprint(albums_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analytics_bp)

    # ── Create tables & seed defaults ──────────────────────────────────────
    with app.app_context():
        # Import all models so SQLAlchemy knows about them
        import models  # noqa: F401
        db.create_all()
        _seed_default_albums(db)
        _seed_default_user(db)

    # ── Health-check route ─────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "drishyamitra-backend"})

    # ── Error handlers ─────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

# Default albums matching the frontend FOLDERS constant in App.js
DEFAULT_ALBUMS = [
    {"name": "Family Trips", "icon": "✈️", "color": "#1a73e8", "bg": "#e8f0fe"},
    {"name": "Weddings",     "icon": "💍", "color": "#e8453c", "bg": "#fce8e6"},
    {"name": "Festivals",    "icon": "🎉", "color": "#f9ab00", "bg": "#fef7e0"},
    {"name": "Birthdays",    "icon": "🎂", "color": "#00897b", "bg": "#e0f2f1"},
    {"name": "Events",       "icon": "📸", "color": "#9334e6", "bg": "#f3e8fd"},
]


def _seed_default_albums(db):
    """Insert default albums if the albums table is empty."""
    from models.album import Album

    if Album.query.first() is None:
        for data in DEFAULT_ALBUMS:
            album = Album(
                name=data["name"],
                icon=data["icon"],
                color=data["color"],
                bg=data["bg"],
            )
            db.session.add(album)
        db.session.commit()


def _seed_default_user(db):
    """Insert a default admin user if the users table is empty."""
    from models.user import User
    from flask_bcrypt import generate_password_hash

    if User.query.first() is None:
        hashed = generate_password_hash("password123").decode('utf-8')
        default_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=hashed,
            role="admin"
        )
        db.session.add(default_user)
        db.session.commit()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = create_app()
    print("\n[INFO] Drishyamitra Backend running on http://localhost:5000")
    print("[INFO] Photo management API ready\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

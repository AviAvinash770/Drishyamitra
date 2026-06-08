"""
Authentication Blueprint
========================
Handles user registration, login, and JWT-protected profile access.

Endpoints:
    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/profile
"""

import logging
from flask import Blueprint, request, jsonify, current_app, g
from flask_bcrypt import Bcrypt
from database.db import db
from models.user import User
from utils.auth_helpers import generate_token, token_required

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="/api/auth")
bcrypt = Bcrypt()


@bp.record_once
def on_register(state):
    """Initialise Bcrypt with the app when the blueprint is registered."""
    bcrypt.init_app(state.app)


# ── POST /api/auth/register ───────────────────────────────────────────────

@bp.route("/register", methods=["POST"])
def register():
    """Register a new user account.

    Expects JSON: ``{"username": "...", "email": "...", "password": "..."}``

    Returns 201 with a JWT token and user object on success.
    """
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # ── Validate required fields ──────────────────────────────────────
    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # ── Check uniqueness ──────────────────────────────────────────────
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    try:
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        db.session.add(user)
        db.session.commit()

        token = generate_token(user.id, current_app.config["SECRET_KEY"])

        logger.info("User registered: %s (%s)", username, email)
        return jsonify({
            "message": "Registration successful",
            "token": token,
            "user": user.to_dict(),
        }), 201

    except Exception as exc:
        db.session.rollback()
        logger.exception("Registration failed")
        return jsonify({"error": str(exc)}), 500


# ── POST /api/auth/login ──────────────────────────────────────────────────

@bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT token.

    Expects JSON: ``{"email": "...", "password": "..."}``
    """
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify({"error": "Invalid email or password"}), 401

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user.id, current_app.config["SECRET_KEY"])

    logger.info("User logged in: %s", email)
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict(),
    }), 200


# ── GET /api/auth/profile ─────────────────────────────────────────────────

@bp.route("/profile", methods=["GET"])
@token_required
def profile():
    """Return the authenticated user's profile."""
    return jsonify(g.current_user.to_dict()), 200


# ── POST /api/auth/profile/update ─────────────────────────────────────────

@bp.route("/profile/update", methods=["POST"])
@token_required
def update_profile():
    """Update user profile info, including optional profile picture."""
    import os
    import uuid
    user = g.current_user
    
    # Check if this is a multipart request (with profile picture upload)
    if request.content_type and 'multipart/form-data' in request.content_type:
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        bio = request.form.get("bio", "").strip()
        
        # Profile pic file upload
        if "profile_pic" in request.files:
            file = request.files["profile_pic"]
            if file and file.filename != "":
                ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "png"
                unique_name = f"profile_{uuid.uuid4().hex}.{ext}"
                upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, unique_name)
                file.save(file_path)
                user.profile_pic = f"/api/photos/file/{unique_name}"
    else:
        # JSON request
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        address = data.get("address", "").strip()
        bio = data.get("bio", "").strip()
        profile_pic_url = data.get("profile_pic", "")
        if profile_pic_url:
            user.profile_pic = profile_pic_url

    # Update basic info if provided
    if username:
        user.username = username
    if email:
        user.email = email
    
    user.phone = phone
    user.address = address
    user.bio = bio
    
    try:
        db.session.commit()
        return jsonify({
            "message": "Profile updated successfully",
            "user": user.to_dict()
        }), 200
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to update profile")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/auth/backup ──────────────────────────────────────────────────

@bp.route("/backup", methods=["GET"])
@token_required
def backup():
    """Create a ZIP file containing the SQLite database and all uploaded photos."""
    import os
    import zipfile
    import io
    from datetime import datetime
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Back up database
            db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
            if db_path.startswith("sqlite:///"):
                actual_db_path = db_path.replace("sqlite:///", "")
                # Relative path check
                if not os.path.isabs(actual_db_path):
                    instance_db = os.path.join(current_app.instance_path, actual_db_path)
                    if os.path.exists(instance_db):
                        zipf.write(instance_db, arcname="drishyamitra.db")
                    elif os.path.exists(actual_db_path):
                        zipf.write(actual_db_path, arcname="drishyamitra.db")
            
            # 2. Back up upload folder
            upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
            if os.path.exists(upload_dir):
                for root, dirs, files in os.walk(upload_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("uploads", file)
                        zipf.write(file_path, arcname=arcname)
                        
        memory_file.seek(0)
        from flask import send_file
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"drishyamitra_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
    except Exception as exc:
        logger.exception("Backup failed")
        return jsonify({"error": str(exc)}), 500

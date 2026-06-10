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
from database.db import db
from models.user import User
from utils.auth_helpers import generate_token, token_required
from utils.activity_helpers import log_activity
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__, url_prefix="/api/auth")


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
        password_hash = generate_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        db.session.add(user)
        db.session.commit()

        # Seed default albums for this newly registered user
        from app import DEFAULT_ALBUMS
        from models.album import Album
        for data in DEFAULT_ALBUMS:
            album = Album(
                name=data["name"],
                icon=data["icon"],
                color=data["color"],
                bg=data["bg"],
                user_id=user.id
            )
            db.session.add(album)
        db.session.commit()

        token = generate_token(user.id, current_app.config["SECRET_KEY"])

        logger.info("User registered: %s (%s)", username, email)
        log_activity(user.id, "Local Registered", f"Email: {email}")
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

    if not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user.id, current_app.config["SECRET_KEY"])

    logger.info("User logged in: %s", email)
    log_activity(user.id, "Local Logged In", f"Email: {email}")
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
        log_activity(user.id, "Profile Updated")
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
        log_activity(user.id, "Backup Downloaded")
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


@bp.route("/backup/email", methods=["POST", "GET"])
@token_required
def email_backup():
    """Create a ZIP file containing the SQLite database and all uploaded photos,
    and email it to the logged-in user's email address using SMTP/Flask-Mail.
    """
    import os
    import zipfile
    import io
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email import encoders
    from datetime import datetime

    user = g.current_user
    recipient_email = user.email

    try:
        # Create zip in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Back up database
            db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
            if db_path.startswith("sqlite:///"):
                actual_db_path = db_path.replace("sqlite:///", "")
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
        zip_data = memory_file.getvalue()

        # Build email message
        msg = MIMEMultipart()
        msg['From'] = current_app.config.get('MAIL_DEFAULT_SENDER', 'no-reply@drishyamitra.com')
        msg['To'] = recipient_email
        msg['Subject'] = f"Drishyamitra Data Backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        body = (
            f"Hello {user.username},\n\n"
            "Please find attached the secure backup of your Drishyamitra data, "
            "including your SQLite database and uploaded photos.\n\n"
            "Best regards,\n"
            "Drishyamitra Team"
        )
        msg.attach(MIMEText(body, 'plain'))

        # Attach ZIP file
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(zip_data)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="drishyamitra_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        )
        msg.attach(part)

        # Try sending via smtplib
        mail_server = current_app.config.get('MAIL_SERVER', '')
        mail_port = int(current_app.config.get('MAIL_PORT', 587))
        mail_username = current_app.config.get('MAIL_USERNAME', '')
        mail_password = current_app.config.get('MAIL_PASSWORD', '')
        mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)

        if mail_server and mail_username:
            smtp_class = smtplib.SMTP_SSL if mail_port == 465 else smtplib.SMTP
            with smtp_class(mail_server, mail_port, timeout=15) as server:
                if mail_port != 465 and mail_use_tls:
                    server.starttls()
                if mail_password:
                    server.login(mail_username, mail_password)
                server.sendmail(msg['From'], [recipient_email], msg.as_string())
            logger.info("Sent email backup to %s via smtplib", recipient_email)
        else:
            logger.warning("SMTP server not configured. Cannot send email backup.")
            return jsonify({"error": "SMTP server not configured in backend configuration."}), 400

        log_activity(user.id, "Backup Emailed", f"Sent to {recipient_email}")
        return jsonify({"message": f"Backup successfully sent to {recipient_email}"}), 200

    except Exception as exc:
        logger.exception("Email backup failed")
        return jsonify({"error": str(exc)}), 500


@bp.route("/google/verify", methods=["POST"])
def google_verify():
    """Verify Google ID Token (OAuth 2.0) and log in / register the user."""
    from google.oauth2 import id_token
    from google.auth.transport import requests
    from models.user import User

    data = request.get_json(silent=True) or {}
    token = data.get("id_token")

    if not token:
        return jsonify({"error": "Google ID Token is required"}), 400

    try:
        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        if not client_id:
            logger.error("GOOGLE_CLIENT_ID is not configured in backend settings.")
            return jsonify({"error": "Google Client ID is not configured on the server."}), 500

        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

        email = idinfo.get('email', '').strip().lower()
        name = idinfo.get('name', '').strip()
        picture = idinfo.get('picture', '')

        if not email:
            return jsonify({"error": "Email not found in Google account payload"}), 400

        user = User.query.filter_by(email=email).first()

        if user is None:
            import uuid
            username = name or email.split('@')[0]
            password_hash = "OAUTH_NO_PASSWORD_" + uuid.uuid4().hex
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                profile_pic=picture
            )
            db.session.add(user)
            db.session.commit()

            from app import DEFAULT_ALBUMS
            from models.album import Album
            for d in DEFAULT_ALBUMS:
                album = Album(
                    name=d["name"],
                    icon=d["icon"],
                    color=d["color"],
                    bg=d["bg"],
                    user_id=user.id
                )
                db.session.add(album)
            db.session.commit()
            
            logger.info("Google OAuth user registered: %s (%s)", username, email)
            log_activity(user.id, "Google Registered", f"Email: {email}")
        else:
            if picture and user.profile_pic != picture:
                user.profile_pic = picture
                db.session.commit()
            logger.info("Google OAuth user logged in: %s", email)
            log_activity(user.id, "Google Logged In", f"Email: {email}")

        app_token = generate_token(user.id, current_app.config["SECRET_KEY"])

        return jsonify({
            "message": "Google authentication successful",
            "token": app_token,
            "user": user.to_dict()
        }), 200

    except ValueError as val_err:
        logger.warning("Invalid Google ID Token: %s", val_err)
        return jsonify({"error": f"Invalid Google ID Token: {val_err}"}), 401
    except Exception as exc:
        logger.exception("Google verification failed")
        return jsonify({"error": str(exc)}), 500


@bp.route("/config", methods=["GET"])
def get_config():
    """Return public configurations, like the Google Client ID."""
    return jsonify({
        "google_client_id": current_app.config.get("GOOGLE_CLIENT_ID", "")
    }), 200


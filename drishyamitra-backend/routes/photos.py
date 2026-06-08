"""
Photos Blueprint
=================
Handles photo upload, listing, detail retrieval, and deletion.

Endpoints:
    POST   /api/photos/upload
    GET    /api/photos/
    GET    /api/photos/<id>
    DELETE /api/photos/<id>
    POST   /api/search
"""

import os
import uuid
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.utils import secure_filename

from database.db import db
from models.photo import Photo
from models.album import Album
from utils.auth_helpers import token_required

logger = logging.getLogger(__name__)
bp = Blueprint("photos", __name__, url_prefix="/api/photos")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "heic", "webp", "gif", "bmp", "tiff"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _human_size(size_bytes):
    """Convert bytes to a human-readable string like '2.4 MB'."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ── POST /api/photos/upload ───────────────────────────────────────────────

@bp.route("/upload", methods=["POST"])
@token_required
def upload_photo():
    """Upload a photo, save it to disk, and run AI analysis.

    Accepts ``multipart/form-data`` with a ``photo`` file field.
    Returns the analysed photo metadata.
    """
    if "photo" not in request.files:
        return jsonify({"error": "No photo file provided"}), 400

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    try:
        # Generate unique filename
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        safe_name = secure_filename(file.filename)

        upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_name)
        file.save(file_path)

        # Calculate file size
        file_size = os.path.getsize(file_path)
        size_str = _human_size(file_size)

        # Extract date from filename or use today
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Create photo record
        photo = Photo(
            filename=safe_name,
            file_path=file_path,
            size=size_str,
            date=today,
            user_id=g.current_user.id,
        )
        db.session.add(photo)
        db.session.commit()

        # Run AI analysis pipeline (non-blocking — errors won't fail the upload)
        analysis_result = {}
        try:
            from services.photo_analysis_service import PhotoAnalysisService
            analysis_result = PhotoAnalysisService.analyze_photo(photo.id)
            logger.info("AI analysis complete for photo %s", photo.id)
        except Exception as exc:
            logger.warning("AI analysis skipped for photo %s: %s", photo.id, exc)

        # Refresh photo to pick up any changes from analysis
        db.session.refresh(photo)

        result = photo.to_dict()
        if analysis_result:
            result["analysis"] = analysis_result

        return jsonify(result), 201

    except Exception as exc:
        db.session.rollback()
        logger.exception("Photo upload failed")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/photos/file/<filename> ───────────────────────────────────────

from flask import send_from_directory

@bp.route("/file/<filename>", methods=["GET"])
def serve_file(filename):
    """Serve the raw photo file from the upload directory."""
    upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
    abs_upload_dir = os.path.abspath(upload_dir)
    return send_from_directory(abs_upload_dir, filename)


# ── GET /api/photos/ ──────────────────────────────────────────────────────

@bp.route("/", methods=["GET"])
def list_photos():
    """List photos with optional filtering.

    Query params:
        album   – filter by album name
        favorite – 'true' to show only favourites
        search  – free-text search (semantic + structured)
    """
    try:
        album_name = request.args.get("album")
        favorite = request.args.get("favorite", "").lower() == "true"
        search_query = request.args.get("search", "").strip()

        # Semantic search path
        if search_query:
            photo_ids = []
            try:
                from services.vector_service import VectorService
                photo_ids = VectorService.search_photos(search_query, limit=50)
            except Exception:
                pass

            if photo_ids:
                photos = Photo.query.filter(Photo.id.in_(photo_ids)).all()
                # Preserve vector search ordering
                id_order = {pid: idx for idx, pid in enumerate(photo_ids)}
                photos.sort(key=lambda p: id_order.get(p.id, 999))
            else:
                # Fallback: structured text search on filename, description, tags
                photos = Photo.query.filter(
                    db.or_(
                        Photo.filename.ilike(f"%{search_query}%"),
                        Photo.description.ilike(f"%{search_query}%"),
                        Photo.location.ilike(f"%{search_query}%"),
                    )
                ).order_by(Photo.upload_date.desc()).all()

            return jsonify([p.to_dict() for p in photos]), 200

        # Filtered query
        query = Photo.query

        if album_name:
            query = query.join(Photo.albums).filter(Album.name == album_name)

        if favorite:
            query = query.filter(Photo.favorite.is_(True))

        photos = query.order_by(Photo.upload_date.desc()).all()
        return jsonify([p.to_dict() for p in photos]), 200

    except Exception as exc:
        logger.exception("Failed to list photos")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/photos/<id> ──────────────────────────────────────────────────

@bp.route("/<int:photo_id>", methods=["GET"])
def get_photo(photo_id):
    """Return detailed metadata for a single photo."""
    photo = Photo.query.get(photo_id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404
    return jsonify(photo.to_dict()), 200


# ── DELETE /api/photos/<id> ───────────────────────────────────────────────

@bp.route("/<int:photo_id>", methods=["DELETE"])
@token_required
def delete_photo(photo_id):
    """Delete a photo, its file on disk, and its vector index entry."""
    photo = Photo.query.get(photo_id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    try:
        # Remove file from disk
        if os.path.exists(photo.file_path):
            os.remove(photo.file_path)

        # Remove from vector store
        try:
            from services.vector_service import VectorService
            VectorService.delete_photo(photo.id)
        except Exception:
            pass

        db.session.delete(photo)
        db.session.commit()

        return jsonify({"message": f"Photo {photo_id} deleted"}), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to delete photo %s", photo_id)
        return jsonify({"error": str(exc)}), 500


# ── POST /api/search ──────────────────────────────────────────────────────

@bp.route("/search", methods=["POST"])
def search_photos():
    """Natural language photo search.

    Expects JSON: ``{"query": "Show photos of Priya from weddings"}``

    Combines structured DB search with ChromaDB semantic search.
    """
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        results = []
        seen_ids = set()

        # 1 — Structured search: person names
        from models.person import Person
        from models.face import Face
        persons = Person.query.filter(Person.name.ilike(f"%{query}%")).all()
        for person in persons:
            photo_ids = list({f.photo_id for f in person.faces})
            for pid in photo_ids:
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    photo = Photo.query.get(pid)
                    if photo:
                        results.append(photo.to_dict())

        # 2 — Structured search: album / location / description
        struct_photos = Photo.query.filter(
            db.or_(
                Photo.description.ilike(f"%{query}%"),
                Photo.location.ilike(f"%{query}%"),
                Photo.filename.ilike(f"%{query}%"),
            )
        ).all()
        for p in struct_photos:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                results.append(p.to_dict())

        # 3 — Semantic vector search
        try:
            from services.vector_service import VectorService
            vector_ids = VectorService.search_photos(query, limit=20)
            for vid in vector_ids:
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    photo = Photo.query.get(vid)
                    if photo:
                        results.append(photo.to_dict())
        except Exception:
            pass

        return jsonify({"query": query, "count": len(results), "results": results}), 200

    except Exception as exc:
        logger.exception("Search failed")
        return jsonify({"error": str(exc)}), 500

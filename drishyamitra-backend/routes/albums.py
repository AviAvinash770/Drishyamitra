"""
Albums Blueprint
=================
Handles album listing and creation.

Endpoints:
    GET  /api/albums/
    POST /api/albums/create
"""

import logging
from flask import Blueprint, request, jsonify, g

from database.db import db
from models.album import Album
from utils.auth_helpers import token_required

logger = logging.getLogger(__name__)
bp = Blueprint("albums", __name__, url_prefix="/api/albums")


# ── GET /api/albums/ ──────────────────────────────────────────────────────

@bp.route("/", methods=["GET"])
@token_required
def list_albums():
    """Return all albums with their photo counts."""
    try:
        albums = Album.query.filter_by(user_id=g.current_user.id).order_by(Album.name).all()
        return jsonify([a.to_dict() for a in albums]), 200
    except Exception as exc:
        logger.exception("Failed to list albums")
        return jsonify({"error": str(exc)}), 500


# ── POST /api/albums/create ───────────────────────────────────────────────

@bp.route("/create", methods=["POST"])
@token_required
def create_album():
    """Create a new album.

    Expects JSON::

        {
            "name": "Goa Trip 2025",
            "description": "Beach photos from our Goa vacation",   // optional
            "icon": "🏖️"                                            // optional
        }
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Album name is required"}), 400

    # Check uniqueness scoped to user
    if Album.query.filter(
        Album.user_id == g.current_user.id,
        db.func.lower(Album.name) == name.lower()
    ).first():
        return jsonify({"error": f'Album "{name}" already exists'}), 409

    try:
        album = Album(
            name=name,
            user_id=g.current_user.id,
            description=data.get("description", ""),
            icon=data.get("icon", "📁"),
            color=data.get("color", "#1a73e8"),
            bg=data.get("bg", "#e8f0fe"),
        )
        db.session.add(album)
        db.session.commit()
        from utils.activity_helpers import log_activity
        log_activity(g.current_user.id, "Album Created", f"Name: {name}")

        logger.info("Album created: %s", name)
        return jsonify(album.to_dict()), 201

    except Exception as exc:
        db.session.rollback()
        logger.exception("Album creation failed")
        return jsonify({"error": str(exc)}), 500


# ── POST /api/albums/<int:album_id>/assign ───────────────────────────────

@bp.route("/<int:album_id>/assign", methods=["POST"])
@token_required
def assign_photos_to_album(album_id):
    """Assign selected photos to a manually created album.

    Expects JSON::

        {
            "photo_ids": [1, 2, 3]
        }
    """
    album = Album.query.filter_by(id=album_id, user_id=g.current_user.id).first()
    if not album:
        return jsonify({"error": "Album not found"}), 404

    data = request.get_json(silent=True) or {}
    photo_ids = data.get("photo_ids", [])

    if not photo_ids:
        return jsonify({"error": "photo_ids is required"}), 400

    try:
        from models.photo import Photo
        photos = Photo.query.filter(Photo.id.in_(photo_ids), Photo.user_id == g.current_user.id).all()
        
        added_count = 0
        for photo in photos:
            if photo not in album.photos:
                album.photos.append(photo)
                added_count += 1
                
        db.session.commit()
        from utils.activity_helpers import log_activity
        log_activity(g.current_user.id, "Album Photos Assigned", f"Album: {album.name}, Photos: {added_count}")
        
        logger.info("Assigned %d photos to album %s", added_count, album.name)
        return jsonify({
            "message": f"Successfully assigned {added_count} photos to album {album.name}",
            "added_count": added_count
        }), 200
        
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to assign photos to album")
        return jsonify({"error": str(exc)}), 500

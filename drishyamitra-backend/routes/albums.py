"""
Albums Blueprint
=================
Handles album listing and creation.

Endpoints:
    GET  /api/albums/
    POST /api/albums/create
"""

import logging
from flask import Blueprint, request, jsonify

from database.db import db
from models.album import Album

logger = logging.getLogger(__name__)
bp = Blueprint("albums", __name__, url_prefix="/api/albums")


# ── GET /api/albums/ ──────────────────────────────────────────────────────

@bp.route("/", methods=["GET"])
def list_albums():
    """Return all albums with their photo counts."""
    try:
        albums = Album.query.order_by(Album.name).all()
        return jsonify([a.to_dict() for a in albums]), 200
    except Exception as exc:
        logger.exception("Failed to list albums")
        return jsonify({"error": str(exc)}), 500


# ── POST /api/albums/create ───────────────────────────────────────────────

@bp.route("/create", methods=["POST"])
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

    # Check uniqueness
    if Album.query.filter(db.func.lower(Album.name) == name.lower()).first():
        return jsonify({"error": f'Album "{name}" already exists'}), 409

    try:
        album = Album(
            name=name,
            description=data.get("description", ""),
            icon=data.get("icon", "📁"),
            color=data.get("color", "#1a73e8"),
            bg=data.get("bg", "#e8f0fe"),
        )
        db.session.add(album)
        db.session.commit()

        logger.info("Album created: %s", name)
        return jsonify(album.to_dict()), 201

    except Exception as exc:
        db.session.rollback()
        logger.exception("Album creation failed")
        return jsonify({"error": str(exc)}), 500

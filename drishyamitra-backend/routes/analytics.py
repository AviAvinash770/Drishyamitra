"""
Analytics Blueprint
====================
Returns aggregated dashboard statistics.

Endpoints:
    GET /api/analytics/dashboard
"""

import logging
from collections import defaultdict

from flask import Blueprint, jsonify, g

from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face
from models.album import Album
from models.sharing import DeliveryHistory
from models.log import AgentLog
from utils.auth_helpers import token_required

logger = logging.getLogger(__name__)
bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.route("/dashboard", methods=["GET"])
@token_required
def dashboard():
    """Return comprehensive analytics for the dashboard.

    Response includes total counts, storage breakdown, face-recognition
    accuracy, most-photographed person, photos-per-month histogram,
    and AI activity count.
    """
    try:
        # ── Counts ────────────────────────────────────────────────────
        total_photos = Photo.query.filter_by(user_id=g.current_user.id).count()
        total_people = Person.query.filter_by(user_id=g.current_user.id).count()
        total_albums = Album.query.filter_by(user_id=g.current_user.id).count()
        total_faces = Face.query.join(Face.photo).filter(Photo.user_id == g.current_user.id).count()
        unrecognised = Face.query.join(Face.photo).filter(Photo.user_id == g.current_user.id, Face.person_id.is_(None)).count()
        recognised = total_faces - unrecognised
        total_deliveries = DeliveryHistory.query.filter_by(user_id=g.current_user.id).count()
        ai_actions = AgentLog.query.filter_by(user_id=g.current_user.id).count()

        # ── Face recognition accuracy ─────────────────────────────────
        accuracy = round((recognised / total_faces * 100), 1) if total_faces else 0.0

        # ── Storage usage ─────────────────────────────────────────────
        from utils.storage_helpers import get_user_storage_usage
        total_bytes = get_user_storage_usage(g.current_user.id)
        storage_gb = round(total_bytes / (1024 * 1024 * 1024), 4)
        storage_limit_gb = 10.0
        storage_pct = round((storage_gb / storage_limit_gb) * 100, 2) if storage_limit_gb else 0

        # ── Most photographed person ──────────────────────────────────
        most_photographed = None
        if total_people > 0:
            persons = Person.query.filter_by(user_id=g.current_user.id).all()
            best = max(persons, key=lambda p: p.photo_count, default=None)
            if best and best.photo_count > 0:
                most_photographed = {
                    "name": best.name,
                    "photoCount": best.photo_count,
                    "emoji": best.emoji,
                }

        # ── Photos per month ──────────────────────────────────────────
        month_counts = defaultdict(int)
        for photo in Photo.query.filter_by(user_id=g.current_user.id).with_entities(Photo.date).all():
            if photo.date and len(photo.date) >= 7:
                month_counts[photo.date[:7]] += 1

        photos_per_month = [
            {"month": k, "count": v}
            for k, v in sorted(month_counts.items())
        ][-6:]  # Last 6 months

        # ── People breakdown ──────────────────────────────────────────
        people_stats = []
        for person in Person.query.filter_by(user_id=g.current_user.id).order_by(Person.name).all():
            people_stats.append({
                "name": person.name,
                "photoCount": person.photo_count,
                "emoji": person.emoji,
                "color": person.color,
            })
        people_stats.sort(key=lambda x: x["photoCount"], reverse=True)

        total_favorites = Photo.query.filter_by(user_id=g.current_user.id, favorite=True).count()

        from sqlalchemy import func
        total_group_photos = db.session.query(Face.photo_id).join(Face.photo).filter(
            Photo.user_id == g.current_user.id
        ).group_by(Face.photo_id).having(func.count(Face.id) > 1).count()

        total_scenes_albums = Album.query.filter(
            Album.user_id == g.current_user.id,
            Album.name.like("Scene:%")
        ).count()

        return jsonify({
            "total_photos": total_photos,
            "total_people": total_people,
            "total_albums": total_albums,
            "total_favorites": total_favorites,
            "total_group_photos": total_group_photos,
            "total_scenes_albums": total_scenes_albums,
            "total_faces_detected": total_faces,
            "unrecognised_faces": unrecognised,
            "recognised_faces": recognised,
            "face_recognition_accuracy": accuracy,
            "total_deliveries": total_deliveries,
            "ai_actions_count": ai_actions,
            "storage": {
                "used_gb": storage_gb,
                "limit_gb": storage_limit_gb,
                "used_pct": storage_pct,
                "remaining_gb": round(storage_limit_gb - storage_gb, 2),
            },
            "most_photographed": most_photographed,
            "photos_per_month": photos_per_month,
            "people_stats": people_stats[:5],
        }), 200

    except Exception as exc:
        logger.exception("Analytics dashboard failed")
        return jsonify({"error": str(exc)}), 500


@bp.route("/activity", methods=["GET"])
@token_required
def list_activity_logs():
    """Fetch and return real activity log records for the logged-in user."""
    try:
        from models.activity_log import ActivityLog
        logs = (
            ActivityLog.query
            .filter_by(user_id=g.current_user.id)
            .order_by(ActivityLog.timestamp.desc())
            .limit(50)
            .all()
        )
        return jsonify([log.to_dict() for log in logs]), 200
    except Exception as exc:
        logger.exception("Failed to fetch activity logs")
        return jsonify({"error": str(exc)}), 500

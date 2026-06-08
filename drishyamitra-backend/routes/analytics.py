"""
Analytics Blueprint
====================
Returns aggregated dashboard statistics.

Endpoints:
    GET /api/analytics/dashboard
"""

import logging
from collections import defaultdict

from flask import Blueprint, jsonify

from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face
from models.album import Album
from models.sharing import DeliveryHistory
from models.log import AgentLog

logger = logging.getLogger(__name__)
bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    """Return comprehensive analytics for the dashboard.

    Response includes total counts, storage breakdown, face-recognition
    accuracy, most-photographed person, photos-per-month histogram,
    and AI activity count.
    """
    try:
        # ── Counts ────────────────────────────────────────────────────
        total_photos = Photo.query.count()
        total_people = Person.query.count()
        total_albums = Album.query.count()
        total_faces = Face.query.count()
        unrecognised = Face.query.filter_by(person_id=None).count()
        recognised = total_faces - unrecognised
        total_deliveries = DeliveryHistory.query.count()
        ai_actions = AgentLog.query.count()

        # ── Face recognition accuracy ─────────────────────────────────
        accuracy = round((recognised / total_faces * 100), 1) if total_faces else 0.0

        # ── Storage usage ─────────────────────────────────────────────
        total_bytes = 0
        for photo in Photo.query.with_entities(Photo.size).all():
            size_str = photo.size or "0"
            try:
                num = float(size_str.split()[0])
                unit = size_str.split()[1] if len(size_str.split()) > 1 else "B"
                if unit == "KB":
                    total_bytes += num * 1024
                elif unit == "MB":
                    total_bytes += num * 1024 * 1024
                elif unit == "GB":
                    total_bytes += num * 1024 * 1024 * 1024
                else:
                    total_bytes += num
            except (ValueError, IndexError):
                pass

        storage_gb = round(total_bytes / (1024 * 1024 * 1024), 2)
        storage_limit_gb = 10.0
        storage_pct = round((storage_gb / storage_limit_gb) * 100, 1) if storage_limit_gb else 0

        # ── Most photographed person ──────────────────────────────────
        most_photographed = None
        if total_people > 0:
            persons = Person.query.all()
            best = max(persons, key=lambda p: p.photo_count, default=None)
            if best and best.photo_count > 0:
                most_photographed = {
                    "name": best.name,
                    "photoCount": best.photo_count,
                    "emoji": best.emoji,
                }

        # ── Photos per month ──────────────────────────────────────────
        month_counts = defaultdict(int)
        for photo in Photo.query.with_entities(Photo.date).all():
            if photo.date and len(photo.date) >= 7:
                month_counts[photo.date[:7]] += 1

        photos_per_month = [
            {"month": k, "count": v}
            for k, v in sorted(month_counts.items())
        ][-6:]  # Last 6 months

        # ── People breakdown ──────────────────────────────────────────
        people_stats = []
        for person in Person.query.order_by(Person.name).all():
            people_stats.append({
                "name": person.name,
                "photoCount": person.photo_count,
                "emoji": person.emoji,
                "color": person.color,
            })
        people_stats.sort(key=lambda x: x["photoCount"], reverse=True)

        return jsonify({
            "total_photos": total_photos,
            "total_people": total_people,
            "total_albums": total_albums,
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

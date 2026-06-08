"""
Faces Blueprint
================
Handles face detection, labelling, and person-photo lookups.

Endpoints:
    POST /api/faces/detect
    POST /api/faces/label
    GET  /api/faces/
    GET  /api/faces/person/<id>
"""

import logging
from flask import Blueprint, request, jsonify

from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face

logger = logging.getLogger(__name__)
bp = Blueprint("faces", __name__, url_prefix="/api/faces")

# Colour palette that matches the frontend GP palette
PERSON_PALETTES = [
    {"color": "#9334e6", "bg": "#f3e8fd", "emoji": "👩"},
    {"color": "#1a73e8", "bg": "#e8f0fe", "emoji": "👨"},
    {"color": "#f9ab00", "bg": "#fef7e0", "emoji": "👵"},
    {"color": "#e8453c", "bg": "#fce8e6", "emoji": "👧"},
    {"color": "#00897b", "bg": "#e0f2f1", "emoji": "👨‍🦳"},
    {"color": "#34a853", "bg": "#e6f4ea", "emoji": "🧑"},
]


def _make_initials(name):
    """Generate initials from a full name (e.g. 'Priya Sharma' → 'PS')."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _pick_palette(person_id):
    """Pick a colour palette for a new person, cycling through the list."""
    return PERSON_PALETTES[person_id % len(PERSON_PALETTES)]


# ── POST /api/faces/detect ────────────────────────────────────────────────

@bp.route("/detect", methods=["POST"])
def detect_faces():
    """Run face detection on a photo.

    Expects JSON: ``{"photo_id": 123}``

    Detects faces, generates embeddings, matches against known people,
    and creates Face records.
    """
    data = request.get_json(silent=True) or {}
    photo_id = data.get("photo_id")

    if not photo_id:
        return jsonify({"error": "photo_id is required"}), 400

    photo = Photo.query.get(photo_id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    try:
        from services.vision_service import VisionService
        from services.embedding_service import EmbeddingService

        detections = VisionService.detect_faces(photo.file_path)

        # Get all known faces (those already linked to a person)
        known_faces = Face.query.filter(Face.person_id.isnot(None)).all()

        created_faces = []
        for det in detections:
            # Try to match against existing people
            matched_person = EmbeddingService.find_matching_person(
                det["embedding"], known_faces
            )

            face = Face(
                photo_id=photo.id,
                person_id=matched_person.id if matched_person else None,
                bounding_box=det["bounding_box"],
                embedding=det["embedding"],
                confidence=det.get("confidence", 1.0),
            )
            db.session.add(face)
            created_faces.append(face)

        db.session.commit()

        return jsonify({
            "faces_detected": len(created_faces),
            "faces": [f.to_dict() for f in created_faces],
        }), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Face detection failed for photo %s", photo_id)
        return jsonify({"error": str(exc)}), 500


# ── POST /api/faces/label ─────────────────────────────────────────────────

@bp.route("/label", methods=["POST"])
def label_face():
    """Label an unrecognised face with a person name.

    Expects JSON: ``{"face_id": 42, "name": "Priya Sharma"}``

    If the person already exists, links the face. Otherwise creates a new
    Person record. Also auto-links other unidentified faces whose embeddings
    are similar.
    """
    data = request.get_json(silent=True) or {}
    face_id = data.get("face_id")
    name = data.get("name", "").strip()

    if not face_id or not name:
        return jsonify({"error": "face_id and name are required"}), 400

    face = Face.query.get(face_id)
    if not face:
        return jsonify({"error": "Face not found"}), 404

    try:
        # Find or create person
        person = Person.query.filter(
            db.func.lower(Person.name) == name.lower()
        ).first()

        if not person:
            palette = _pick_palette(Person.query.count())
            person = Person(
                name=name,
                initials=_make_initials(name),
                emoji=palette["emoji"],
                color=palette["color"],
                bg=palette["bg"],
                tags=[],
            )
            db.session.add(person)
            db.session.flush()  # Get person.id

        # Link the face
        face.person_id = person.id

        # Auto-link similar unidentified faces
        auto_linked = 0
        try:
            from services.embedding_service import EmbeddingService

            unlinked = Face.query.filter(
                Face.person_id.is_(None),
                Face.id != face.id,
            ).all()

            for uf in unlinked:
                sim = EmbeddingService.calculate_similarity(
                    face.embedding, uf.embedding
                )
                if sim >= EmbeddingService.SIMILARITY_THRESHOLD:
                    uf.person_id = person.id
                    auto_linked += 1
        except Exception as exc:
            logger.warning("Auto-linking skipped: %s", exc)

        db.session.commit()

        return jsonify({
            "message": f'Face labelled as "{name}"',
            "auto_linked": auto_linked,
            "person": person.to_dict(),
        }), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Face labelling failed")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/faces/ ───────────────────────────────────────────────────────

@bp.route("/", methods=["GET"])
def list_unrecognised():
    """Return all faces that have not been identified (person_id IS NULL)."""
    try:
        faces = Face.query.filter(Face.person_id.is_(None)).order_by(
            Face.created_at.desc()
        ).all()
        return jsonify([f.to_dict() for f in faces]), 200
    except Exception as exc:
        logger.exception("Failed to list unrecognised faces")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/faces/person/<id> ────────────────────────────────────────────

@bp.route("/person/<int:person_id>", methods=["GET"])
def get_person_photos(person_id):
    """Return a person's profile and all photos containing them."""
    person = Person.query.get(person_id)
    if not person:
        return jsonify({"error": "Person not found"}), 404

    try:
        photo_ids = list({f.photo_id for f in person.faces})
        photos = Photo.query.filter(Photo.id.in_(photo_ids)).order_by(
            Photo.upload_date.desc()
        ).all() if photo_ids else []

        return jsonify({
            "person": person.to_dict(),
            "photos": [p.to_dict() for p in photos],
        }), 200

    except Exception as exc:
        logger.exception("Failed to get person photos")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/faces/persons (convenience — list all people) ────────────────

@bp.route("/persons", methods=["GET"])
def list_persons():
    """Return all known persons with their photo counts."""
    try:
        persons = Person.query.order_by(Person.name).all()
        return jsonify([p.to_dict() for p in persons]), 200
    except Exception as exc:
        logger.exception("Failed to list persons")
        return jsonify({"error": str(exc)}), 500

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
import threading
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.utils import secure_filename

from database.db import db
from models.photo import Photo
from models.album import Album
from utils.auth_helpers import token_required
from utils.activity_helpers import log_activity

logger = logging.getLogger(__name__)
bp = Blueprint("photos", __name__, url_prefix="/api/photos")
analysis_lock = threading.Lock()

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

        # Upload to Cloudinary if configured
        import cloudinary
        import cloudinary.uploader
        
        # Configure Cloudinary
        cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME")
        api_key = current_app.config.get("CLOUDINARY_API_KEY")
        api_secret = current_app.config.get("CLOUDINARY_API_SECRET")
        cloudinary_url = current_app.config.get("CLOUDINARY_URL")
        
        db_file_path = file_path
        
        if cloudinary_url or (cloud_name and api_key and api_secret):
            try:
                if cloudinary_url:
                    cloudinary.config(cloudinary_url=cloudinary_url)
                else:
                    cloudinary.config(
                        cloud_name=cloud_name,
                        api_key=api_key,
                        api_secret=api_secret,
                        secure=True
                    )
                
                # Upload the local file to Cloudinary
                upload_res = cloudinary.uploader.upload(file_path, folder="drishyamitra")
                secure_url = upload_res.get("secure_url")
                if secure_url:
                    db_file_path = secure_url
                    logger.info("Cloudinary upload successful: %s -> %s", file_path, secure_url)
            except Exception as e:
                logger.error("Cloudinary upload failed: %s. Falling back to local storage.", e)

        # Extract date from filename or use today
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Create photo record
        photo = Photo(
            filename=safe_name,
            file_path=db_file_path,
            size=size_str,
            date=today,
            user_id=g.current_user.id,
        )
        db.session.add(photo)
        db.session.commit()
        log_activity(g.current_user.id, "Photo Uploaded", f"Filename: {safe_name}")

        # Run AI analysis pipeline in background thread
        try:
            from services.photo_analysis_service import PhotoAnalysisService
            from routes.faces import active_background_tasks, clustering_status_lock
            import threading
            
            app_obj = current_app._get_current_object()
            user_id = g.current_user.id
            
            with clustering_status_lock:
                active_background_tasks[user_id] = active_background_tasks.get(user_id, 0) + 1
            
            def run_analysis(app, pid, uid, lpath=None):
                try:
                    with analysis_lock:
                        with app.app_context():
                            try:
                                PhotoAnalysisService.analyze_photo(pid, local_path=lpath)
                                logger.info("Background AI analysis complete for photo %s", pid)
                            except Exception as exc:
                                logger.warning("Background AI analysis failed for photo %s: %s", pid, exc)
                finally:
                    with clustering_status_lock:
                        active_background_tasks[uid] = max(0, active_background_tasks.get(uid, 0) - 1)
            
            t = threading.Thread(target=run_analysis, args=(app_obj, photo.id, user_id, file_path))
            t.start()
            logger.info("AI analysis started in background for photo %s", photo.id)
        except Exception as exc:
            logger.warning("Failed to start background AI analysis for photo %s: %s", photo.id, exc)

        result = photo.to_dict()

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
@token_required
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
            # Clean search query: lowercase, trim, and remove trailing punctuation
            clean_search = search_query.lower().strip().rstrip(".?!,")

            # Check if search query matches any recognized person's name
            from models.person import Person
            from models.face import Face
            all_persons = Person.query.filter(Person.user_id == g.current_user.id).all()
            matched_person_ids = []
            for p in all_persons:
                p_name_lower = p.name.lower().strip()
                if clean_search == p_name_lower or clean_search in p_name_lower or p_name_lower in clean_search:
                    matched_person_ids.append(p.id)
            
            if matched_person_ids:
                subquery = db.session.query(Face.photo_id).filter(Face.person_id.in_(matched_person_ids)).subquery()
                photos = Photo.query.filter(Photo.id.in_(subquery), Photo.user_id == g.current_user.id).order_by(Photo.upload_date.desc()).all()
                return jsonify([p.to_dict() for p in photos]), 200

            if clean_search in ("group", "group photo", "group photos"):
                from sqlalchemy import func
                from models.face import Face
                subquery = db.session.query(Face.photo_id).join(Face.photo).filter(
                    Photo.user_id == g.current_user.id
                ).group_by(Face.photo_id).having(func.count(Face.id) > 1).subquery()
                photos = Photo.query.filter(Photo.id.in_(subquery)).order_by(Photo.upload_date.desc()).all()
                return jsonify([p.to_dict() for p in photos]), 200

            photo_ids = []
            try:
                from services.vector_service import VectorService
                photo_ids = VectorService.search_photos(clean_search, limit=50)
            except Exception:
                pass

            if photo_ids:
                photos = Photo.query.filter(Photo.id.in_(photo_ids), Photo.user_id == g.current_user.id).all()
                # Preserve vector search ordering
                id_order = {pid: idx for idx, pid in enumerate(photo_ids)}
                photos.sort(key=lambda p: id_order.get(p.id, 999))
            else:
                # Fallback: structured text search on filename, description, tags
                photos = Photo.query.filter(
                    Photo.user_id == g.current_user.id,
                    db.or_(
                        Photo.filename.ilike(f"%{clean_search}%"),
                        Photo.description.ilike(f"%{clean_search}%"),
                        Photo.location.ilike(f"%{clean_search}%"),
                    )
                ).order_by(Photo.upload_date.desc()).all()

            return jsonify([p.to_dict() for p in photos]), 200

        # Filtered query
        query = Photo.query.filter_by(user_id=g.current_user.id)

        if album_name:
            query = query.join(Photo.albums).filter(Album.name == album_name, Album.user_id == g.current_user.id)

        if favorite:
            query = query.filter(Photo.favorite.is_(True))

        photos = query.order_by(Photo.upload_date.desc()).all()
        return jsonify([p.to_dict() for p in photos]), 200

    except Exception as exc:
        logger.exception("Failed to list photos")
        return jsonify({"error": str(exc)}), 500


# ── GET /api/photos/<id> ──────────────────────────────────────────────────

@bp.route("/<int:photo_id>", methods=["GET"])
@token_required
def get_photo(photo_id):
    """Return detailed metadata for a single photo."""
    photo = Photo.query.filter_by(id=photo_id, user_id=g.current_user.id).first()
    if not photo:
        return jsonify({"error": "Photo not found"}), 404
    return jsonify(photo.to_dict()), 200


# ── DELETE /api/photos/<id> ───────────────────────────────────────────────

@bp.route("/<int:photo_id>", methods=["DELETE"])
@token_required
def delete_photo(photo_id):
    """Delete a photo, its file on disk, and its vector index entry."""
    photo = Photo.query.filter_by(id=photo_id, user_id=g.current_user.id).first()
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    try:
        # Remove file from disk or Cloudinary
        if photo.file_path and photo.file_path.startswith(('http://', 'https://')):
            try:
                import re
                import cloudinary.uploader
                m = re.search(r'/upload/(?:v\d+/)?([^.]+)', photo.file_path)
                if m:
                    public_id = m.group(1)
                    cloudinary.uploader.destroy(public_id)
                    logger.info("Deleted photo from Cloudinary: %s", public_id)
            except Exception as e:
                logger.warning("Failed to delete Cloudinary file %s: %s", photo.file_path, e)
        else:
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
        log_activity(g.current_user.id, "Photo Deleted", f"Filename: {photo.filename}")

        return jsonify({"message": f"Photo {photo_id} deleted"}), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to delete photo %s", photo_id)
        return jsonify({"error": str(exc)}), 500


# ── POST /api/photos/search ───────────────────────────────────────────────

@bp.route("/search", methods=["POST"])
@token_required
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
        persons = Person.query.filter(Person.user_id == g.current_user.id, Person.name.ilike(f"%{query}%")).all()
        for person in persons:
            photo_ids = list({f.photo_id for f in person.faces})
            for pid in photo_ids:
                if pid not in seen_ids:
                    photo = Photo.query.filter_by(id=pid, user_id=g.current_user.id).first()
                    if photo:
                        seen_ids.add(pid)
                        results.append(photo.to_dict())

        # 2 — Structured search: album / location / description
        struct_photos = Photo.query.filter(
            Photo.user_id == g.current_user.id,
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
                    photo = Photo.query.filter_by(id=vid, user_id=g.current_user.id).first()
                    if photo:
                        seen_ids.add(vid)
                        results.append(photo.to_dict())
        except Exception:
            pass

        return jsonify({"query": query, "count": len(results), "results": results}), 200

    except Exception as exc:
        logger.exception("Search failed")
        return jsonify({"error": str(exc)}), 500


# ── POST /api/photos/bulk-delete ──────────────────────────────────────────

@bp.route("/bulk-delete", methods=["POST"])
@token_required
def bulk_delete_photos():
    """Delete multiple photos, their files on disk, and their vector index entries."""
    data = request.get_json(silent=True) or {}
    photo_ids = data.get("photo_ids", [])
    if not photo_ids:
        return jsonify({"error": "photo_ids is required"}), 400

    deleted_count = 0
    try:
        from services.vector_service import VectorService
        for pid in photo_ids:
            photo = Photo.query.filter_by(id=pid, user_id=g.current_user.id).first()
            if not photo:
                continue

            # Remove file from disk or Cloudinary
            if photo.file_path and photo.file_path.startswith(('http://', 'https://')):
                try:
                    import re
                    import cloudinary.uploader
                    m = re.search(r'/upload/(?:v\d+/)?([^.]+)', photo.file_path)
                    if m:
                        public_id = m.group(1)
                        cloudinary.uploader.destroy(public_id)
                        logger.info("Deleted photo from Cloudinary (bulk): %s", public_id)
                except Exception as e:
                    logger.warning("Failed to delete Cloudinary file %s (bulk): %s", photo.file_path, e)
            else:
                if os.path.exists(photo.file_path):
                    try:
                        os.remove(photo.file_path)
                    except Exception as e:
                        logger.warning("Failed to delete file %s: %s", photo.file_path, e)

            # Remove from vector store
            try:
                VectorService.delete_photo(photo.id)
            except Exception:
                pass

            db.session.delete(photo)
            deleted_count += 1

        db.session.commit()
        log_activity(g.current_user.id, "Bulk Photos Deleted", f"Count: {deleted_count}")

        return jsonify({
            "message": f"Successfully deleted {deleted_count} photos",
            "deleted_count": deleted_count
        }), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to delete bulk photos")
        return jsonify({"error": str(exc)}), 500


# ── POST /api/photos/assign-label ─────────────────────────────────────────

@bp.route("/assign-label", methods=["POST"])
@token_required
def assign_label():
    """Manually assign a label (person) to a photo."""
    data = request.get_json(silent=True) or {}
    photo_id = data.get("photo_id")
    label_name = data.get("label_name", "").strip()

    if not photo_id or not label_name:
        return jsonify({"error": "photo_id and label_name are required"}), 400

    try:
        from models.person import Person
        from models.face import Face
        from routes.faces import _pick_palette, _make_initials

        photo = Photo.query.filter_by(id=photo_id, user_id=g.current_user.id).first()
        if not photo:
            return jsonify({"error": "Photo not found"}), 404

        # Find or create person
        person = Person.query.filter(
            Person.user_id == g.current_user.id,
            db.func.lower(Person.name) == label_name.lower()
        ).first()

        if not person:
            palette = _pick_palette(Person.query.filter_by(user_id=g.current_user.id).count())
            person = Person(
                name=label_name,
                user_id=g.current_user.id,
                initials=_make_initials(label_name),
                emoji=palette["emoji"],
                color=palette["color"],
                bg=palette["bg"],
                tags=[],
            )
            db.session.add(person)
            db.session.flush()

        unassigned_faces = [f for f in photo.faces if f.person_id is None]
        
        if unassigned_faces:
            for f in unassigned_faces:
                f.person_id = person.id
                f.is_manually_labeled = True
        else:
            dummy_face = Face(
                photo_id=photo.id,
                person_id=person.id,
                bounding_box={"w":0,"h":0,"x":0,"y":0},
                embedding=[],
                confidence=1.0,
                is_manually_labeled=True
            )
            db.session.add(dummy_face)

        db.session.commit()
        log_activity(g.current_user.id, "Photo Labeled", f"Assigned '{label_name}' to photo")

        return jsonify({
            "message": f"Successfully labeled photo as {label_name}",
            "person": person.to_dict()
        }), 200

    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to assign label")
        return jsonify({"error": str(exc)}), 500


def send_whatsapp_pywhatkit_async(default_contact, image_paths, delivery_id, app):
    with app.app_context():
        import pywhatkit
        import time
        from models.sharing import DeliveryHistory

        th_delivery = DeliveryHistory.query.get(delivery_id)
        if not th_delivery:
            return

        logger.info("Initializing pywhatkit automation background worker...")
        errors = []
        sent_count = 0

        for idx, path in enumerate(image_paths):
            if not os.path.isabs(path):
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                path = os.path.abspath(os.path.join(root_dir, path))
            
            if not os.path.exists(path):
                err_msg = f"Image path does not exist: {path}"
                logger.error(f"[pywhatkit] {err_msg}")
                errors.append(err_msg)
                continue

            try:
                logger.info(f"[pywhatkit] Sending image {idx+1}/{len(image_paths)}: {path} to {default_contact}")
                pywhatkit.sendwhats_image(
                    phone_no=default_contact,
                    img_path=path,
                    wait_time=15,
                    tab_close=True,
                    close_time=3
                )
                logger.info(f"[pywhatkit] Image {idx+1} sent successfully.")
                sent_count += 1
                time.sleep(5)
            except Exception as e:
                err_msg = f"Failed to send image {path}: {str(e)}"
                logger.error(f"[pywhatkit] {err_msg}")
                errors.append(err_msg)

        try:
            if sent_count == len(image_paths):
                th_delivery.status = 'delivered'
                th_delivery.error_message = None
            elif sent_count > 0:
                th_delivery.status = 'delivered'
                th_delivery.error_message = f"Sent {sent_count}/{len(image_paths)}: " + "; ".join(errors)
            else:
                th_delivery.status = 'failed'
                th_delivery.error_message = "; ".join(errors) or "WhatsApp Web connection lost or invalid phone number format"
            db.session.commit()
            logger.info("[pywhatkit] WhatsApp background send finished. Status: %s", th_delivery.status)
        except Exception as db_err:
            logger.error("Failed to update DeliveryHistory for pywhatkit: %s", db_err)


@bp.route("/share-whatsapp-pywhatkit", methods=["POST"])
@token_required
def share_whatsapp_pywhatkit():
    """Trigger background automation worker for pywhatkit WhatsApp sharing."""
    data = request.get_json(silent=True) or {}
    images = data.get("images", [])
    default_contact = data.get("default_contact", "")

    if not default_contact:
        return jsonify({"error": "default_contact is required"}), 400
    if not images:
        return jsonify({"error": "images list is required"}), 400

    try:
        from models.sharing import DeliveryHistory
        # Create a pending delivery history record
        delivery = DeliveryHistory(
            recipient=default_contact,
            platform='whatsapp',
            person_name='Shared Photos',
            photo_count=len(images),
            status='pending',
            user_id=g.current_user.id
        )
        db.session.add(delivery)
        db.session.commit()
        
        delivery_id = delivery.id
        app = current_app._get_current_object()

        threading.Thread(
            target=send_whatsapp_pywhatkit_async,
            args=(default_contact, images, delivery_id, app),
            daemon=True
        ).start()

        return jsonify({
            "status": "success",
            "message": f"WhatsApp sharing worker started in background for {len(images)} photos.",
            "delivery_id": delivery_id
        }), 200
    except Exception as exc:
        logger.exception("Failed to initialize WhatsApp sharing")
        return jsonify({"error": str(exc)}), 500


@bp.route("/share-email", methods=["POST"])
@token_required
def share_email():
    """Trigger SMTP email sharing."""
    data = request.get_json(silent=True) or {}
    images = data.get("images", [])
    recipient = data.get("recipient", "")

    if not recipient:
        return jsonify({"error": "recipient is required"}), 400
    if not images:
        return jsonify({"error": "images list is required"}), 400

    try:
        from models.sharing import DeliveryHistory
        # Create a pending delivery history record
        delivery = DeliveryHistory(
            recipient=recipient,
            platform='email',
            person_name='Shared Photos',
            photo_count=len(images),
            status='pending',
            user_id=g.current_user.id
        )
        db.session.add(delivery)
        db.session.commit()
        
        delivery_id = delivery.id
        app = current_app._get_current_object()

        # Run email sending in a background thread to prevent blocking
        def run_send():
            with app.app_context():
                try:
                    th_delivery = DeliveryHistory.query.get(delivery_id)
                    if not th_delivery:
                        return
                    
                    from services.sharing_service import _send_real_email
                    success, error_msg = _send_real_email(recipient, "Shared Photos", images)
                    th_delivery.status = 'delivered' if success else 'failed'
                    th_delivery.error_message = error_msg
                    db.session.commit()
                    logger.info("[SMTP] Email background send finished. Status: %s", th_delivery.status)
                except Exception as e:
                    logger.error("[SMTP] Failed to send email via background worker: %s", e)
                    try:
                        th_delivery = DeliveryHistory.query.get(delivery_id)
                        if th_delivery:
                            th_delivery.status = 'failed'
                            th_delivery.error_message = str(e)
                            db.session.commit()
                    except Exception:
                        pass

        threading.Thread(target=run_send, daemon=True).start()

        return jsonify({
            "status": "success",
            "message": f"Email sharing worker started in background for {len(images)} photos.",
            "delivery_id": delivery_id
        }), 200
    except Exception as exc:
        logger.exception("Failed to initialize email sharing")
        return jsonify({"error": str(exc)}), 500


@bp.route("/<int:photo_id>/favorite", methods=["POST"])
@token_required
def toggle_favorite(photo_id):
    """Toggle the favorite status of a photo."""
    photo = Photo.query.filter_by(id=photo_id, user_id=g.current_user.id).first()
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    try:
        photo.favorite = not photo.favorite
        db.session.commit()
        log_activity(g.current_user.id, "Photo Favorite Toggled", f"Filename: {photo.filename}, Favorite: {photo.favorite}")
        return jsonify({
            "message": f"Photo favorite status set to {photo.favorite}",
            "favorite": photo.favorite
        }), 200
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to toggle favorite for photo %s", photo_id)
        return jsonify({"error": str(exc)}), 500


@bp.route("/by-label", methods=["GET"])
@token_required
def get_photos_by_label():
    """Fetch absolute file paths of photos for a given person or album label."""
    label = request.args.get("label", "").strip()
    if not label:
        return jsonify({"error": "label query parameter is required"}), 400

    try:
        clean_label = label.lower().strip().rstrip(".?!,")
        from routes.share import resolve_sharing_assets
        paths = resolve_sharing_assets([clean_label], g.current_user.id)
        return jsonify({"paths": paths}), 200
    except Exception as exc:
        logger.exception("Failed to resolve label to photo paths")
        return jsonify({"error": str(exc)}), 500


@bp.route("/dissociate-label", methods=["POST"])
@token_required
def dissociate_label():
    """Dissociate a photo from a person label without deleting the photo."""
    data = request.get_json(silent=True) or {}
    photo_ids = data.get("photo_ids", [])
    person_id = data.get("person_id")

    if not photo_ids and data.get("photo_id"):
        photo_ids = [data.get("photo_id")]

    if not photo_ids or not person_id:
        return jsonify({"error": "photo_ids and person_id are required"}), 400

    try:
        from models.face import Face
        faces = Face.query.join(Face.photo).filter(
            Face.photo_id.in_(photo_ids),
            Face.person_id == person_id,
            Photo.user_id == g.current_user.id
        ).all()

        for face in faces:
            bbox = face.bounding_box
            if bbox and bbox.get("w") == 0 and bbox.get("h") == 0:
                db.session.delete(face)
            else:
                face.person_id = None
                face.is_manually_labeled = False

        db.session.commit()
        return jsonify({"message": "Successfully dissociated photos from person"}), 200
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to dissociate photos from person")
        return jsonify({"error": str(exc)}), 500


@bp.route("/sharing-history", methods=["GET"])
@token_required
def get_sharing_history():
    """Fetch the logged-in user's photo sharing history."""
    from services.sharing_service import SharingService
    try:
        history = SharingService.get_delivery_history(user_id=g.current_user.id)
        return jsonify(history), 200
    except Exception as exc:
        logger.exception("Failed to fetch sharing history")
        return jsonify({"error": str(exc)}), 500


@bp.route("/<int:photo_id>/move-album", methods=["POST"])
@token_required
def move_photo_album(photo_id):
    """Manually move a photo to a specific event album (Birthdays, Weddings, Anniversaries)."""
    photo = Photo.query.filter_by(id=photo_id, user_id=g.current_user.id).first()
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    data = request.get_json(silent=True) or {}
    target_album_name = data.get("album_name")

    try:
        from models.album import Album
        # Find all event albums for this user
        event_albums = Album.query.filter(
            Album.name.in_(["Birthdays", "Weddings", "Anniversaries"]),
            Album.user_id == g.current_user.id
        ).all()

        # Remove the photo from all these event albums first (to 'move' it)
        for album in event_albums:
            if photo in album.photos:
                album.photos.remove(photo)

        # If a target album is specified, add it to that album
        if target_album_name in ["Birthdays", "Weddings", "Anniversaries"]:
            target_album = Album.query.filter_by(name=target_album_name, user_id=g.current_user.id).first()
            if not target_album:
                # Create it if it doesn't exist
                icon_map = {"Birthdays": "🎂", "Weddings": "💍", "Anniversaries": "❤️"}
                color_map = {"Birthdays": "#00897b", "Weddings": "#e8453c", "Anniversaries": "#e91e63"}
                bg_map = {"Birthdays": "#e0f2f1", "Weddings": "#fce8e6", "Anniversaries": "#fde8ef"}
                target_album = Album(
                    name=target_album_name,
                    icon=icon_map.get(target_album_name, "📁"),
                    color=color_map.get(target_album_name, "#1a73e8"),
                    bg=bg_map.get(target_album_name, "#e8f0fe"),
                    user_id=g.current_user.id
                )
                db.session.add(target_album)
                db.session.flush()
            
            if photo not in target_album.photos:
                target_album.photos.append(photo)

        db.session.commit()
        return jsonify({
            "status": "success",
            "message": f"Successfully moved photo to {target_album_name if target_album_name else 'no event album'}."
        }), 200
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to manually move photo album")
        return jsonify({"error": str(exc)}), 500



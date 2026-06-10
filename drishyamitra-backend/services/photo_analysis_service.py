"""
Photo analysis service for Drishyamitra.

Orchestrates the complete AI pipeline that runs when a photo is uploaded:
face detection → person matching → LLM metadata generation → vector indexing.
"""

import json
import logging
import os
import random

from flask import current_app

from database.db import db
from models.face import Face
from models.photo import Photo
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from services.vision_service import VisionService

logger = logging.getLogger(__name__)

# Fallback emoji list used when the LLM is unavailable
_FALLBACK_EMOJIS = ['📷', '🖼️', '🌅', '🏞️', '🎉', '👨‍👩‍👧‍👦', '🌸', '✨']

# Default album suggestions
_ALBUM_OPTIONS = [
    'Family Trips',
    'Weddings',
    'Festivals',
    'Birthdays',
    'Events',
]


class PhotoAnalysisService:
    """Orchestrates the complete AI analysis pipeline for uploaded photos."""

    @staticmethod
    def analyze_photo(photo_id):
        """
        Run the full analysis pipeline on an already-persisted ``Photo``.

        Steps
        -----
        1. Load the ``Photo`` record from the database.
        2. Run ``VisionService.detect_faces()`` on the image file.
        3. For each detected face:
           a. Query all existing faces that already have a ``person_id``.
           b. Use ``EmbeddingService.find_matching_person()`` to check for a
              known person.
           c. Create a ``Face`` record (linked to the matched ``Person`` or
              with ``person_id=None``).
        4. Generate AI caption, tags, and album suggestion via
           ``generate_metadata()``.
        5. Update the ``Photo`` record with the generated metadata.
        6. Index the photo in the vector store for semantic search.
        7. Return a summary dict.

        Args:
            photo_id (int): Primary-key ID of the ``Photo`` to analyse.

        Returns:
            dict: Analysis results with keys ``photo_id``, ``faces_detected``,
            ``faces_matched``, ``description``, ``tags``, ``suggested_album``,
            and ``emoji``.
        """
        # 1. Fetch photo -------------------------------------------------------
        photo = Photo.query.get(photo_id)
        if photo is None:
            logger.error("Photo with id=%s not found.", photo_id)
            return {'error': f'Photo {photo_id} not found.'}

        image_path = photo.file_path
        if not image_path or not os.path.isfile(image_path):
            logger.error("Image file missing for photo %s: %s", photo_id, image_path)
            return {'error': f'Image file not found at {image_path}'}

        faces_detected = 0
        faces_matched = 0
        detected_person_names = []

        # 2. Face detection ----------------------------------------------------
        try:
            raw_faces = VisionService.detect_faces(image_path)
        except Exception as exc:
            logger.error("Face detection failed for photo %s: %s", photo_id, exc)
            raw_faces = []

        # 3. Person matching & Face record creation ----------------------------
        if raw_faces:
            # Pre-load all known faces for this user
            from models.person import Person
            known_faces = (
                Face.query
                .join(Person, Face.person_id == Person.id)
                .filter(Person.user_id == photo.user_id)
                .all()
            )

            # First pass: try matching all faces against known people
            matches = []
            unmatched_indices = []
            
            for idx, face_data in enumerate(raw_faces):
                faces_detected += 1
                embedding = face_data['embedding']
                matched_person = EmbeddingService.find_matching_person(embedding, known_faces)
                
                if matched_person:
                    matches.append((idx, matched_person))
                    faces_matched += 1
                    detected_person_names.append(matched_person.name)
                else:
                    unmatched_indices.append(idx)

            # Second pass: Save Face records (unmatched faces get person_id = None)
            for idx, face_data in enumerate(raw_faces):
                embedding = face_data['embedding']
                bounding_box = face_data['bounding_box']
                confidence = face_data['confidence']
                
                matched_p = next((m[1] for m in matches if m[0] == idx), None)
                
                new_face = Face(
                    photo_id=photo_id,
                    person_id=matched_p.id if matched_p else None,
                    bounding_box=bounding_box,
                    embedding=embedding,
                    confidence=confidence,
                )
                if matched_p:
                    new_face.person = matched_p
                db.session.add(new_face)
                known_faces.append(new_face)

            try:
                db.session.flush()
            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to persist face records: %s", exc)

        # 4. AI metadata generation --------------------------------------------
        metadata = PhotoAnalysisService.generate_metadata(
            filename=photo.filename or '',
            detected_names=detected_person_names,
            image_path=image_path,
        )

        description = metadata.get('description', '')
        tags = metadata.get('tags', [])
        confidence = metadata.get('confidence', 0.0)
        
        # Filter tags to fix label explosion
        if confidence < 0.85:
            tags = []
        else:
            tags = tags[:3]

        suggested_album = metadata.get('folder', '')
        emoji = random.choice(_FALLBACK_EMOJIS)

        # 5. Update photo record -----------------------------------------------
        try:
            from services.scene_clustering_service import SceneClusteringService
            bg_hist = SceneClusteringService.compute_color_histogram(image_path)
            photo.background_features = bg_hist
            photo.description = description
            photo.tags = tags
            photo.emoji = emoji
            db.session.commit()

            # Run event auto-categorisation
            try:
                auto_categorize_event_album(photo, suggested_album)
            except Exception as ev_err:
                logger.error("Failed to auto-categorise photo %d: %s", photo_id, ev_err)

        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to update photo %s metadata: %s", photo_id, exc)

        # 6. Vector-store indexing ---------------------------------------------
        try:
            VectorService.index_photo(photo_id, description, tags)
        except Exception as exc:
            logger.error("Vector indexing failed for photo %s: %s", photo_id, exc)

        # 6.5 Run DBSCAN clustering pipeline automatically -----------------------
        try:
            from routes.faces import run_face_clustering
            app_obj = current_app._get_current_object()
            run_face_clustering(app_obj, photo.user_id)
            logger.info("Auto-clustering completed successfully after upload for photo %s", photo_id)
        except Exception as exc:
            logger.error("Auto-clustering failed after upload for photo %s: %s", photo_id, exc)

        # 6.6 Run Places & Scenes clustering automatically -----------------------
        try:
            from services.scene_clustering_service import SceneClusteringService
            SceneClusteringService.cluster_photo_by_scene(photo)
            logger.info("Scene-clustering completed successfully after upload for photo %s", photo_id)
        except Exception as exc:
            logger.error("Scene-clustering failed after upload for photo %s: %s", photo_id, exc)

        # 7. Return summary ----------------------------------------------------
        result = {
            'photo_id': photo_id,
            'faces_detected': faces_detected,
            'faces_matched': faces_matched,
            'description': description,
            'tags': tags,
            'suggested_album': suggested_album,
            'emoji': emoji,
        }
        logger.info("Analysis complete for photo %s: %s", photo_id, result)
        return result

    @staticmethod
    def generate_metadata(filename, detected_names, image_path=None):
        """
        Use OpenAI GPT-4o-mini Vision API to generate photo description, tags,
        and a suggested album folder based on the image's background/context.

        If the API is unavailable or the call fails, a deterministic fallback
        based on the filename is returned instead.

        Args:
            filename (str): Original filename of the uploaded photo.
            detected_names (list[str]): Names of people detected in the photo.
            image_path (str, optional): Path to the image file on disk.

        Returns:
            dict: With keys ``description`` (str), ``tags`` (list[str]),
            `folder` (str), and `confidence` (float).
        """
        names_str = ', '.join(detected_names) if detected_names else 'none'

        try:
            import base64
            from openai import OpenAI

            api_key = current_app.config.get('OPENAI_API_KEY', '')
            if not api_key:
                logger.warning("OPENAI_API_KEY is not set – using fallback metadata.")
                return _fallback_metadata(filename, detected_names)

            if not image_path or not os.path.isfile(image_path):
                logger.warning("No image path provided or file not found – using fallback metadata.")
                return _fallback_metadata(filename, detected_names)

            # Read image file and encode to base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            # Determine mime type
            mime_type = "image/jpeg"
            if image_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif image_path.lower().endswith(".gif"):
                mime_type = "image/gif"
            elif image_path.lower().endswith(".webp"):
                mime_type = "image/webp"

            prompt = (
                f"You are a photo analyzer. Given a photo file name '{filename}' "
                f"and detected people '{names_str}', analyze the image background and context. "
                "Describe the context/background (e.g. 'beach', 'birthday party', 'wedding', 'anniversary party', 'park').\n"
                "Provide:\n"
                "1. A short natural caption (2 sentences max)\n"
                "2. 3 to 5 relevant tags\n"
                "3. Suggest an album from: "
                "['Family Trips', 'Weddings', 'Festivals', 'Birthdays', 'Anniversaries', 'Events']\n"
                "Return JSON ONLY (no markdown formatting fences, just raw JSON):\n"
                '{"description": "...", "tags": [...], "folder": "...", "confidence": 0.XX}'
            )

            client = OpenAI(api_key=api_key)
            chat_completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300,
                temperature=0.4
            )

            raw_text = chat_completion.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw_text.startswith('```'):
                lines = raw_text.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                raw_text = '\n'.join(lines).strip()

            parsed = json.loads(raw_text)

            return {
                'description': str(parsed.get('description', '')),
                'tags': list(parsed.get('tags', [])),
                'folder': str(parsed.get('folder', '')),
                'confidence': float(parsed.get('confidence', 0.9)),
            }

        except ImportError:
            logger.warning(
                "openai package not installed – using fallback metadata. "
                "Install with: pip install openai"
            )
            return _fallback_metadata(filename, detected_names)

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse OpenAI Vision response as JSON: %s", exc)
            return _fallback_metadata(filename, detected_names)

        except Exception as exc:
            logger.error("OpenAI Vision API call failed: %s", exc)
            return _fallback_metadata(filename, detected_names)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fallback_metadata(filename, detected_names):
    """
    Generate basic metadata from the filename when the LLM is unavailable.

    Args:
        filename (str): Original image filename.
        detected_names (list[str]): Names of detected people (may be empty).

    Returns:
        dict: Fallback metadata dict.
    """
    base = os.path.splitext(filename)[0] if filename else 'photo'
    # Replace common separators with spaces for a human-readable description
    readable = base.replace('_', ' ').replace('-', ' ').strip()

    if detected_names:
        description = f"A photo featuring {', '.join(detected_names)}."
    else:
        description = f"A photo: {readable}."

    # Derive rudimentary tags from the filename
    tags = [
        token.lower()
        for token in readable.split()
        if len(token) > 2
    ][:5]

    if not tags:
        tags = ['photo', 'upload']

    return {
        'description': description,
        'tags': tags,
        'folder': 'Events',
        'confidence': 0.3,
    }


def auto_categorize_event_album(photo, suggested_album=None):
    """Automatically categorize photo into event albums: 'Birthdays', 'Weddings', 'Anniversaries'."""
    text_parts = [
        photo.description or '',
        ' '.join(photo.tags or []),
        photo.filename or '',
        photo.location or ''
    ]
    text = ' '.join(text_parts).lower()
    
    event_name = None
    if suggested_album:
        folder_clean = suggested_album.lower()
        if "wedding" in folder_clean or "marriage" in folder_clean or "ceremony" in folder_clean:
            event_name = "Weddings"
        elif "birthday" in folder_clean or "party" in folder_clean:
            event_name = "Birthdays"
        elif "anniversary" in folder_clean:
            event_name = "Anniversaries"
            
    if not event_name:
        birthday_kws = ["birthday", "cake", "bday", "candles", "balloons", "celebration", "gift", "wish", "born", "years old", "celebrate"]
        wedding_kws = ["wedding", "marriage", "bride", "groom", "reception", "ceremony", "couple", "husband", "wife", "garland", "haldi", "mehendi", "sangeet", "marriage anniversary"]
        anniversary_kws = ["anniversary", "anniversaries", "milestone", "celebrating years", "togetherness", "wedding day", "jubilee"]
        
        if any(k in text for k in anniversary_kws):
            event_name = "Anniversaries"
        elif any(k in text for k in wedding_kws):
            event_name = "Weddings"
        elif any(k in text for k in birthday_kws):
            event_name = "Birthdays"

    if not event_name and photo.background_features:
        from models.album import Album
        from services.scene_clustering_service import SceneClusteringService
        for target_name in ["Birthdays", "Weddings", "Anniversaries"]:
            album = Album.query.filter_by(name=target_name, user_id=photo.user_id).first()
            if album and album.photos:
                for op in album.photos:
                    if op.id != photo.id and op.background_features:
                        sim = SceneClusteringService.calculate_similarity(photo.background_features, op.background_features)
                        if sim >= 0.75:
                            event_name = target_name
                            break
            if event_name:
                break

    if event_name:
        from models.album import Album
        album = Album.query.filter_by(name=event_name, user_id=photo.user_id).first()
        if not album:
            icon_map = {"Birthdays": "🎂", "Weddings": "💍", "Anniversaries": "❤️"}
            color_map = {"Birthdays": "#00897b", "Weddings": "#e8453c", "Anniversaries": "#e91e63"}
            bg_map = {"Birthdays": "#e0f2f1", "Weddings": "#fce8e6", "Anniversaries": "#fde8ef"}
            album = Album(
                name=event_name,
                icon=icon_map.get(event_name, "📁"),
                color=color_map.get(event_name, "#1a73e8"),
                bg=bg_map.get(event_name, "#e8f0fe"),
                user_id=photo.user_id
            )
            db.session.add(album)
            db.session.flush()
        
        if photo not in album.photos:
            album.photos.append(photo)
            db.session.commit()
            logger.info("Automatically categorized photo %d into event album '%s'", photo.id, event_name)

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
            # Pre-load all known faces (those with an assigned person)
            known_faces = (
                Face.query
                .filter(Face.person_id.isnot(None))
                .all()
            )

            for face_data in raw_faces:
                faces_detected += 1
                embedding = face_data['embedding']
                bounding_box = face_data['bounding_box']
                confidence = face_data['confidence']

                matched_person = EmbeddingService.find_matching_person(
                    embedding, known_faces
                )

                new_face = Face(
                    photo_id=photo_id,
                    person_id=matched_person.id if matched_person else None,
                    bounding_box=bounding_box,
                    embedding=embedding,
                    confidence=confidence,
                )
                db.session.add(new_face)

                if matched_person:
                    faces_matched += 1
                    detected_person_names.append(matched_person.name)
                    logger.info(
                        "Face in photo %s matched to person '%s' (id=%s).",
                        photo_id,
                        matched_person.name,
                        matched_person.id,
                    )

            try:
                db.session.flush()
            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to persist face records: %s", exc)

        # 4. AI metadata generation --------------------------------------------
        metadata = PhotoAnalysisService.generate_metadata(
            filename=photo.filename or '',
            detected_names=detected_person_names,
        )

        description = metadata.get('description', '')
        tags = metadata.get('tags', [])
        suggested_album = metadata.get('folder', '')
        emoji = random.choice(_FALLBACK_EMOJIS)

        # 5. Update photo record -----------------------------------------------
        try:
            photo.description = description
            photo.tags = tags
            photo.emoji = emoji
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to update photo %s metadata: %s", photo_id, exc)

        # 6. Vector-store indexing ---------------------------------------------
        try:
            VectorService.index_photo(photo_id, description, tags)
        except Exception as exc:
            logger.error("Vector indexing failed for photo %s: %s", photo_id, exc)

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
    def generate_metadata(filename, detected_names):
        """
        Use Groq API (Llama 3.3 70B) to generate photo description, tags,
        and a suggested album folder.

        If the API is unavailable or the call fails, a deterministic fallback
        based on the filename is returned instead.

        Args:
            filename (str): Original filename of the uploaded photo.
            detected_names (list[str]): Names of people detected in the photo.

        Returns:
            dict: With keys ``description`` (str), ``tags`` (list[str]),
            ``folder`` (str), and ``confidence`` (float).
        """
        names_str = ', '.join(detected_names) if detected_names else 'none'

        prompt = (
            f"You are a photo analyzer. Given a photo file name '{filename}' "
            f"and detected people '{names_str}', generate:\n"
            "1. A short natural caption (2 sentences max)\n"
            "2. 3 to 5 relevant tags\n"
            "3. Suggest an album from: "
            "['Family Trips', 'Weddings', 'Festivals', 'Birthdays', 'Events']\n"
            'Return JSON ONLY: '
            '{"description": "...", "tags": [...], "folder": "...", '
            '"confidence": 0.XX}'
        )

        try:
            from groq import Groq

            api_key = current_app.config.get('GROQ_API_KEY', '')
            if not api_key:
                logger.warning("GROQ_API_KEY is not set – using fallback metadata.")
                return _fallback_metadata(filename, detected_names)

            model = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

            client = Groq(api_key=api_key)
            chat_completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a helpful photo analysis assistant. '
                            'Always respond with valid JSON only.'
                        ),
                    },
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.4,
                max_tokens=256,
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
                'confidence': float(parsed.get('confidence', 0.5)),
            }

        except ImportError:
            logger.warning(
                "groq package not installed – using fallback metadata. "
                "Install with: pip install groq"
            )
            return _fallback_metadata(filename, detected_names)

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Groq response as JSON: %s", exc)
            return _fallback_metadata(filename, detected_names)

        except Exception as exc:
            logger.error("Groq API call failed: %s", exc)
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

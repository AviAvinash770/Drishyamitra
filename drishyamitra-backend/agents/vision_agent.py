"""
Vision agent – answers visual queries about photos such as face counts,
person identification, and face-recognition statistics.

This agent does *not* run inference itself; it queries the pre-computed
``Face`` and ``Person`` tables populated by the face-recognition pipeline
and surfaces the results as natural-language answers.
"""

import logging
from typing import Dict, Any, List

from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face

logger = logging.getLogger(__name__)


class VisionAgent:
    """Handles visual queries about photos."""

    @staticmethod
    def run(state: Dict[str, Any]) -> Dict[str, Any]:
        """Answer visual queries about one or more photos.

        Capabilities:
        * Count faces in the photos identified by ``state['photo_ids']``.
        * List people recognised in those photos.
        * Provide aggregate face-recognition statistics when no specific
          photos are referenced.

        Parameters
        ----------
        state : dict
            Shared workflow state.

        Returns
        -------
        dict
            Updated state with ``response_text`` and ``action_logs``.
        """
        query: str = state.get("user_query", "").lower()
        action_logs: list = list(state.get("action_logs", []))
        photo_ids: List[int] = list(state.get("photo_ids", []))

        try:
            if photo_ids:
                response = VisionAgent._analyse_photos(photo_ids)
            else:
                # No specific photos – provide library-wide stats
                response = VisionAgent._global_stats()

            action_logs.append(
                f"[vision] Answered visual query for {len(photo_ids) or 'all'} photos."
            )

        except Exception as exc:
            logger.error("VisionAgent error: %s", exc, exc_info=True)
            response = "An error occurred while analysing photos."
            action_logs.append(f"[vision] Error: {exc}")

        state["response_text"] = response
        state["action_logs"] = action_logs
        return state

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _analyse_photos(photo_ids: List[int]) -> str:
        """Return a detailed breakdown for the given photo IDs."""
        parts: List[str] = []
        total_faces = 0
        identified: Dict[str, int] = {}  # person_name → count
        unidentified = 0

        for pid in photo_ids:
            photo = Photo.query.get(pid)
            if not photo:
                continue

            faces = Face.query.filter_by(photo_id=pid).all()
            face_count = len(faces)
            total_faces += face_count

            photo_label = getattr(photo, "filename", None) or f"Photo #{pid}"

            if face_count == 0:
                parts.append(f"• **{photo_label}** – no faces detected.")
                continue

            names: List[str] = []
            for face in faces:
                if face.person_id:
                    person = Person.query.get(face.person_id)
                    name = person.name if person and person.name else "Unknown"
                    names.append(name)
                    identified[name] = identified.get(name, 0) + 1
                else:
                    names.append("Unidentified")
                    unidentified += 1

            parts.append(
                f"• **{photo_label}** – {face_count} face(s): {', '.join(names)}"
            )

        # Build summary header
        header_parts = [f"Analysed **{len(photo_ids)}** photo(s)."]
        header_parts.append(f"Total faces detected: **{total_faces}**.")
        if identified:
            header_parts.append(
                "Recognised people: "
                + ", ".join(f"{n} ({c})" for n, c in identified.items())
                + "."
            )
        if unidentified:
            header_parts.append(f"Unidentified faces: **{unidentified}**.")

        return "\n".join(header_parts) + "\n\n" + "\n".join(parts)

    @staticmethod
    def _global_stats() -> str:
        """Return library-wide face-recognition statistics."""
        total_photos = Photo.query.count()
        total_faces = Face.query.count()
        total_persons = Person.query.count()

        # Photos with at least one face
        photos_with_faces = (
            db.session.query(Face.photo_id)
            .distinct()
            .count()
        )

        # Identified vs unidentified faces
        identified_faces = Face.query.filter(Face.person_id.isnot(None)).count()
        unidentified_faces = total_faces - identified_faces

        lines = [
            "📊 **Photo Library Statistics**",
            f"• Total photos: **{total_photos}**",
            f"• Photos with faces: **{photos_with_faces}**",
            f"• Total faces detected: **{total_faces}**",
            f"• Identified faces: **{identified_faces}**",
            f"• Unidentified faces: **{unidentified_faces}**",
            f"• Known people: **{total_persons}**",
        ]
        return "\n".join(lines)

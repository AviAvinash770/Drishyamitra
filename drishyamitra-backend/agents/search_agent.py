"""
Search agent – finds photos through structured DB queries and semantic
vector search, then merges the results into a single deduplicated list.

Search strategy (executed in order):
1. **Person match** – if the query mentions a known person name, fetch
   their photo IDs via the ``Face`` table.
2. **Date / year match** – if the query contains a 4-digit year or a
   recognisable date fragment, filter the ``Photo`` table accordingly.
3. **Album match** – if the query mentions an album name, pull photos
   belonging to that album.
4. **Semantic search** – always run ``VectorService.search_photos`` to
   catch anything the structured filters missed.

Results from steps 1–3 are placed first (structured hits are higher
confidence), followed by any new IDs from step 4.
"""

import logging
import re
from typing import Dict, Any, List, Set

from flask import current_app
from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face
from models.album import Album, photo_album
from services.vector_service import VectorService

logger = logging.getLogger(__name__)

# Regex to find 4-digit years in queries
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Regex to find date patterns like "2024-03", "March 2024", etc.
_MONTH_YEAR_RE = re.compile(
    r"\b(?:(?P<y1>\d{4})-(?P<m1>\d{1,2}))"             # 2024-03
    r"|(?:(?P<m2>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"\s+(?P<y2>\d{4}))\b",
    re.IGNORECASE,
)

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class SearchAgent:
    """Handles photo search queries using both structured DB and semantic vector search."""

    @staticmethod
    def run(state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the multi-strategy search pipeline.

        Updates *state* with:
        * ``photo_ids`` – ordered list of matching photo IDs.
        * ``response_text`` – human-readable summary of results.
        * ``action_logs`` – appended with a search summary entry.

        Parameters
        ----------
        state : dict
            Shared workflow state containing at least ``user_query``.

        Returns
        -------
        dict
            The updated state.
        """
        query: str = state.get("user_query", "")
        action_logs: list = list(state.get("action_logs", []))
        structured_ids: List[int] = []
        semantic_ids: List[int] = []
        search_details: List[str] = []

        try:
            # ── 1. Person-name search ────────────────────────────────────
            person_ids_found = SearchAgent._search_by_person(query)
            if person_ids_found:
                structured_ids.extend(person_ids_found)
                search_details.append(f"person match ({len(person_ids_found)} photos)")

            # ── 2. Date / year search ────────────────────────────────────
            date_ids = SearchAgent._search_by_date(query)
            if date_ids:
                structured_ids.extend(date_ids)
                search_details.append(f"date match ({len(date_ids)} photos)")

            # ── 3. Album-name search ─────────────────────────────────────
            album_ids = SearchAgent._search_by_album(query)
            if album_ids:
                structured_ids.extend(album_ids)
                search_details.append(f"album match ({len(album_ids)} photos)")

            # ── 4. Semantic vector search ────────────────────────────────
            # Only run semantic search if no structured hits were found!
            if not structured_ids:
                try:
                    sem_results = VectorService.search_photos(query, limit=10)
                    if sem_results:
                        semantic_ids = [int(pid) for pid in sem_results]
                        search_details.append(f"semantic match ({len(semantic_ids)} photos)")
                except Exception as vec_err:
                    logger.warning("VectorService search failed: %s", vec_err)
                    search_details.append("semantic search unavailable")

            # ── Merge & deduplicate (structured first) ───────────────────
            seen: Set[int] = set()
            merged: List[int] = []
            for pid in structured_ids + semantic_ids:
                if pid not in seen:
                    seen.add(pid)
                    merged.append(pid)

            # Build response text
            if merged:
                photo_count = len(merged)
                response = f"I found {photo_count} photo{'s' if photo_count != 1 else ''}"
                if search_details:
                    response += f" ({', '.join(search_details)})"
                response += "."
            else:
                response = (
                    "I couldn't find any photos matching your query. "
                    "Try rephrasing or being more specific."
                )

            action_logs.append(f"[search] Found {len(merged)} photos via: {', '.join(search_details) or 'none'}")

        except Exception as exc:
            logger.error("SearchAgent error: %s", exc, exc_info=True)
            merged = []
            response = "An error occurred while searching for photos. Please try again."
            action_logs.append(f"[search] Error: {exc}")

        state["photo_ids"] = merged
        state["response_text"] = response
        state["action_logs"] = action_logs
        return state

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _search_by_person(query: str) -> List[int]:
        """Find photo IDs for any person whose name appears in the query.

        Uses a case-insensitive ``LIKE`` match against all known person
        names so that partial matches (e.g. *"Ravi"* matching
        *"Ravi Kumar"*) are also captured.
        """
        photo_ids: List[int] = []
        try:
            persons = Person.query.all()
            for person in persons:
                if person.name and person.name.lower() in query.lower():
                    face_rows = Face.query.filter_by(person_id=person.id).all()
                    for face in face_rows:
                        if face.photo_id and face.photo_id not in photo_ids:
                            photo_ids.append(face.photo_id)
        except Exception as exc:
            logger.warning("Person-name search failed: %s", exc)
        return photo_ids

    @staticmethod
    def _search_by_date(query: str) -> List[int]:
        """Extract date / year references from the query and filter photos."""
        photo_ids: List[int] = []
        try:
            # Try month + year first
            m = _MONTH_YEAR_RE.search(query)
            if m:
                if m.group("y1") and m.group("m1"):
                    year, month = int(m.group("y1")), int(m.group("m1"))
                elif m.group("y2") and m.group("m2"):
                    year = int(m.group("y2"))
                    month = _MONTH_MAP.get(m.group("m2")[:3].lower(), 0)
                else:
                    year, month = None, None

                if year and month:
                    photos = Photo.query.filter(
                        db.extract("year", Photo.created_at) == year,
                        db.extract("month", Photo.created_at) == month,
                    ).all()
                    photo_ids.extend(p.id for p in photos)
                    return photo_ids

            # Fall back to year-only
            year_match = _YEAR_RE.search(query)
            if year_match:
                year = int(year_match.group())
                photos = Photo.query.filter(
                    db.extract("year", Photo.created_at) == year
                ).all()
                photo_ids.extend(p.id for p in photos)
        except Exception as exc:
            logger.warning("Date search failed: %s", exc)
        return photo_ids

    @staticmethod
    def _search_by_album(query: str) -> List[int]:
        """Match query text against album names and return member photo IDs."""
        photo_ids: List[int] = []
        try:
            albums = Album.query.all()
            for album in albums:
                if album.name and album.name.lower() in query.lower():
                    rows = (
                        db.session.query(photo_album.c.photo_id)
                        .filter(photo_album.c.album_id == album.id)
                        .all()
                    )
                    photo_ids.extend(r[0] for r in rows)
        except Exception as exc:
            logger.warning("Album search failed: %s", exc)
        return photo_ids

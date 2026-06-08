"""
Memory agent – resolves person references mentioned in the user query
and surfaces relationship / recognition metadata.

Capabilities:
* Case-insensitive fuzzy name lookup using SQL ``LIKE``.
* Aggregates per-person statistics: photo count, tag list, relationship
  label (if stored).
* Populates *state['person_ids']* so downstream agents can act on
  resolved identities.
"""

import logging
from typing import Dict, Any, List

from database.db import db
from models.person import Person
from models.face import Face
from models.photo import Photo

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Resolves person references and manages relationship context.

    The memory agent is invoked when the orchestrator detects that the
    user is asking about *who* someone is, how many photos they appear in,
    or any relationship-related query.
    """

    @staticmethod
    def run(state: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve person names mentioned in the user query.

        Resolution pipeline:
        1. Tokenise the query and try exact (case-insensitive) matches.
        2. If no exact match is found, fall back to ``LIKE '%token%'``
           across the ``Person.name`` column.
        3. For every matched person, collect:
           - ``photo_count`` – number of photos they appear in.
           - ``tags`` – any tags / labels associated with their faces.
           - ``relationship`` – stored relationship label, if any.

        State updates
        -------------
        * ``person_ids`` – list of resolved ``Person.id`` values.
        * ``response_text`` – human-readable summary.
        * ``action_logs`` – appended with resolution details.

        Parameters
        ----------
        state : dict
            Shared workflow state.

        Returns
        -------
        dict
            Updated state.
        """
        query: str = state.get("user_query", "")
        action_logs: list = list(state.get("action_logs", []))
        matched_persons: List[Dict[str, Any]] = []
        person_ids: List[int] = []

        try:
            matched_persons = MemoryAgent._resolve_persons(query)

            if matched_persons:
                person_ids = [p["id"] for p in matched_persons]
                parts: List[str] = []
                for p in matched_persons:
                    desc = f"**{p['name']}** – appears in {p['photo_count']} photo(s)"
                    if p.get("relationship"):
                        desc += f" (relationship: {p['relationship']})"
                    if p.get("tags"):
                        desc += f" [tags: {', '.join(p['tags'])}]"
                    parts.append(desc)

                response = "Here's what I know:\n" + "\n".join(f"• {d}" for d in parts)
            else:
                response = (
                    "I couldn't find anyone matching that name in the photo library. "
                    "Make sure the person has been identified in at least one photo."
                )

            action_logs.append(
                f"[memory] Resolved {len(person_ids)} person(s): "
                f"{[p['name'] for p in matched_persons]}"
            )

        except Exception as exc:
            logger.error("MemoryAgent error: %s", exc, exc_info=True)
            response = "An error occurred while looking up person information."
            action_logs.append(f"[memory] Error: {exc}")

        state["person_ids"] = person_ids
        state["response_text"] = response
        state["action_logs"] = action_logs
        return state

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_persons(query: str) -> List[Dict[str, Any]]:
        """Return metadata dicts for all persons whose name fuzzy-matches the query.

        Each returned dict contains:
        ``id``, ``name``, ``photo_count``, ``relationship``, ``tags``.
        """
        results: List[Dict[str, Any]] = []
        seen_ids: set = set()

        all_persons = Person.query.all()

        for person in all_persons:
            if not person.name:
                continue

            # Case-insensitive substring check
            if person.name.lower() not in query.lower():
                continue

            if person.id in seen_ids:
                continue
            seen_ids.add(person.id)

            # Aggregate stats
            face_rows = Face.query.filter_by(person_id=person.id).all()
            photo_ids = list({f.photo_id for f in face_rows if f.photo_id})
            photo_count = len(photo_ids)

            # Collect unique tags from faces (if the column exists)
            tags: List[str] = []
            for face in face_rows:
                tag = getattr(face, "tag", None) or getattr(face, "label", None)
                if tag and tag not in tags:
                    tags.append(tag)

            # Relationship label (if Person model has one)
            relationship = getattr(person, "relationship", None) or ""

            results.append({
                "id": person.id,
                "name": person.name,
                "photo_count": photo_count,
                "relationship": relationship,
                "tags": tags,
            })

        # If direct substring matching found nothing, try LIKE on each word
        if not results:
            results = MemoryAgent._fuzzy_word_search(query, seen_ids)

        return results

    @staticmethod
    def _fuzzy_word_search(query: str, exclude_ids: set) -> List[Dict[str, Any]]:
        """Fall-back: split query into words and run ``LIKE`` for each."""
        results: List[Dict[str, Any]] = []
        words = [w for w in query.split() if len(w) >= 3]

        for word in words:
            pattern = f"%{word}%"
            matches = Person.query.filter(
                Person.name.ilike(pattern)
            ).all()

            for person in matches:
                if person.id in exclude_ids:
                    continue
                exclude_ids.add(person.id)

                face_rows = Face.query.filter_by(person_id=person.id).all()
                photo_ids = list({f.photo_id for f in face_rows if f.photo_id})

                tags: List[str] = []
                for face in face_rows:
                    tag = getattr(face, "tag", None) or getattr(face, "label", None)
                    if tag and tag not in tags:
                        tags.append(tag)

                results.append({
                    "id": person.id,
                    "name": person.name,
                    "photo_count": len(photo_ids),
                    "relationship": getattr(person, "relationship", None) or "",
                    "tags": tags,
                })

        return results

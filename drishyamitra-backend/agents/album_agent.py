"""
Album agent – manages album creation, photo assignment, and automatic
photo grouping.

Interactive flow:
1. Parse the desired album name from the user query via LLM or keyword
   extraction.
2. Create the album if it does not already exist.
3. If the workflow state already contains ``photo_ids`` (e.g. populated
   by a preceding search step), assign those photos to the album.

Auto-grouping (``auto_group_photos``):
* Groups ungrouped photos by **date** (month/year), **person**, and
  **location** (if geo-data is available).
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import current_app
from groq import Groq

from database.db import db
from models.photo import Photo
from models.album import Album, photo_album
from models.face import Face
from models.person import Person

logger = logging.getLogger(__name__)


class AlbumAgent:
    """Manages album creation and photo grouping."""

    @staticmethod
    def run(state: Dict[str, Any]) -> Dict[str, Any]:
        """Create an album and/or assign photos based on the user query.

        Pipeline:
        1. Extract album name from the query (LLM-assisted, with regex
           fallback).
        2. Find or create the ``Album`` row.
        3. If ``state['photo_ids']`` is non-empty, add those photos to
           the album.  Otherwise, attempt a lightweight search so the
           album is not empty.
        4. Populate ``state['album_id']``, ``state['response_text']``.

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
        user_id: int = state.get("user_id")
        action_logs: list = list(state.get("action_logs", []))
        photo_ids: List[int] = list(state.get("photo_ids", []))

        try:
            album_name = AlbumAgent._extract_album_name(query)
            if not album_name:
                state["response_text"] = (
                    "I couldn't determine an album name from your request. "
                    "Please specify a name, e.g. 'Create an album called Summer Vacation'."
                )
                action_logs.append("[album] Could not extract album name.")
                state["action_logs"] = action_logs
                return state

            # Find or create album scoped to user
            album = Album.query.filter(
                Album.user_id == user_id,
                db.func.lower(Album.name) == album_name.lower()
            ).first()

            created = False
            if not album:
                album = Album(name=album_name, user_id=user_id)
                db.session.add(album)
                db.session.flush()  # get album.id
                created = True

            # Assign photos
            assigned_count = AlbumAgent._assign_photos(album, photo_ids)

            db.session.commit()

            # Response
            verb = "Created" if created else "Updated"
            response = f"{verb} album **{album.name}**"
            if assigned_count:
                response += f" and added {assigned_count} photo(s) to it."
            else:
                response += "."

            action_logs.append(
                f"[album] {verb} album '{album.name}' (id={album.id}), "
                f"assigned {assigned_count} photo(s)."
            )
            state["album_id"] = album.id

        except Exception as exc:
            db.session.rollback()
            logger.error("AlbumAgent error: %s", exc, exc_info=True)
            response = "An error occurred while managing the album. Please try again."
            action_logs.append(f"[album] Error: {exc}")

        state["response_text"] = response
        state["action_logs"] = action_logs
        return state

    # ── Auto-grouping ────────────────────────────────────────────────────────

    @staticmethod
    def auto_group_photos(user_id=None) -> Dict[str, Any]:
        """Automatically group ungrouped photos into albums.

        Grouping strategies (applied in order):
        1. **Date** – by month/year of ``captured_at``.
        2. **Person** – photos containing the same identified person.
        3. **Location** – by ``location`` field (if populated).

        Returns
        -------
        dict
            Summary of created albums and photo assignments.
        """
        summary: Dict[str, Any] = {"albums_created": 0, "photos_assigned": 0, "details": []}

        try:
            # Identify photos not in any album (for this user)
            assigned_photo_ids = {
                row[0]
                for row in db.session.query(photo_album.c.photo_id)
                .join(Photo, Photo.id == photo_album.c.photo_id)
                .filter(Photo.user_id == user_id)
                .all()
            }
            all_photos = Photo.query.filter_by(user_id=user_id).all()
            ungrouped = [p for p in all_photos if p.id not in assigned_photo_ids]

            if not ungrouped:
                summary["details"].append("All photos are already in albums.")
                return summary

            # ── Strategy 1: Group by month/year ──────────────────────────
            date_groups: Dict[str, List[int]] = defaultdict(list)
            no_date: List[Photo] = []
            for photo in ungrouped:
                captured = getattr(photo, "created_at", None)
                if captured and isinstance(captured, datetime):
                    key = captured.strftime("%B %Y")  # e.g. "March 2024"
                    date_groups[key].append(photo.id)
                else:
                    no_date.append(photo)

            for label, pids in date_groups.items():
                if len(pids) < 2:
                    continue
                album_name = f"Photos – {label}"
                album = Album.query.filter(
                    Album.user_id == user_id,
                    db.func.lower(Album.name) == album_name.lower()
                ).first()
                if not album:
                    album = Album(name=album_name, user_id=user_id)
                    db.session.add(album)
                    db.session.flush()
                    summary["albums_created"] += 1

                count = AlbumAgent._assign_photos(album, pids)
                summary["photos_assigned"] += count
                summary["details"].append(f"Date group '{album_name}': {count} photos")

            # ── Strategy 2: Group by person ──────────────────────────────
            person_groups: Dict[int, List[int]] = defaultdict(list)
            for photo in ungrouped:
                faces = Face.query.join(Face.photo).filter(Face.photo_id == photo.id, Photo.user_id == user_id).all()
                for face in faces:
                    if face.person_id:
                        person_groups[face.person_id].append(photo.id)

            for person_id, pids in person_groups.items():
                unique_pids = list(set(pids))
                if len(unique_pids) < 2:
                    continue
                person = Person.query.filter_by(id=person_id, user_id=user_id).first()
                if not person:
                    continue
                person_name = person.name if person.name else f"Person {person_id}"
                album_name = f"Photos of {person_name}"
                album = Album.query.filter(
                    Album.user_id == user_id,
                    db.func.lower(Album.name) == album_name.lower()
                ).first()
                if not album:
                    album = Album(name=album_name, user_id=user_id)
                    db.session.add(album)
                    db.session.flush()
                    summary["albums_created"] += 1

                count = AlbumAgent._assign_photos(album, unique_pids)
                summary["photos_assigned"] += count
                summary["details"].append(f"Person group '{album_name}': {count} photos")

            # ── Strategy 3: Group by location ────────────────────────────
            location_groups: Dict[str, List[int]] = defaultdict(list)
            for photo in ungrouped:
                loc = getattr(photo, "location", None)
                if loc:
                    location_groups[loc].append(photo.id)

            for loc, pids in location_groups.items():
                if len(pids) < 2:
                    continue
                album_name = f"Photos at {loc}"
                album = Album.query.filter(
                    Album.user_id == user_id,
                    db.func.lower(Album.name) == album_name.lower()
                ).first()
                if not album:
                    album = Album(name=album_name, user_id=user_id)
                    db.session.add(album)
                    db.session.flush()
                    summary["albums_created"] += 1

                count = AlbumAgent._assign_photos(album, pids)
                summary["photos_assigned"] += count
                summary["details"].append(f"Location group '{album_name}': {count} photos")

            db.session.commit()

        except Exception as exc:
            db.session.rollback()
            logger.error("Auto-group error: %s", exc, exc_info=True)
            summary["details"].append(f"Error during auto-grouping: {exc}")

        return summary

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_album_name(query: str) -> Optional[str]:
        """Extract an album name from the user's natural-language request.

        Tries, in order:
        1. Quoted string (``"My Album"`` or ``'My Album'``).
        2. Keyword phrase after *called / named / titled*.
        3. Groq LLM extraction as a last resort.
        """
        # 1. Quoted string
        quoted = re.findall(r"""['"]([^'"]+)['"]""", query)
        if quoted:
            return quoted[0].strip()

        # 2. Keyword extraction
        kw_match = re.search(
            r"(?:called|named|titled|name(?:d)?)\s+(.+?)(?:\s+(?:with|and|from|using)|$)",
            query,
            re.IGNORECASE,
        )
        if kw_match:
            return kw_match.group(1).strip().rstrip(".")

        # 3. LLM extraction (best-effort)
        try:
            api_key = current_app.config.get("GROQ_API_KEY", "")
            if api_key:
                client = Groq(api_key=api_key)
                resp = client.chat.completions.create(
                    model=current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Extract the album name from the user request. "
                                "Respond with ONLY the album name, nothing else. "
                                "If no album name can be determined, respond with NONE."
                            ),
                        },
                        {"role": "user", "content": query},
                    ],
                    temperature=0.0,
                    max_tokens=30,
                )
                name = resp.choices[0].message.content.strip()
                if name.upper() != "NONE":
                    return name
        except Exception as exc:
            logger.warning("LLM album-name extraction failed: %s", exc)

        return None

    @staticmethod
    def _assign_photos(album: Album, photo_ids: List[int]) -> int:
        """Add photos to an album, skipping duplicates.

        Returns the number of newly assigned photos.
        """
        existing = {
            row[0]
            for row in db.session.query(photo_album.c.photo_id)
            .filter(photo_album.c.album_id == album.id)
            .all()
        }
        count = 0
        for pid in photo_ids:
            if pid in existing:
                continue
            # Verify the photo exists and belongs to the user who owns the album
            photo = Photo.query.filter_by(id=pid, user_id=album.user_id).first()
            if photo:
                db.session.execute(
                    photo_album.insert().values(album_id=album.id, photo_id=pid)
                )
                existing.add(pid)
                count += 1
        return count

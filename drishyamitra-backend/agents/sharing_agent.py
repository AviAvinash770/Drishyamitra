"""
Sharing agent – handles photo delivery via email and WhatsApp.

Recipient detection:
* **Email** – scans the query for RFC-5322-like addresses.
* **Phone / WhatsApp** – scans for 10–15 digit phone numbers (with
  optional ``+`` prefix and separators).

The agent resolves ``photo_ids`` from the workflow state, fetches the
corresponding file paths, and calls the appropriate
``SharingService`` method.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple

from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face
from services.sharing_service import SharingService

logger = logging.getLogger(__name__)

# ── Regex patterns ───────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?[\d\-\s]{10,15}")

# Keywords that hint at the desired platform
_EMAIL_KW = {"email", "mail", "e-mail", "gmail", "outlook", "yahoo"}
_WHATSAPP_KW = {"whatsapp", "wa", "watsapp", "wapp"}


class SharingAgent:
    """Handles photo sharing via email and WhatsApp."""

    @staticmethod
    def run(state: Dict[str, Any]) -> Dict[str, Any]:
        """Share photos based on the workflow state.

        Pipeline:
        1. Retrieve ``photo_ids`` from state and load file paths.
        2. Parse recipient address and platform from the query.
        3. Optionally resolve a person name for a friendly subject line.
        4. Call ``SharingService.send_email`` or ``send_whatsapp``.
        5. Update state with the delivery result.

        Parameters
        ----------
        state : dict
            Shared workflow state containing ``user_query`` and
            (optionally) ``photo_ids``.

        Returns
        -------
        dict
            Updated state.
        """
        query: str = state.get("user_query", "")
        action_logs: list = list(state.get("action_logs", []))
        photo_ids: List[int] = list(state.get("photo_ids", []))

        try:
            # ── 1. Resolve photo paths ───────────────────────────────────
            photo_paths = SharingAgent._resolve_photo_paths(photo_ids)
            if not photo_paths:
                state["response_text"] = (
                    "There are no photos selected for sharing. "
                    "Please search for photos first, then ask me to share them."
                )
                action_logs.append("[sharing] No photo paths available to share.")
                state["action_logs"] = action_logs
                return state

            # ── 2. Detect recipient & platform ───────────────────────────
            recipient, platform = SharingAgent._parse_recipient(query)
            if not recipient:
                state["response_text"] = (
                    "I couldn't find a recipient in your message. "
                    "Please include an email address or phone number."
                )
                action_logs.append("[sharing] No recipient detected.")
                state["action_logs"] = action_logs
                return state

            # ── 3. Person name (for subject / caption) ───────────────────
            person_name = SharingAgent._extract_person_name(query)

            # ── 4. Infer user_id (default to 0 when not available) ───────
            user_id = state.get("user_id", 0)

            # ── 5. Send ──────────────────────────────────────────────────
            if platform == "whatsapp":
                result = SharingService.send_whatsapp(
                    recipient=recipient,
                    person_name=person_name,
                    photo_paths=photo_paths,
                    user_id=user_id,
                )
                method_label = "WhatsApp"
            else:
                result = SharingService.send_email(
                    recipient=recipient,
                    person_name=person_name,
                    photo_paths=photo_paths,
                    user_id=user_id,
                )
                method_label = "email"

            # ── 6. Build response ────────────────────────────────────────
            if result.get("success") or result.get("status") in ["delivered", "sent"]:
                response = (
                    f"Successfully shared {len(photo_paths)} photo(s) via "
                    f"{method_label} to **{recipient}**."
                )
            else:
                error_detail = result.get("error", "Unknown error")
                response = (
                    f"I attempted to share the photos via {method_label}, "
                    f"but encountered an issue: {error_detail}"
                )

            action_logs.append(
                f"[sharing] Sent {len(photo_paths)} photo(s) via {method_label} "
                f"to {recipient}. Result: {result}"
            )

            # Persist into state for downstream logging
            state["recipient"] = recipient
            state["platform"] = platform

        except Exception as exc:
            logger.error("SharingAgent error: %s", exc, exc_info=True)
            response = "An error occurred while trying to share the photos."
            action_logs.append(f"[sharing] Error: {exc}")

        state["response_text"] = response
        state["action_logs"] = action_logs
        return state

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_photo_paths(photo_ids: List[int]) -> List[str]:
        """Convert a list of photo IDs to file-system paths.

        Falls back to ``Photo.filename`` if ``Photo.file_path`` is not
        available.
        """
        paths: List[str] = []
        for pid in photo_ids:
            photo = Photo.query.get(pid)
            if not photo:
                continue
            path = (
                getattr(photo, "file_path", None)
                or getattr(photo, "filepath", None)
                or getattr(photo, "filename", None)
            )
            if path:
                paths.append(str(path))
        return paths

    @staticmethod
    def _parse_recipient(query: str) -> Tuple[Optional[str], str]:
        """Extract a recipient address and infer the delivery platform.

        Returns
        -------
        tuple[str | None, str]
            ``(recipient, platform)`` where *platform* is ``'email'`` or
            ``'whatsapp'``.
        """
        q_lower = query.lower()

        # Email addresses
        email_match = _EMAIL_RE.search(query)
        # Phone numbers
        phone_match = _PHONE_RE.search(query)

        # Decide platform based on keywords first
        wants_whatsapp = any(kw in q_lower for kw in _WHATSAPP_KW)
        wants_email = any(kw in q_lower for kw in _EMAIL_KW)

        if email_match and not wants_whatsapp:
            return email_match.group(), "email"

        if phone_match:
            phone = re.sub(r"[\s\-]", "", phone_match.group().strip())
            return phone, "whatsapp"

        if email_match:
            return email_match.group(), "email"

        return None, "email"

    @staticmethod
    def _extract_person_name(query: str) -> str:
        """Try to find a known person name in the query for the subject line.

        Returns the first matched person name, or ``'photos'`` as a
        generic fallback.
        """
        try:
            persons = Person.query.all()
            for person in persons:
                if person.name and person.name.lower() in query.lower():
                    return person.name
        except Exception:
            pass
        return "photos"

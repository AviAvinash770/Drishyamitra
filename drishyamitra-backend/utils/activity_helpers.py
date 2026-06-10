"""
Activity logging utility.
"""

import logging
from database.db import db
from models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(user_id, action, details=None):
    """
    Log a user action to the activity_logs table in SQLite.

    Args:
        user_id (int): The ID of the user performing the action.
        action (str): The name/type of the action (e.g. 'Photo Uploaded').
        details (str, optional): Additional text description/metadata.
    """
    try:
        # Avoid logging if user_id is missing/None
        if not user_id:
            return None

        log = ActivityLog(user_id=user_id, action=action, details=details)
        db.session.add(log)
        db.session.commit()
        logger.info("[Activity] User %s: %s (%s)", user_id, action, details or "")
        return log
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to write activity log: %s", exc)
        return None

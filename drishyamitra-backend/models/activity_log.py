"""
ActivityLog model – tracks real user actions inside the application (e.g. login, photo upload, backup).
"""

from database.db import db
from datetime import datetime, timezone


class ActivityLog(db.Model):
    """Represents a recorded action taken by a user inside the application."""

    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to user
    user = db.relationship('User', backref=db.backref('activity_logs', cascade="all, delete-orphan", lazy=True))

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the activity log."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

"""
DeliveryHistory model – tracks photo-sharing/delivery events.
"""

from database.db import db
from datetime import datetime, timezone


class DeliveryHistory(db.Model):
    """Records each photo delivery (share) made to a recipient via a platform."""

    __tablename__ = 'delivery_history'

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False)
    platform = db.Column(db.String(20), nullable=False)
    person_name = db.Column(db.String(100), nullable=False)
    photo_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Return a JSON-serialisable dictionary with a human-readable relative time."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        delta = now - self.created_at if self.created_at else None

        if delta:
            if delta.seconds < 3600:
                time_ago = f'{delta.seconds // 60} minutes ago'
            elif delta.seconds < 86400:
                time_ago = f'{delta.seconds // 3600} hours ago'
            else:
                time_ago = f'{delta.days} days ago'
        else:
            time_ago = 'Just now'

        return {
            'id': self.id,
            'recipient': self.recipient,
            'platform': self.platform,
            'person': self.person_name,
            'count': self.photo_count,
            'status': self.status,
            'time': time_ago,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

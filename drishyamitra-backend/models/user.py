"""
User model for authentication and ownership of photos.
"""

from database.db import db
from datetime import datetime, timezone


class User(db.Model):
    """Represents a registered user of the Drishyamitra application."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    photos = db.relationship('Photo', backref='owner', lazy=True)

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the user (password excluded)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'phone': self.phone,
            'address': self.address,
            'bio': self.bio,
            'profile_pic': self.profile_pic,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

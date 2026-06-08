"""
Album model and photo ↔ album many-to-many association table.
"""

from database.db import db
from datetime import datetime, timezone

# Many-to-many association table between photos and albums
photo_album = db.Table(
    'photo_album',
    db.Column('photo_id', db.Integer, db.ForeignKey('photos.id'), primary_key=True),
    db.Column('album_id', db.Integer, db.ForeignKey('albums.id'), primary_key=True)
)


class Album(db.Model):
    """A named collection (folder/album) of photos."""

    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(10), default='📁')
    color = db.Column(db.String(20), default='#1a73e8')
    bg = db.Column(db.String(20), default='#e8f0fe')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    photos = db.relationship('Photo', secondary=photo_album, back_populates='albums')

    @property
    def count(self):
        """Return the number of photos in this album."""
        return len(self.photos)

    def to_dict(self):
        """Return a JSON-serialisable dictionary for the frontend albums view."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'bg': self.bg,
            'count': self.count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

"""
Face model – stores detected face bounding boxes and Facenet512 embeddings.
"""

from database.db import db
from datetime import datetime, timezone


class Face(db.Model):
    """
    A single detected face within a photo.

    Stores the bounding box coordinates and the 512-dimensional Facenet512
    embedding vector used for recognition and clustering.
    """

    __tablename__ = 'faces'

    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=True)
    bounding_box = db.Column(db.JSON, nullable=False)
    embedding = db.Column(db.JSON, nullable=False)  # 512-dim Facenet512 vector
    confidence = db.Column(db.Float, default=1.0)
    is_manually_labeled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the face detection."""
        return {
            'id': self.id,
            'photo_id': self.photo_id,
            'person_id': self.person_id,
            'person_name': self.person.name if self.person else 'Unknown',
            'bounding_box': self.bounding_box,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

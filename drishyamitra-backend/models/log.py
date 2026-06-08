"""
AgentLog model – records AI agent activity for auditability.
"""

from database.db import db
from datetime import datetime, timezone


class AgentLog(db.Model):
    """Stores a log entry for each action performed by an AI agent."""

    __tablename__ = 'agent_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    prompt = db.Column(db.Text, nullable=False)
    agent_name = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    log_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the log entry."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'prompt': self.prompt,
            'agent_name': self.agent_name,
            'action': self.action,
            'log_text': self.log_text,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

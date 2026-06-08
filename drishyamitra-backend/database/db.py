"""
Shared SQLAlchemy instance for the Drishyamitra backend.

Import ``db`` from this module wherever you need database access:

    from database.db import db
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

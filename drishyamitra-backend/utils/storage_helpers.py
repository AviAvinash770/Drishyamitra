"""
Storage helper utilities.
"""

import os
from flask import current_app
from models.photo import Photo


def get_user_storage_usage(user_id):
    """
    Calculate the actual storage used (in bytes) on disk by a user's uploaded files.

    Args:
        user_id (int): The ID of the user.

    Returns:
        int: Total size in bytes of all uploaded files belonging to the user.
    """
    total_bytes = 0
    try:
        photos = Photo.query.filter_by(user_id=user_id).all()
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")

        for photo in photos:
            if photo.file_path:
                filename = os.path.basename(photo.file_path)
                full_path = os.path.join(upload_folder, filename)

                if os.path.exists(full_path):
                    total_bytes += os.path.getsize(full_path)
                elif os.path.exists(photo.file_path):
                    total_bytes += os.path.getsize(photo.file_path)
    except Exception:
        pass

    return total_bytes

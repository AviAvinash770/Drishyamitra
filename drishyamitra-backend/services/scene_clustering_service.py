import os
import cv2
import numpy as np
import logging
from database.db import db
from models.photo import Photo
from models.album import Album

logger = logging.getLogger(__name__)

class SceneClusteringService:
    """Service to automatically cluster photos into 'Places & Scenes' albums by background similarity."""

    @staticmethod
    def compute_color_histogram(image_path):
        """Extract a 120-dimensional normalized HSV color histogram of the image background."""
        if not image_path or not os.path.exists(image_path):
            return []
        try:
            image = cv2.imread(image_path)
            if image is None:
                return []
            # Resize image to speed up calculation
            image = cv2.resize(image, (150, 150))
            # Convert to HSV color space
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            # Compute histogram for H and S channels (12 bins for Hue, 10 bins for Saturation)
            hist = cv2.calcHist([hsv], [0, 1], None, [12, 10], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            return hist.flatten().tolist()
        except Exception as e:
            logger.error("Failed to compute color histogram for %s: %s", image_path, e)
            return []

    @staticmethod
    def calculate_similarity(hist1, hist2):
        """Calculate cosine similarity between two histograms."""
        if not hist1 or not hist2:
            return 0.0
        h1 = np.array(hist1, dtype=np.float32)
        h2 = np.array(hist2, dtype=np.float32)
        dot = np.dot(h1, h2)
        n1 = np.linalg.norm(h1)
        n2 = np.linalg.norm(h2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(dot / (n1 * n2))

    @staticmethod
    def determine_scene_name(tags, description):
        """Analyze description and tags to generate a meaningful Scene album name."""
        text = (description + " " + " ".join(tags)).lower()
        if any(k in text for k in ["beach", "ocean", "sea", "sand", "coast", "shore"]):
            return "Beach & Coast"
        if any(k in text for k in ["greenery", "forest", "tree", "garden", "park", "grass", "nature", "outdoor"]):
            return "Greenery & Nature"
        if any(k in text for k in ["wedding", "bride", "groom", "reception", "marriage", "ceremony"]):
            return "Weddings & Ceremonies"
        if any(k in text for k in ["stage", "concert", "performance", "dance", "indoor stage"]):
            return "Stages & Performances"
        if any(k in text for k in ["sunset", "sunrise", "sky", "dusk", "horizon"]):
            return "Sunsets & Sunrises"
        if any(k in text for k in ["night", "dark", "lights", "neon"]):
            return "Night Scenes"
        if any(k in text for k in ["indoor", "room", "office", "home", "studio", "kitchen", "classroom"]):
            return "Indoors & Rooms"
        
        # Fallback to the most prominent tag that is not generic
        valid_tags = [t for t in tags if t.lower() not in ["person", "people", "photo", "image", "man", "woman", "boy", "girl"]]
        if valid_tags:
            return f"{valid_tags[0].capitalize()} Scenes"
        return "Generic Scenes"

    @classmethod
    def cluster_photo_by_scene(cls, photo):
        """Cluster photo into automated scene albums based on background features."""
        if not photo.background_features:
            return

        try:
            user_id = photo.user_id
            # Fetch all other photos for this user that have background features
            other_photos = Photo.query.filter(
                Photo.user_id == user_id,
                Photo.id != photo.id,
                Photo.background_features.isnot(None)
            ).all()

            matches = []
            for op in other_photos:
                sim = cls.calculate_similarity(photo.background_features, op.background_features)
                if sim >= 0.70:
                    matches.append((op, sim))

            # Sort matches by similarity descending
            matches.sort(key=lambda x: x[1], reverse=True)

            # Check if any matching photo is already in a Scene: album
            assigned_album = None
            for op, sim in matches:
                scene_albums = [a for a in op.albums if a.name.startswith("Scene:")]
                if scene_albums:
                    assigned_album = scene_albums[0]
                    break

            if assigned_album:
                # Add to existing Scene album if not already there
                if photo not in assigned_album.photos:
                    assigned_album.photos.append(photo)
                    db.session.commit()
                    logger.info("Assigned photo %d to existing Scene album '%s'", photo.id, assigned_album.name)
            elif len(matches) >= 1:
                # If we have matches but no scene album created yet, group them and create a new album
                similar_photos = [photo] + [m[0] for m in matches]
                
                # Combine tags and descriptions to generate name
                all_tags = []
                descriptions = []
                for sp in similar_photos:
                    if sp.tags:
                        all_tags.extend(sp.tags)
                    if sp.description:
                        descriptions.append(sp.description)
                
                scene_base_name = cls.determine_scene_name(all_tags, " ".join(descriptions))
                album_name = f"Scene: {scene_base_name}"

                # Check if album already exists for this user (could be named from a different photo cluster)
                album = Album.query.filter_by(name=album_name, user_id=user_id).first()
                if not album:
                    album = Album(
                        name=album_name,
                        description=f"Automatically grouped places and scenes like {scene_base_name}.",
                        icon="🌄",
                        color="#34a853",
                        bg="#e6f4ea",
                        user_id=user_id
                    )
                    db.session.add(album)
                    db.session.flush()
                    logger.info("Created new automated Scene album: '%s'", album_name)

                # Add all similar photos to this album
                for sp in similar_photos:
                    if sp not in album.photos:
                        album.photos.append(sp)

                db.session.commit()
                logger.info("Grouped %d photos into automated Scene album '%s'", len(similar_photos), album_name)
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to cluster photo %d by scene background: %s", photo.id, e)

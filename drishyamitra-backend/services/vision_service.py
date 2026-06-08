"""
Vision service for Drishyamitra.

Handles face detection and embedding generation using DeepFace with the
RetinaFace detector backend and Facenet512 embedding model.
"""

import logging

logger = logging.getLogger(__name__)


class VisionService:
    """Handles face detection and embedding generation using DeepFace."""

    DETECTOR_BACKEND = 'retinaface'
    MODEL_NAME = 'Facenet512'

    @staticmethod
    def detect_faces(image_path):
        """
        Detect faces in an image and generate 512-dimensional embeddings.

        Uses DeepFace with the RetinaFace detector for robust face localisation
        and Facenet512 for high-quality 512-dim embedding vectors.

        Args:
            image_path (str): Absolute filesystem path to the image file.

        Returns:
            list[dict]: A list of dicts, each containing:
                - bounding_box (dict): ``{"x": int, "y": int, "w": int, "h": int}``
                - embedding (list[float]): 512-dimensional face embedding.
                - confidence (float): Detection confidence score (0-1).
              Returns an empty list when no faces are found or on any error.
        """
        try:
            from deepface import DeepFace
        except ImportError:
            logger.warning(
                "deepface is not installed – face detection unavailable. "
                "Install with: pip install deepface"
            )
            return []

        try:
            results = DeepFace.represent(
                img_path=image_path,
                model_name=VisionService.MODEL_NAME,
                detector_backend=VisionService.DETECTOR_BACKEND,
                enforce_detection=False,
            )
        except Exception as exc:
            logger.error("DeepFace.represent failed for '%s': %s", image_path, exc)
            return []

        if not results:
            return []

        faces = []
        for entry in results:
            facial_area = entry.get('facial_area', {})
            embedding = entry.get('embedding', [])
            confidence = entry.get('face_confidence', 0.0)

            # Skip entries with trivially small or missing bounding boxes
            if not facial_area or not embedding:
                continue

            bounding_box = {
                'x': int(facial_area.get('x', 0)),
                'y': int(facial_area.get('y', 0)),
                'w': int(facial_area.get('w', 0)),
                'h': int(facial_area.get('h', 0)),
            }

            # Skip detections that are clearly noise (zero-area boxes)
            if bounding_box['w'] <= 0 or bounding_box['h'] <= 0:
                continue

            faces.append({
                'bounding_box': bounding_box,
                'embedding': embedding,
                'confidence': float(confidence),
            })

        logger.info(
            "Detected %d face(s) in '%s'.",
            len(faces),
            image_path,
        )
        return faces

    @staticmethod
    def extract_face_region(image_path, bounding_box):
        """
        Extract a cropped face region from an image using OpenCV.

        Args:
            image_path (str): Absolute filesystem path to the source image.
            bounding_box (dict): Dict with keys ``x``, ``y``, ``w``, ``h``.

        Returns:
            numpy.ndarray | None: BGR numpy array of the cropped face region,
            or ``None`` if the image cannot be read or the box is invalid.
        """
        try:
            import cv2
        except ImportError:
            logger.warning(
                "opencv-python is not installed – face cropping unavailable. "
                "Install with: pip install opencv-python"
            )
            return None

        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error("Could not read image at '%s'.", image_path)
                return None

            x = max(int(bounding_box.get('x', 0)), 0)
            y = max(int(bounding_box.get('y', 0)), 0)
            w = int(bounding_box.get('w', 0))
            h = int(bounding_box.get('h', 0))

            if w <= 0 or h <= 0:
                logger.error("Invalid bounding box dimensions: %s", bounding_box)
                return None

            img_h, img_w = image.shape[:2]
            x2 = min(x + w, img_w)
            y2 = min(y + h, img_h)

            face_region = image[y:y2, x:x2]
            if face_region.size == 0:
                logger.error("Cropped face region is empty for box %s.", bounding_box)
                return None

            return face_region

        except Exception as exc:
            logger.error(
                "Failed to extract face region from '%s': %s",
                image_path,
                exc,
            )
            return None

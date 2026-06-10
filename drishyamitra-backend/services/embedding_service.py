"""
Embedding service for Drishyamitra.

Manages face-embedding comparisons using cosine similarity and provides
person-matching logic against the existing face database.
"""

import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages face embedding comparisons and matching."""

    SIMILARITY_THRESHOLD = 0.60

    @staticmethod
    def calculate_similarity(embedding_a, embedding_b):
        """
        Calculate cosine similarity between two face embeddings.

        Args:
            embedding_a (list[float]): First 512-dim embedding vector.
            embedding_b (list[float]): Second 512-dim embedding vector.

        Returns:
            float: Cosine similarity score in the range [0, 1].
                   Returns 0.0 if either embedding is empty or malformed.
        """
        try:
            import json
            
            # If the database returns the JSON column as a string, parse it first
            if isinstance(embedding_a, str):
                embedding_a = json.loads(embedding_a)
            if isinstance(embedding_b, str):
                embedding_b = json.loads(embedding_b)

            vec_a = np.array(embedding_a, dtype=np.float64).reshape(1, -1)
            vec_b = np.array(embedding_b, dtype=np.float64).reshape(1, -1)

            if vec_a.size == 0 or vec_b.size == 0:
                logger.warning("One or both embeddings are empty.")
                return 0.0

            score = cosine_similarity(vec_a, vec_b)[0][0]
            return float(max(0.0, min(score, 1.0)))

        except Exception as exc:
            logger.error("Similarity calculation failed: %s", exc)
            return 0.0

    @staticmethod
    def find_matching_person(new_embedding, existing_faces):
        """
        Compare a new face embedding against all existing known faces.

        Iterates over every ``Face`` record that already has a ``person_id``
        assigned, computes cosine similarity, and returns the ``Person``
        associated with the best match **if** it exceeds the threshold.

        Args:
            new_embedding (list[float]): 512-dim embedding of the new face.
            existing_faces (list): List of ``Face`` model objects that have
                ``person_id`` set (i.e. already identified faces).

        Returns:
            Person | None: The ``Person`` ORM object if a match is found
            above ``SIMILARITY_THRESHOLD``, otherwise ``None``.
        """
        if not new_embedding or not existing_faces:
            return None

        best_score = 0.0
        best_person = None

        for face in existing_faces:
            if face.person_id is None:
                continue

            stored_embedding = face.embedding
            if not stored_embedding:
                continue

            score = EmbeddingService.calculate_similarity(
                new_embedding, stored_embedding
            )

            if score > best_score:
                best_score = score
                best_person = face.person

        if best_score >= EmbeddingService.SIMILARITY_THRESHOLD:
            logger.info(
                "Matched face to person '%s' (id=%s) with score %.4f.",
                best_person.name if best_person else "?",
                best_person.id if best_person else "?",
                best_score,
            )
            return best_person

        logger.debug(
            "No match above threshold %.2f (best was %.4f).",
            EmbeddingService.SIMILARITY_THRESHOLD,
            best_score,
        )
        return None

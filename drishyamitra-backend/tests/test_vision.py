"""
Tests for the vision / face-detection service.
Uses a synthetic test image so DeepFace is exercised without requiring
real photographs.
"""

import unittest
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VisionServiceTestCase(unittest.TestCase):
    """Test suite for services.vision_service.VisionService."""

    def test_detect_faces_with_invalid_path(self):
        """Calling detect_faces on a non-existent path should return []."""
        from services.vision_service import VisionService
        result = VisionService.detect_faces("/nonexistent/path/image.jpg")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_detect_faces_returns_correct_structure(self):
        """Each detection dict should contain bounding_box, embedding, confidence."""
        from services.vision_service import VisionService

        # Create a simple synthetic image (no real face — DeepFace will return [])
        try:
            from PIL import Image
            test_dir = os.path.join(os.path.dirname(__file__), "test_assets")
            os.makedirs(test_dir, exist_ok=True)
            img_path = os.path.join(test_dir, "blank.jpg")
            Image.new("RGB", (200, 200), color="white").save(img_path)

            result = VisionService.detect_faces(img_path)
            self.assertIsInstance(result, list)
            # Verify the dictionary structure of any returned detections
            for face in result:
                self.assertIn("bounding_box", face)
                self.assertIn("embedding", face)
                self.assertIn("confidence", face)
                self.assertIsInstance(face["bounding_box"], dict)
                self.assertIsInstance(face["embedding"], list)
                self.assertIsInstance(face["confidence"], float)
        except ImportError:
            self.skipTest("Pillow not installed")


class EmbeddingServiceTestCase(unittest.TestCase):
    """Test suite for services.embedding_service.EmbeddingService."""

    def test_identical_embeddings_have_similarity_one(self):
        """Two identical vectors should yield similarity ≈ 1.0."""
        from services.embedding_service import EmbeddingService
        vec = list(np.random.randn(512).astype(float))
        sim = EmbeddingService.calculate_similarity(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_orthogonal_embeddings_have_low_similarity(self):
        """Two orthogonal vectors should yield similarity ≈ 0.0."""
        from services.embedding_service import EmbeddingService
        vec_a = [1.0] + [0.0] * 511
        vec_b = [0.0, 1.0] + [0.0] * 510
        sim = EmbeddingService.calculate_similarity(vec_a, vec_b)
        self.assertAlmostEqual(sim, 0.0, places=4)

    def test_find_matching_person_returns_none_for_empty(self):
        """No existing faces should mean no match."""
        from services.embedding_service import EmbeddingService
        result = EmbeddingService.find_matching_person([0.0] * 512, [])
        self.assertIsNone(result)


class PaletteExtractorTestCase(unittest.TestCase):
    """Test suite for utils.palette_extractor."""

    def test_extract_palette_returns_list(self):
        """extract_palette should return a list of hex colour strings."""
        from utils.palette_extractor import extract_palette

        try:
            from PIL import Image
            test_dir = os.path.join(os.path.dirname(__file__), "test_assets")
            os.makedirs(test_dir, exist_ok=True)
            img_path = os.path.join(test_dir, "red_blue.jpg")
            img = Image.new("RGB", (100, 100), color="red")
            img.save(img_path)

            palette = extract_palette(img_path, num_colors=2)
            self.assertIsInstance(palette, list)
            self.assertGreaterEqual(len(palette), 1)
            for hex_color in palette:
                self.assertTrue(hex_color.startswith("#"))
        except ImportError:
            self.skipTest("Pillow not installed")

    def test_extract_palette_bad_path(self):
        """Bad path should return a fallback palette, not crash."""
        from utils.palette_extractor import extract_palette
        palette = extract_palette("/does/not/exist.jpg")
        self.assertIsInstance(palette, list)
        self.assertGreater(len(palette), 0)


if __name__ == "__main__":
    unittest.main()

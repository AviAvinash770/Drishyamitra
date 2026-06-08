"""
Tests for the LangGraph Agent Workflow.
Covers supervisor routing, agent node executions, and compound search-first routing.
"""

import unittest
import os
import sys

# Ensure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.db import db
from models.photo import Photo
from models.person import Person
from models.face import Face
from models.album import Album
from workflows.agent_workflow import run_agent_workflow


class WorkflowTestCase(unittest.TestCase):
    """Test suite for workflows.agent_workflow."""

    def setUp(self):
        """Create a fresh test app and database for every test."""
        self.app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
            "GROQ_API_KEY": "",  # Force keyword fallback for deterministic testing
            "SECRET_KEY": "test-secret"
        })
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Drop all tables and pop app context after each test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ── Basic Routing Tests ────────────────────────────────────────────

    def test_workflow_general_fallback(self):
        """A general query should route to end and return the offline / fallback reply."""
        res = run_agent_workflow("Hello, how are you today?")
        self.assertIn("response", res)
        # Should invoke fallback or general conversation
        self.assertIn("Drishyamitra", res["response"])
        self.assertTrue(any("Classified intent as 'end'" in a["log"] for a in res["actions"]))

    def test_workflow_search_route(self):
        """A query matching search keywords should run the search agent."""
        res = run_agent_workflow("Find photos taken in 2024")
        self.assertTrue(any("Classified intent as 'search'" in a["log"] for a in res["actions"]))
        self.assertTrue(any("[search]" in a["log"] for a in res["actions"]))

    def test_workflow_memory_route(self):
        """A query asking 'who' or about relations should trigger the memory agent."""
        # Seed a person
        p = Person(name="Alice Smith", initials="AS", color="#ffffff", bg="#000000")
        db.session.add(p)
        db.session.commit()

        res = run_agent_workflow("Who is Alice Smith?")
        self.assertTrue(any("Classified intent as 'memory'" in a["log"] for a in res["actions"]))
        self.assertTrue(any("[memory] Resolved" in a["log"] for a in res["actions"]))
        self.assertIn("Alice Smith", res["response"])

    # ── Compound/Advanced Routing Tests ─────────────────────────────────

    def test_workflow_sharing_requires_search_first(self):
        """If a sharing command is run without selected photo_ids, it should search first."""
        # Seed a person, a photo, and a face linking them
        person = Person(name="Bob Jones", initials="BJ", color="#ffffff", bg="#000000")
        db.session.add(person)
        db.session.flush()

        photo = Photo(
            filename="bob_pic.jpg",
            file_path="/uploads/bob_pic.jpg",
            size="1.2 MB",
            height=200,
            emoji="📸"
        )
        db.session.add(photo)
        db.session.flush()

        face = Face(photo_id=photo.id, person_id=person.id, bounding_box={}, embedding=[])
        db.session.add(face)
        db.session.commit()

        # Ask to share Bob's photos via email.
        # This classifies as 'sharing'. Because photo_ids starts empty, it must route to search first.
        res = run_agent_workflow("Email photos of Bob Jones to bob@example.com")

        # Verify orchestrator intercepted and set original intent
        self.assertTrue(any("Routing to 'search' first" in a["log"] for a in res["actions"]))
        
        # Verify search agent executed
        self.assertTrue(any("[search] Found 1 photos" in a["log"] for a in res["actions"]))
        
        # Verify sharing agent executed and completed delivery
        self.assertTrue(any("[sharing] Sent 1 photo(s) via email to bob@example.com" in a["log"] for a in res["actions"]))
        self.assertIn("Successfully shared 1 photo(s)", res["response"])

    def test_workflow_album_requires_search_first(self):
        """Creating an album from a query should find photos first if none are selected."""
        # Seed a person, photo, and face
        person = Person(name="Charlie", initials="C", color="#ffffff", bg="#000000")
        db.session.add(person)
        db.session.flush()

        photo = Photo(
            filename="charlie.jpg",
            file_path="/uploads/charlie.jpg",
            size="800 KB",
            height=180,
            emoji="📸"
        )
        db.session.add(photo)
        db.session.flush()

        face = Face(photo_id=photo.id, person_id=person.id, bounding_box={}, embedding=[])
        db.session.add(face)
        db.session.commit()

        # Request to organize photos of Charlie into an album named "Charlie Trip"
        res = run_agent_workflow("Create an album called 'Charlie Trip' with photos of Charlie")

        # Verify we went search-first
        self.assertTrue(any("Routing to 'search' first" in a["log"] for a in res["actions"]))
        
        # Verify search found the photo
        self.assertTrue(any("[search] Found 1 photos" in a["log"] for a in res["actions"]))
        
        # Verify album agent ran and assigned the photo
        self.assertTrue(any("[album] Created album 'Charlie Trip'" in a["log"] for a in res["actions"]))
        self.assertIn("Created album **Charlie Trip** and added 1 photo(s) to it", res["response"])


if __name__ == "__main__":
    unittest.main()

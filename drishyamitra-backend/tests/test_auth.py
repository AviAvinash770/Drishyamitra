"""
Tests for the authentication module.
Covers registration, login, and JWT-protected profile access.
"""

import unittest
import json
import os
import sys

# Ensure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.db import db


class AuthTestCase(unittest.TestCase):
    """Test suite for /api/auth/* endpoints."""

    def setUp(self):
        """Create a fresh test app and database for every test."""
        self.app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
            "SECRET_KEY": "test-secret"
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Drop all tables after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # ── Registration ───────────────────────────────────────────────────

    def test_register_success(self):
        """A valid registration should return 201 and a JWT token."""
        res = self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": "testuser",
                "email": "test@example.com",
                "password": "StrongP@ss1"
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], "testuser")

    def test_register_missing_fields(self):
        """Missing fields should return 400."""
        res = self.client.post(
            "/api/auth/register",
            data=json.dumps({"username": "test"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_register_duplicate_email(self):
        """Registering with an existing email should fail."""
        payload = json.dumps({
            "username": "user1",
            "email": "dup@example.com",
            "password": "Pass1234"
        })
        self.client.post("/api/auth/register", data=payload, content_type="application/json")
        res = self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": "user2",
                "email": "dup@example.com",
                "password": "Pass5678"
            }),
            content_type="application/json",
        )
        self.assertIn(res.status_code, [400, 409])

    # ── Login ──────────────────────────────────────────────────────────

    def test_login_success(self):
        """Valid credentials should return a JWT token."""
        self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": "loginuser",
                "email": "login@example.com",
                "password": "Secret123"
            }),
            content_type="application/json",
        )
        res = self.client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "login@example.com",
                "password": "Secret123"
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("token", data)

    def test_login_wrong_password(self):
        """Wrong password should return 401."""
        self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": "wpuser",
                "email": "wp@example.com",
                "password": "Correct1"
            }),
            content_type="application/json",
        )
        res = self.client.post(
            "/api/auth/login",
            data=json.dumps({
                "email": "wp@example.com",
                "password": "WrongPass"
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)

    # ── Profile ────────────────────────────────────────────────────────

    def test_profile_with_token(self):
        """GET /profile with a valid token should return user data."""
        reg = self.client.post(
            "/api/auth/register",
            data=json.dumps({
                "username": "profuser",
                "email": "prof@example.com",
                "password": "MyPass99"
            }),
            content_type="application/json",
        )
        token = json.loads(reg.data)["token"]
        res = self.client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["email"], "prof@example.com")

    def test_profile_without_token(self):
        """GET /profile without a token should return 401."""
        res = self.client.get("/api/auth/profile")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()

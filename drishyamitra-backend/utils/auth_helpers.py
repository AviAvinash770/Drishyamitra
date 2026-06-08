"""
Authentication helper utilities.

Provides JWT token generation / decoding and a ``@token_required``
decorator that protects Flask routes.
"""

from functools import wraps
from datetime import datetime, timedelta, timezone

import jwt
from flask import request, jsonify, g, current_app


def generate_token(user_id: int, secret_key: str) -> str:
    """
    Create a signed JWT containing the user's ID.

    Args:
        user_id: The primary-key ID of the authenticated user.
        secret_key: The application secret used for HS256 signing.

    Returns:
        A URL-safe JWT string valid for 24 hours.
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def decode_token(token: str, secret_key: str) -> dict:
    """
    Decode and verify a JWT.

    Args:
        token: The raw JWT string.
        secret_key: The application secret used for verification.

    Returns:
        The decoded payload dictionary.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is malformed or tampered with.
    """
    return jwt.decode(token, secret_key, algorithms=['HS256'])


def token_required(f):
    """
    Flask route decorator that enforces JWT authentication.

    Expects an ``Authorization`` header in the form ``Bearer <token>``.
    On success, sets ``flask.g.current_user`` to the corresponding
    :class:`~models.user.User` instance.  Returns a ``401`` JSON
    response on any authentication failure.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        print("[DEBUG] auth_header received:", auth_header)
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]

        print("[DEBUG] token extracted:", token)
        if not token:
            print("[DEBUG] Authentication token is missing!")
            return jsonify({'error': 'Authentication token is missing'}), 401

        try:
            payload = decode_token(token, current_app.config['SECRET_KEY'])
            user_id = payload.get('user_id')

            if user_id is None:
                return jsonify({'error': 'Invalid token payload'}), 401

            # Import here to avoid circular imports at module level
            from models.user import User
            user = User.query.get(user_id)

            if user is None:
                return jsonify({'error': 'User not found'}), 401

            g.current_user = user

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated

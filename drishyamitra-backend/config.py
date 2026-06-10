"""
Configuration module for the Drishyamitra Flask backend.

Loads environment variables from a .env file using python-dotenv
and exposes them as attributes on the Config class.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
load_dotenv()


class Config:
    """
    Application configuration class.

    All settings are loaded from environment variables with sensible defaults
    for local development. In production, override via environment or .env file.
    """

    # Flask core
    SECRET_KEY = os.environ.get('SECRET_KEY', 'drishyamitra-super-secret-key-change-in-production')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///drishyamitra.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 50 MB

    # Groq LLM
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GROQ_MODEL = 'llama-3.3-70b-versatile'

    # OpenAI API (Vision AI auto-tagging)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

    # Google Client ID (OAuth 2.0)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

    # Mail Server (SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', os.environ.get('SMTP_SERVER', ''))
    MAIL_PORT = int(os.environ.get('MAIL_PORT', os.environ.get('SMTP_PORT', 587)))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', os.environ.get('SMTP_USER', ''))
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', os.environ.get('SMTP_PASSWORD', ''))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('SMTP_USER', 'no-reply@drishyamitra.com'))

    # ChromaDB vector store
    CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR', './chroma_data')

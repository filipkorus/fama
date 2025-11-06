import os

class Config:
    """Flask application configuration"""

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/cryptography_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secret key for sessions
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Flask-SocketIO configuration
    SOCKETIO_MESSAGE_QUEUE = os.getenv('SOCKETIO_MESSAGE_QUEUE', None)

    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # Application settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    TESTING = os.getenv('FLASK_TESTING', 'False') == 'True'

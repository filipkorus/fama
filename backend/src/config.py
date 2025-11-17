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

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days
    JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', 'False') == 'True'  # Set to True in production with HTTPS

    # Password validation
    VALIDATE_PASSWORD_STRENGTH = os.getenv('VALIDATE_PASSWORD_STRENGTH', 'False') == 'True'

    # Flask-SocketIO configuration
    SOCKETIO_MESSAGE_QUEUE = os.getenv('SOCKETIO_MESSAGE_QUEUE', None)

    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # Server configuration
    BACKEND_PORT = int(os.getenv('BACKEND_PORT', 5000))

    # Application settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    TESTING = os.getenv('FLASK_TESTING', 'False') == 'True'

    # Logger configuration
    LOGGER_LEVEL = os.getenv('LOGGER_LEVEL', 'DEBUG')
    LOGGER_FORMAT = '%(asctime)s - %(levelname)s - %(filename)s - %(message)s'

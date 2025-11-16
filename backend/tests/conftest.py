import pytest
import sys
import os

# CRITICAL: Set test database BEFORE any imports
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import timedelta
from app import app as flask_app, socketio
from database import db as _db

class TestConfig:
    """Test configuration"""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SECURE = False
    VALIDATE_PASSWORD_STRENGTH = False

# Apply test configuration
flask_app.config.from_object(TestConfig)

@pytest.fixture(scope='function')
def app():
    """Create and configure a test app instance"""
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client"""
    with app.test_client() as client:
        yield client

@pytest.fixture
def socketio_client(app):
    """Create a Socket.IO test client"""
    client = socketio.test_client(app)
    yield client

@pytest.fixture
def sample_public_key():
    """Generate a valid ML-KEM public key for testing"""
    import base64
    try:
        from crypto.ml_kem import MLKEMCrypto
        crypto = MLKEMCrypto('Kyber768')
        pub_key, _ = crypto.generate_keypair()
        return base64.b64encode(pub_key).decode('utf-8')
    except Exception:
        pass

    # Fallback: generate fake key with correct size (1184 bytes for Kyber768)
    kyber768_key_size = 1184
    fake_key = b'0' * kyber768_key_size
    return base64.b64encode(fake_key).decode('utf-8')


@pytest.fixture
def sample_user_with_device(app, sample_public_key):
    """Create a sample user"""
    from models import User

    with app.app_context():
        user = User(username='testuser', public_key=sample_public_key)
        user.set_password('TestPass123')
        _db.session.add(user)
        _db.session.commit()

        yield user


@pytest.fixture
def sample_access_token(app, sample_user_with_device):
    """Generate access token for sample user"""
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(identity=str(sample_user_with_device.id))
        yield token

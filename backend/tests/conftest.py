from unittest.mock import patch
from datetime import timedelta
import pytest
import os



os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from src.app import app as flask_app, socketio
from src.database import db as _db
from src.socketio_handlers.messages import register_message_handlers
from src.socketio_handlers.connection import register_connection_handlers

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


@pytest.fixture(scope='module')
def test_client():
    register_connection_handlers(socketio)
    register_message_handlers(socketio)

    with patch('src.socketio_handlers.connection.verify_socket_token') as mock_verify, \
         patch('src.models.User.get_username_by_userid') as mock_get_username:

        mock_verify.return_value = ({'user_id': 1, 'username': 'fixture_user'}, None)
        mock_get_username.return_value = 'fixture_user'

        with flask_app.app_context():
            client = socketio.test_client(flask_app, flask_test_client=flask_app.test_client(), auth={'token': 'Bearer mock'})

            yield client

            if client.is_connected():
                client.disconnect()

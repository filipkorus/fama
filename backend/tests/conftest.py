import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, socketio
from config import Config

class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret-key'

@pytest.fixture
def client():
    """Create a test client"""
    app.config.from_object(TestConfig)
    
    with app.test_client() as client:
        yield client

@pytest.fixture
def socketio_client():
    """Create a Socket.IO test client"""
    app.config.from_object(TestConfig)
    
    client = socketio.test_client(app)
    yield client
    client.disconnect()

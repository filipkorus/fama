"""
Tests for WebSocket connection handlers
Tests connect/disconnect events and authentication
"""

import pytest
from app import app, socketio
from models import User, Room, SymmetricKey
from database import db
import base64


@pytest.fixture
def authenticated_socketio_client(client, sample_public_key):
    """Create a Socket.IO client with valid authentication"""
    # Register and login to get access token
    register_response = client.post('/api/auth/register', json={
        'username': 'socketuser',
        'password': 'TestPass123',
        'public_key': sample_public_key
    })

    access_token = register_response.get_json()['access_token']

    # Connect to Socket.IO with authentication using test_client
    socketio_client = socketio.test_client(
        app,
        flask_test_client=client,
        auth={'token': f'Bearer {access_token}'}
    )

    yield socketio_client

    # Cleanup
    if socketio_client.is_connected():
        socketio_client.disconnect()


class TestWebSocketConnection:
    """Test WebSocket connection and authentication"""

    def test_connect_with_valid_token(self, authenticated_socketio_client):
        """Test Socket.IO connection with valid JWT token"""
        assert authenticated_socketio_client.is_connected()

    def test_connect_without_token(self, app, client):
        """Test Socket.IO connection without token - should be rejected"""
        socketio_client = socketio.test_client(app, flask_test_client=client)
        assert not socketio_client.is_connected()

    def test_connect_with_invalid_token(self, app, client):
        """Test Socket.IO connection with invalid token - should be rejected"""
        socketio_client = socketio.test_client(
            app,
            flask_test_client=client,
            auth={'token': 'Bearer invalid_token_here'}
        )
        assert not socketio_client.is_connected()

    def test_connect_without_bearer_prefix(self, client, sample_public_key):
        """Test connection with token without 'Bearer ' prefix"""
        register_response = client.post('/api/auth/register', json={
            'username': 'testuser2',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        access_token = register_response.get_json()['access_token']

        # Connect without 'Bearer ' prefix
        socketio_client = socketio.test_client(
            app,
            flask_test_client=client,
            auth={'token': access_token}
        )

        assert socketio_client.is_connected()
        socketio_client.disconnect()

    def test_connect_loads_user_rooms(self, client, sample_public_key, app):
        """Test that connection loads all user's rooms with participants and keys"""
        # Register user
        register_response = client.post('/api/auth/register', json={
            'username': 'roomuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        access_token = register_response.get_json()['access_token']

        # Create a room in database
        with app.app_context():
            user = User.query.filter_by(username='roomuser').first()
            room = Room(name='Test Room', is_group=False)
            room.participants.append(user)
            db.session.add(room)
            db.session.commit()

            # Add symmetric key after room is committed and has an ID
            sym_key = SymmetricKey(
                room_id=room.id,
                user_id=user.id,
                key_version=1,
                encrypted_key=base64.b64encode(b'test_key').decode('utf-8')
            )
            db.session.add(sym_key)
            db.session.commit()

        # Connect
        socketio_client = socketio.test_client(
            app,
            flask_test_client=client,
            auth={'token': f'Bearer {access_token}'}
        )

        # Verify connection was successful and data exists in database
        assert socketio_client.is_connected()

        # Verify the room and key were created correctly
        with app.app_context():
            user = User.query.filter_by(username='roomuser').first()
            rooms = Room.query.filter(Room.participants.contains(user)).all()
            assert len(rooms) == 1
            assert rooms[0].name == 'Test Room'
            assert len(rooms[0].participants) == 1
            assert rooms[0].participants[0].username == 'roomuser'

            # Verify symmetric key exists
            sym_key = SymmetricKey.query.filter_by(
                room_id=rooms[0].id,
                user_id=user.id,
                key_version=1
            ).first()
            assert sym_key is not None
            assert sym_key.encrypted_key == base64.b64encode(b'test_key').decode('utf-8')

        socketio_client.disconnect()

    def test_disconnect(self, authenticated_socketio_client):
        """Test Socket.IO disconnection"""
        assert authenticated_socketio_client.is_connected()

        authenticated_socketio_client.disconnect()

        assert not authenticated_socketio_client.is_connected()

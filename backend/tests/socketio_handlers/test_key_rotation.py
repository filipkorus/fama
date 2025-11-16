"""
Tests for symmetric key rotation
Tests rotate_room_key event and key version management
"""

import pytest
from app import app, socketio
from models import Room, SymmetricKey, User
from database import db
import base64


@pytest.fixture
def authenticated_socketio_client(client, sample_public_key):
    """Create a Socket.IO client with valid authentication"""
    register_response = client.post('/api/auth/register', json={
        'username': 'keyuser',
        'password': 'TestPass123',
        'public_key': sample_public_key
    })
    access_token = register_response.get_json()['access_token']

    socketio_client = socketio.test_client(
        app,
        flask_test_client=client,
        auth={'token': f'Bearer {access_token}'}
    )

    yield socketio_client

    if socketio_client.is_connected():
        socketio_client.disconnect()


@pytest.fixture
def second_authenticated_client(client, sample_public_key):
    """Create a second authenticated Socket.IO client"""
    register_response = client.post('/api/auth/register', json={
        'username': 'keyuser2',
        'password': 'TestPass456',
        'public_key': sample_public_key
    })
    access_token = register_response.get_json()['access_token']

    socketio_client = socketio.test_client(
        app,
        flask_test_client=client,
        auth={'token': f'Bearer {access_token}'}
    )

    yield socketio_client

    if socketio_client.is_connected():
        socketio_client.disconnect()


@pytest.fixture
def room_with_keys(app, authenticated_socketio_client, second_authenticated_client):
    """Create a room with two participants and initial keys"""
    with app.app_context():
        user1 = User.query.filter_by(username='keyuser').first()
        user2 = User.query.filter_by(username='keyuser2').first()

    authenticated_socketio_client.get_received()

    key1_v1 = base64.b64encode(b'user1_key_version_1').decode('utf-8')
    key2_v1 = base64.b64encode(b'user2_key_version_1').decode('utf-8')

    authenticated_socketio_client.emit('create_room', {
        'name': 'Key Rotation Room',
        'participant_ids': [user2.id],
        'encrypted_keys': [
            {'user_id': user1.id, 'encrypted_key': key1_v1},
            {'user_id': user2.id, 'encrypted_key': key2_v1}
        ]
    })

    with app.app_context():
        room = Room.query.filter_by(name='Key Rotation Room').first()
        room_id = room.id

    yield room_id, user1.id, user2.id


class TestKeyRotation:
    """Test symmetric key rotation functionality"""

    def test_rotate_room_key(self, authenticated_socketio_client, room_with_keys, app):
        """Test rotating a room's symmetric key"""
        room_id, user1_id, user2_id = room_with_keys

        authenticated_socketio_client.get_received()

        key1_v2 = base64.b64encode(b'user1_key_version_2').decode('utf-8')
        key2_v2 = base64.b64encode(b'user2_key_version_2').decode('utf-8')

        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': key1_v2},
                {'user_id': user2_id, 'encrypted_key': key2_v2}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert room.current_key_version == 2

            # Check new keys exist
            key1_new = SymmetricKey.query.filter_by(
                room_id=room_id, user_id=user1_id, key_version=2
            ).first()
            key2_new = SymmetricKey.query.filter_by(
                room_id=room_id, user_id=user2_id, key_version=2
            ).first()

            assert key1_new is not None
            assert key1_new.encrypted_key == key1_v2
            assert key2_new is not None
            assert key2_new.encrypted_key == key2_v2

    def test_rotate_key_increments_version(self, authenticated_socketio_client, room_with_keys, app):
        """Test that key rotation increments the version number"""
        room_id, user1_id, user2_id = room_with_keys

        with app.app_context():
            room = db.session.get(Room, room_id)
            initial_version = room.current_key_version

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'key_v2_u1'},
                {'user_id': user2_id, 'encrypted_key': 'key_v2_u2'}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert room.current_key_version == initial_version + 1

    def test_rotate_key_revokes_old_keys(self, authenticated_socketio_client, room_with_keys, app):
        """Test that old keys are revoked after rotation"""
        room_id, user1_id, user2_id = room_with_keys

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'rotated_u1'},
                {'user_id': user2_id, 'encrypted_key': 'rotated_u2'}
            ]
        })

        with app.app_context():
            old_keys = SymmetricKey.query.filter_by(
                room_id=room_id, key_version=1
            ).all()

            for key in old_keys:
                assert key.revoked_at is not None

    def test_multiple_rotations(self, authenticated_socketio_client, room_with_keys, app):
        """Test performing multiple consecutive key rotations"""
        room_id, user1_id, user2_id = room_with_keys

        authenticated_socketio_client.get_received()

        # First rotation
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'v2_u1'},
                {'user_id': user2_id, 'encrypted_key': 'v2_u2'}
            ]
        })

        # Second rotation
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'v3_u1'},
                {'user_id': user2_id, 'encrypted_key': 'v3_u2'}
            ]
        })

        # Third rotation
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'v4_u1'},
                {'user_id': user2_id, 'encrypted_key': 'v4_u2'}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert room.current_key_version == 4

            # Verify all old keys are revoked
            old_keys = SymmetricKey.query.filter(
                SymmetricKey.room_id == room_id,
                SymmetricKey.key_version < 4
            ).all()

            for key in old_keys:
                assert key.revoked_at is not None
class TestKeyVersioning:
    """Test key version management and history"""

    def test_old_keys_preserved_in_database(self, authenticated_socketio_client, room_with_keys, app):
        """Test that old key versions are preserved in database"""
        room_id, user1_id, user2_id = room_with_keys

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'preserved_v2_u1'},
                {'user_id': user2_id, 'encrypted_key': 'preserved_v2_u2'}
            ]
        })

        with app.app_context():
            # Version 1 keys should still exist
            v1_keys = SymmetricKey.query.filter_by(
                room_id=room_id, key_version=1
            ).all()
            assert len(v1_keys) == 2

            # Version 2 keys should exist
            v2_keys = SymmetricKey.query.filter_by(
                room_id=room_id, key_version=2
            ).all()
            assert len(v2_keys) == 2

    def test_current_key_version_updated(self, authenticated_socketio_client, room_with_keys, app):
        """Test that room's current_key_version field is updated correctly"""
        room_id, user1_id, user2_id = room_with_keys

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert room.current_key_version == 1

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'new_v2_u1'},
                {'user_id': user2_id, 'encrypted_key': 'new_v2_u2'}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert room.current_key_version == 2

    def test_key_version_in_messages(self, authenticated_socketio_client, room_with_keys, app):
        """Test that messages reference the correct key version"""
        room_id, user1_id, user2_id = room_with_keys

        # Join room
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('join_room', {'room_id': room_id})

        # Send message with version 1
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('send_message', {
            'room_id': room_id,
            'encrypted_content': 'v1_message',
            'iv': 'iv',
            'tag': 'tag',
            'key_version': 1
        })

        # Rotate key
        authenticated_socketio_client.emit('rotate_room_key', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user1_id, 'encrypted_key': 'msg_test_v2_u1'},
                {'user_id': user2_id, 'encrypted_key': 'msg_test_v2_u2'}
            ]
        })

        # Send message with version 2
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('send_message', {
            'room_id': room_id,
            'encrypted_content': 'v2_message',
            'iv': 'iv',
            'tag': 'tag',
            'key_version': 2
        })

        with app.app_context():
            from models import Message
            messages = Message.query.filter_by(room_id=room_id).order_by(Message.created_at).all()

            # Verify messages were sent (content field is encrypted_content in DB)
            assert len(messages) >= 2
            assert messages[0].key_version == 1
            assert messages[1].key_version == 2

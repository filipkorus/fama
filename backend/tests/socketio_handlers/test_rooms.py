"""
Tests for room creation and management
Tests creating rooms, inviting users, joining, leaving
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
        'username': 'socketuser',
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
        'username': 'seconduser',
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


class TestRoomCreation:
    """Test room creation functionality"""

    def test_create_room_basic(self, authenticated_socketio_client, app):
        """Test creating a basic chat room"""
        with app.app_context():
            user = User.query.filter_by(username='socketuser').first()
            user_id = user.id

        authenticated_socketio_client.get_received()
        fake_encrypted_key = base64.b64encode(b'encrypted_aes_key').decode('utf-8')

        authenticated_socketio_client.emit('create_room', {
            'name': 'Test Room',
            'participant_ids': [],
            'is_group': False,
            'encrypted_keys': [
                {'user_id': user_id, 'encrypted_key': fake_encrypted_key}
            ]
        })

        # Verify in database
        with app.app_context():
            room = Room.query.filter_by(name='Test Room').first()
            assert room is not None
            assert len(room.participants) == 1
            assert room.is_group is False
            assert room.current_key_version == 1

            sym_key = SymmetricKey.query.filter_by(
                room_id=room.id,
                user_id=user_id
            ).first()
            assert sym_key is not None
            assert sym_key.encrypted_key == fake_encrypted_key
            assert sym_key.key_version == 1

    def test_create_room_with_multiple_participants(self, authenticated_socketio_client, second_authenticated_client, app):
        """Test creating a group room with multiple participants"""
        with app.app_context():
            user1 = User.query.filter_by(username='socketuser').first()
            user2 = User.query.filter_by(username='seconduser').first()

        authenticated_socketio_client.get_received()
        second_authenticated_client.get_received()

        fake_key_1 = base64.b64encode(b'encrypted_key_user1').decode('utf-8')
        fake_key_2 = base64.b64encode(b'encrypted_key_user2').decode('utf-8')

        authenticated_socketio_client.emit('create_room', {
            'name': 'Group Chat',
            'participant_ids': [user2.id],
            'is_group': True,
            'encrypted_keys': [
                {'user_id': user1.id, 'encrypted_key': fake_key_1},
                {'user_id': user2.id, 'encrypted_key': fake_key_2}
            ]
        })

        with app.app_context():
            room = Room.query.filter_by(name='Group Chat').first()
            assert room is not None
            assert len(room.participants) == 2
            assert room.is_group is True

            key1 = SymmetricKey.query.filter_by(room_id=room.id, user_id=user1.id).first()
            key2 = SymmetricKey.query.filter_by(room_id=room.id, user_id=user2.id).first()
            assert key1 is not None and key1.encrypted_key == fake_key_1
            assert key2 is not None and key2.encrypted_key == fake_key_2

    def test_create_room_without_encrypted_keys(self, authenticated_socketio_client, app):
        """Test creating a room without providing encrypted keys"""
        authenticated_socketio_client.get_received()

        authenticated_socketio_client.emit('create_room', {
            'name': 'No Keys Room',
            'encrypted_keys': []
        })

        with app.app_context():
            room = Room.query.filter_by(name='No Keys Room').first()
            assert room is not None
            # Room should still be created, just without keys
            keys = SymmetricKey.query.filter_by(room_id=room.id).all()
            assert len(keys) == 0


class TestRoomInvitation:
    """Test inviting users to rooms with key rotation"""

    def test_invite_user_to_room(self, authenticated_socketio_client, second_authenticated_client, app):
        """Test inviting a user to an existing room"""
        with app.app_context():
            user1 = User.query.filter_by(username='socketuser').first()
            user2 = User.query.filter_by(username='seconduser').first()

        # Create room with user1
        authenticated_socketio_client.get_received()
        fake_key_1_v1 = base64.b64encode(b'user1_key_v1').decode('utf-8')
        authenticated_socketio_client.emit('create_room', {
            'name': 'Invite Test',
            'encrypted_keys': [{'user_id': user1.id, 'encrypted_key': fake_key_1_v1}]
        })

        with app.app_context():
            room = Room.query.filter_by(name='Invite Test').first()
            room_id = room.id

        # Invite user2 with key rotation
        authenticated_socketio_client.get_received()
        fake_key_1_v2 = base64.b64encode(b'user1_key_v2').decode('utf-8')
        fake_key_2_v2 = base64.b64encode(b'user2_key_v2').decode('utf-8')

        authenticated_socketio_client.emit('invite_to_room', {
            'room_id': room_id,
            'invited_user_ids': [user2.id],
            'new_encrypted_keys': [
                {'user_id': user1.id, 'encrypted_key': fake_key_1_v2},
                {'user_id': user2.id, 'encrypted_key': fake_key_2_v2}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert len(room.participants) == 2
            assert room.current_key_version == 2

    def test_invite_rotates_keys(self, authenticated_socketio_client, second_authenticated_client, app):
        """Test that inviting a user rotates symmetric keys"""
        with app.app_context():
            user1 = User.query.filter_by(username='socketuser').first()
            user2 = User.query.filter_by(username='seconduser').first()

        # Create room
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('create_room', {
            'name': 'Rotation Test',
            'encrypted_keys': [{'user_id': user1.id, 'encrypted_key': 'key_v1'}]
        })

        with app.app_context():
            room = Room.query.filter_by(name='Rotation Test').first()
            assert room.current_key_version == 1

        # Invite user2
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('invite_to_room', {
            'room_id': room.id,
            'invited_user_ids': [user2.id],
            'new_encrypted_keys': [
                {'user_id': user1.id, 'encrypted_key': 'key_v2_u1'},
                {'user_id': user2.id, 'encrypted_key': 'key_v2_u2'}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room.id)
            assert room.current_key_version == 2

            # Old key should be revoked
            old_key = SymmetricKey.query.filter_by(
                room_id=room.id, user_id=user1.id, key_version=1
            ).first()
            assert old_key.revoked_at is not None

    def test_invite_unauthorized(self, authenticated_socketio_client, second_authenticated_client, app):
        """Test that non-participants cannot invite users"""
        with app.app_context():
            user1 = User.query.filter_by(username='socketuser').first()

        # Create room with user1 only
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('create_room', {
            'name': 'Private Room',
            'encrypted_keys': [{'user_id': user1.id, 'encrypted_key': 'key'}]
        })

        with app.app_context():
            room = Room.query.filter_by(name='Private Room').first()
            initial_count = len(room.participants)

        # User2 (non-participant) tries to invite
        second_authenticated_client.get_received()
        second_authenticated_client.emit('invite_to_room', {
            'room_id': room.id,
            'invited_user_ids': [999],
            'new_encrypted_keys': []
        })

        with app.app_context():
            room = db.session.get(Room, room.id)
            assert len(room.participants) == initial_count


class TestRoomJoinLeave:
    """Test joining and leaving rooms"""

    def test_join_room(self, authenticated_socketio_client, app):
        """Test joining an existing room"""
        with app.app_context():
            user = User.query.filter_by(username='socketuser').first()
            room = Room(name='Join Test')
            room.participants.append(user)
            db.session.add(room)
            db.session.commit()
            room_id = room.id

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('join_room', {'room_id': room_id})

        # Verify user is still in the room (join_room is idempotent)
        with app.app_context():
            room = db.session.get(Room, room_id)
            user = User.query.filter_by(username='socketuser').first()
            assert user in room.participants

    def test_join_room_not_participant(self, authenticated_socketio_client, second_authenticated_client, app):
        """Test that non-participants cannot join a room"""
        with app.app_context():
            user1 = User.query.filter_by(username='socketuser').first()
            room = Room(name='Exclusive Room')
            room.participants.append(user1)
            db.session.add(room)
            db.session.commit()
            room_id = room.id

        # User2 tries to join
        second_authenticated_client.get_received()
        second_authenticated_client.emit('join_room', {'room_id': room_id})

        # Verify user2 is NOT in the room
        with app.app_context():
            room = db.session.get(Room, room_id)
            user2 = User.query.filter_by(username='seconduser').first()
            assert user2 not in room.participants
            assert len(room.participants) == 1  # Only user1

    def test_leave_room_with_remaining_participants(self, authenticated_socketio_client, second_authenticated_client, app):
        """Test leaving a room when other participants remain"""
        with app.app_context():
            user1 = User.query.filter_by(username='socketuser').first()
            user2 = User.query.filter_by(username='seconduser').first()

        # Create room with both users
        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('create_room', {
            'name': 'Multi Leave Test',
            'participant_ids': [user2.id],
            'encrypted_keys': [
                {'user_id': user1.id, 'encrypted_key': 'key1'},
                {'user_id': user2.id, 'encrypted_key': 'key2'}
            ]
        })

        with app.app_context():
            room = Room.query.filter_by(name='Multi Leave Test').first()
            room_id = room.id

        # User1 leaves
        authenticated_socketio_client.emit('leave_room', {
            'room_id': room_id,
            'new_encrypted_keys': [
                {'user_id': user2.id, 'encrypted_key': 'key2_v2'}
            ]
        })

        with app.app_context():
            room = db.session.get(Room, room_id)
            assert room is not None
            assert len(room.participants) == 1
            assert user2.id in [p.id for p in room.participants]
            assert room.rotation_pending is True

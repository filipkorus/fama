import pytest
from app import app, socketio, connected_users
from models import Room, Message, SymmetricKey, User
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


@pytest.fixture
def second_authenticated_client(client, sample_public_key):
    """Create a second authenticated Socket.IO client"""
    # Register second user
    register_response = client.post('/api/auth/register', json={
        'username': 'seconduser',
        'password': 'TestPass456',
        'public_key': sample_public_key
    })

    access_token = register_response.get_json()['access_token']

    # Connect to Socket.IO using test_client
    socketio_client = socketio.test_client(
        app,
        flask_test_client=client,
        auth={'token': f'Bearer {access_token}'}
    )

    yield socketio_client

    # Cleanup
    if socketio_client.is_connected():
        socketio_client.disconnect()


def test_socketio_connect_with_valid_token(authenticated_socketio_client):
    """Test Socket.IO connection with valid JWT token"""
    # Connection successful means authentication passed
    assert authenticated_socketio_client.is_connected()


def test_socketio_connect_without_token(app, client):
    """Test Socket.IO connection without token - should be rejected"""
    # Try to connect without auth
    socketio_client = socketio.test_client(app, flask_test_client=client)

    # Connection should be rejected
    assert not socketio_client.is_connected()


def test_socketio_connect_with_invalid_token(app, client):
    """Test Socket.IO connection with invalid token - should be rejected"""
    # Try to connect with invalid token
    socketio_client = socketio.test_client(
        app,
        flask_test_client=client,
        auth={'token': 'Bearer invalid_token_here'}
    )

    # Connection should be rejected
    assert not socketio_client.is_connected()


# ===== ROOM MANAGEMENT TESTS =====

def test_create_room(authenticated_socketio_client, app):
    """Test creating a new chat room with E2E encryption"""
    # Get creator's device info
    with app.app_context():
        user = User.query.filter_by(username='socketuser').first()
        device = user.devices[0]
        user_id = user.id
        device_id = device.id

    # Clear buffer
    authenticated_socketio_client.get_received()

    # Fake encrypted symmetric key (in real scenario, this would be AES key encrypted with ML-KEM)
    fake_encrypted_key = base64.b64encode(b'encrypted_aes_symmetric_key').decode('utf-8')

    # Create room with encrypted key
    authenticated_socketio_client.emit('create_room', {
        'name': 'Test Room',
        'participant_ids': [],
        'is_group': False,
        'encrypted_keys': [
            {'user_id': user_id, 'device_id': device_id, 'encrypted_key': fake_encrypted_key}
        ]
    })

    # Verify room and encrypted key in database
    with app.app_context():
        room = Room.query.filter_by(name='Test Room').first()
        assert room is not None
        assert len(room.participants) == 1
        assert room.is_group is False

        # Check symmetric key was stored
        sym_key = SymmetricKey.query.filter_by(
            room_id=room.id,
            user_id=user_id,
            device_id=device_id
        ).first()
        assert sym_key is not None
        assert sym_key.encrypted_key == fake_encrypted_key


def test_create_room_with_participants(authenticated_socketio_client, second_authenticated_client, app):
    """Test creating a room with multiple participants and encrypted keys"""
    # Get users' device info
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]

    # Clear buffers
    authenticated_socketio_client.get_received()
    second_authenticated_client.get_received()

    # Fake encrypted keys for both users
    fake_key_1 = base64.b64encode(b'encrypted_key_for_user1_device').decode('utf-8')
    fake_key_2 = base64.b64encode(b'encrypted_key_for_user2_device').decode('utf-8')

    # Create room with second user and encrypted keys
    authenticated_socketio_client.emit('create_room', {
        'name': 'Group Chat',
        'participant_ids': [user2.id],
        'is_group': True,
        'encrypted_keys': [
            {'user_id': user1.id, 'device_id': device1.id, 'encrypted_key': fake_key_1},
            {'user_id': user2.id, 'device_id': device2.id, 'encrypted_key': fake_key_2}
        ]
    })

    # Verify room and encrypted keys in database
    with app.app_context():
        room = Room.query.filter_by(name='Group Chat').first()
        assert room is not None
        assert len(room.participants) == 2
        assert room.is_group is True

        # Check both users have encrypted keys
        key1 = SymmetricKey.query.filter_by(
            room_id=room.id,
            user_id=user1.id,
            device_id=device1.id
        ).first()
        key2 = SymmetricKey.query.filter_by(
            room_id=room.id,
            user_id=user2.id,
            device_id=device2.id
        ).first()
        assert key1 is not None
        assert key1.encrypted_key == fake_key_1
        assert key2 is not None
        assert key2.encrypted_key == fake_key_2


def test_invite_to_room(authenticated_socketio_client, second_authenticated_client, app):
    """Test inviting users to an existing room with key rotation"""
    # Get user IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]
        user1_id = user1.id
        user2_id = user2.id
        device1_id = device1.id
        device2_id = device2.id

    # Create room with first user (key version 1)
    authenticated_socketio_client.get_received()
    fake_key_1_v1 = base64.b64encode(b'encrypted_key_user1_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Invite Test Room',
        'participant_ids': [],
        'encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1_v1}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Invite Test Room').first()
        room_id = room.id
        assert room.current_key_version == 1

    # First user invites second user with NEW keys for BOTH users (key rotation)
    authenticated_socketio_client.get_received()
    fake_key_1_v2 = base64.b64encode(b'encrypted_key_user1_v2').decode('utf-8')
    fake_key_2_v2 = base64.b64encode(b'encrypted_key_user2_v2').decode('utf-8')

    authenticated_socketio_client.emit('invite_to_room', {
        'room_id': room_id,
        'invited_user_ids': [user2_id],
        'new_encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1_v2},
            {'user_id': user2_id, 'device_id': device2_id, 'encrypted_key': fake_key_2_v2}
        ]
    })

    # Verify in database
    with app.app_context():
        room = db.session.get(Room, room_id)
        assert len(room.participants) == 2
        assert room.current_key_version == 2  # Key rotated

        # Verify old key (v1) was revoked
        old_key = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1_id,
            device_id=device1_id,
            key_version=1
        ).first()
        assert old_key is not None
        assert old_key.revoked_at is not None

        # Verify new keys (v2) exist for both users
        key1_v2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1_id,
            device_id=device1_id,
            key_version=2
        ).first()
        key2_v2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user2_id,
            device_id=device2_id,
            key_version=2
        ).first()
        assert key1_v2 is not None
        assert key1_v2.encrypted_key == fake_key_1_v2
        assert key1_v2.revoked_at is None
        assert key2_v2 is not None
        assert key2_v2.encrypted_key == fake_key_2_v2
        assert key2_v2.revoked_at is None

        # Verify system message was created for user joining
        system_messages = Message.query.filter_by(
            room_id=room_id,
            message_type='system'
        ).all()
        assert len(system_messages) == 1  # Only user joined message

        # Check user joined message
        user_joined_msg = system_messages[0]
        assert 'joined' in base64.b64decode(user_joined_msg.encrypted_content).decode('utf-8')
        assert user_joined_msg.sender_id is None
        assert user_joined_msg.key_version == 2


def test_invite_to_room_unauthorized(authenticated_socketio_client, second_authenticated_client, app):
    """Test that non-participants cannot invite others to a room"""
    # Get user IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]
        user1_id = user1.id
        user2_id = user2.id
        device1_id = device1.id
        device2_id = device2.id

    # Create room with first user only
    authenticated_socketio_client.get_received()
    fake_key_1 = base64.b64encode(b'encrypted_key_user1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Private Room',
        'participant_ids': [],
        'encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Private Room').first()
        room_id = room.id
        initial_participant_count = len(room.participants)
        assert initial_participant_count == 1  # Only user1 is participant

    # Create a fake third user ID to try to invite
    fake_user_id = 9999
    fake_key_2 = base64.b64encode(b'encrypted_key_fake').decode('utf-8')

    # Second user (non-participant) tries to invite someone
    second_authenticated_client.get_received()
    second_authenticated_client.emit('invite_to_room', {
        'room_id': room_id,
        'invited_user_ids': [fake_user_id],
        'new_encrypted_keys': [
            {'user_id': fake_user_id, 'device_id': 1, 'encrypted_key': fake_key_2}
        ]
    })

    # Wait a moment for the operation to complete
    second_authenticated_client.get_received()

    # Verify room participants unchanged - the invite should be rejected
    with app.app_context():
        room = db.session.get(Room, room_id)
        assert len(room.participants) == initial_participant_count

        # Verify no symmetric key was created for the fake user
        fake_key = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=fake_user_id
        ).first()
        assert fake_key is None


def test_leave_room(authenticated_socketio_client, app):
    """Test leaving a room without key rotation"""
    # Get user info
    with app.app_context():
        user = User.query.filter_by(username='socketuser').first()
        device = user.devices[0]
        user_id = user.id
        device_id = device.id

    # Create room
    authenticated_socketio_client.get_received()
    fake_key = base64.b64encode(b'encrypted_key_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Leave Test',
        'encrypted_keys': [
            {'user_id': user_id, 'device_id': device_id, 'encrypted_key': fake_key}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Leave Test').first()
        room_id = room.id

    # Leave room without key rotation
    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('leave_room', {'room_id': room_id})

    # Verify in database
    with app.app_context():
        room = db.session.get(Room, room_id)
        assert len(room.participants) == 0
        assert room.current_key_version == 1  # No rotation

        # Verify system message was created
        system_messages = Message.query.filter_by(
            room_id=room_id,
            message_type='system'
        ).all()
        assert len(system_messages) == 1
        assert 'left the room' in base64.b64decode(system_messages[0].encrypted_content).decode('utf-8')
        assert system_messages[0].sender_id is None
        assert system_messages[0].key_version == 1


def test_leave_room_with_key_rotation(authenticated_socketio_client, second_authenticated_client, app):
    """Test leaving a room and then rotating keys by remaining participant"""
    # Get user IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]
        user1_id = user1.id
        user2_id = user2.id
        device1_id = device1.id
        device2_id = device2.id

    # Create room with both users (key version 1)
    authenticated_socketio_client.get_received()
    fake_key_1_v1 = base64.b64encode(b'encrypted_key_user1_v1').decode('utf-8')
    fake_key_2_v1 = base64.b64encode(b'encrypted_key_user2_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Leave Test With Rotation',
        'participant_ids': [user2_id],
        'encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1_v1},
            {'user_id': user2_id, 'device_id': device2_id, 'encrypted_key': fake_key_2_v1}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Leave Test With Rotation').first()
        room_id = room.id
        assert room.current_key_version == 1

    # User1 leaves room (no key rotation yet)
    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('leave_room', {'room_id': room_id})
    authenticated_socketio_client.get_received()

    # Verify user1 left but no key rotation yet
    with app.app_context():
        room = db.session.get(Room, room_id)
        assert len(room.participants) == 1
        assert room.current_key_version == 1  # Still version 1

    # User2 (remaining participant) rotates the key for forward secrecy
    second_authenticated_client.get_received()
    fake_key_2_v2 = base64.b64encode(b'encrypted_key_user2_v2').decode('utf-8')
    second_authenticated_client.emit('rotate_room_key', {
        'room_id': room_id,
        'new_encrypted_keys': [
            {'user_id': user2_id, 'device_id': device2_id, 'encrypted_key': fake_key_2_v2}
        ]
    })
    second_authenticated_client.get_received()

    # Verify in database
    with app.app_context():
        room = db.session.get(Room, room_id)
        assert room.current_key_version == 2  # Key rotated by user2

        # Verify old keys (v1) were revoked
        old_key_1 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1_id,
            key_version=1
        ).first()
        old_key_2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user2_id,
            key_version=1
        ).first()
        assert old_key_1.revoked_at is not None
        assert old_key_2.revoked_at is not None

        # Verify new key (v2) exists only for remaining user
        key2_v2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user2_id,
            device_id=device2_id,
            key_version=2
        ).first()
        assert key2_v2 is not None
        assert key2_v2.encrypted_key == fake_key_2_v2
        assert key2_v2.revoked_at is None

        # User1 should NOT have v2 key (forward secrecy)
        key1_v2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1_id,
            key_version=2
        ).first()
        assert key1_v2 is None

        # Verify system message for user leaving
        system_messages = Message.query.filter_by(
            room_id=room_id,
            message_type='system'
        ).all()
        # Should have only 1 message for user left (no key rotation message)
        assert len(system_messages) == 1
        left_msg = system_messages[0]
        assert 'left' in base64.b64decode(left_msg.encrypted_content).decode('utf-8')
        assert left_msg.sender_id is None
        assert left_msg.key_version == 1  # Created before rotation


def test_rotate_room_key_unauthorized(authenticated_socketio_client, second_authenticated_client, app):
    """Test that non-participants cannot rotate room keys"""
    # Get user IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        user1_id = user1.id
        device1_id = device1.id

    # Create room with only user1
    authenticated_socketio_client.get_received()
    fake_key_1 = base64.b64encode(b'encrypted_key_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Rotation Test Room',
        'encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1}
        ]
    })

    # Get room_id
    with app.app_context():
        room = Room.query.filter_by(name='Rotation Test Room').first()
        room_id = room.id
        initial_version = room.current_key_version

    # User2 (non-participant) tries to rotate keys
    second_authenticated_client.get_received()
    fake_key_2 = base64.b64encode(b'encrypted_key_v2').decode('utf-8')
    second_authenticated_client.emit('rotate_room_key', {
        'room_id': room_id,
        'new_encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_2}
        ]
    })
    second_authenticated_client.get_received()

    # Verify key version unchanged
    with app.app_context():
        room = db.session.get(Room, room_id)
        assert room.current_key_version == initial_version  # No change


def test_get_rooms(authenticated_socketio_client):
    """Test getting list of user's rooms"""
    # Create a room first
    authenticated_socketio_client.get_received('/')
    authenticated_socketio_client.emit('create_room', {'name': 'My Room'}, namespace='/')
    authenticated_socketio_client.get_received('/')

    # Get rooms list using callback
    response = authenticated_socketio_client.emit('get_rooms', {}, namespace='/', callback=True)

    assert response is not None
    assert 'rooms' in response
    assert len(response['rooms']) > 0

    # Verify room has current_key_version field
    room = response['rooms'][0]
    assert 'current_key_version' in room
    assert room['current_key_version'] == 1


# ===== KEY EXCHANGE TESTS =====

def test_get_room_keys(authenticated_socketio_client, second_authenticated_client, app):
    """Test getting public keys of room participants"""
    # Get second user ID
    with app.app_context():
        second_user = User.query.filter_by(username='seconduser').first()
        second_user_id = second_user.id

    # Create room with both users
    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('create_room', {
        'name': 'Key Test Room',
        'participant_ids': [second_user_id]
    })
    authenticated_socketio_client.get_received()

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Key Test Room').first()
        room_id = room.id

    # Get room keys using callback
    response = authenticated_socketio_client.emit('get_room_keys', {'room_id': room_id}, namespace='/', callback=True)

    assert response is not None
    assert 'participant_keys' in response
    assert len(response['participant_keys']) == 2  # Both users' devices


def test_exchange_key(authenticated_socketio_client, second_authenticated_client, app, sample_public_key):
    """Test exchanging encrypted symmetric keys with key_version"""
    # Get user IDs and device IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]

    # Create room
    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('create_room', {
        'name': 'Exchange Test',
        'participant_ids': [user2.id]
    })
    authenticated_socketio_client.get_received()

    # Get room_id
    with app.app_context():
        room = Room.query.filter_by(name='Exchange Test').first()
        room_id = room.id

    # Exchange encrypted symmetric keys for current key version
    fake_encrypted_key = base64.b64encode(b'encrypted_symmetric_key').decode('utf-8')

    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('exchange_key', {
        'room_id': room_id,
        'encrypted_keys': [
            {'user_id': user1.id, 'device_id': device1.id, 'encrypted_key': fake_encrypted_key, 'key_version': 1},
            {'user_id': user2.id, 'device_id': device2.id, 'encrypted_key': fake_encrypted_key, 'key_version': 1}
        ]
    })

    # Verify keys in database with correct version (primary verification)
    with app.app_context():
        key1 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1.id,
            key_version=1
        ).first()
        key2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user2.id,
            key_version=1
        ).first()
        assert key1 is not None
        assert key2 is not None
        assert key1.key_version == 1
        assert key2.key_version == 1
        assert key1.encrypted_key == fake_encrypted_key
        assert key2.encrypted_key == fake_encrypted_key


# ===== ENCRYPTED MESSAGING TESTS =====

def test_send_encrypted_message(authenticated_socketio_client, app):
    """Test sending encrypted message to a room with key_version"""
    # Get user info
    with app.app_context():
        user = User.query.filter_by(username='socketuser').first()
        device = user.devices[0]
        user_id = user.id
        device_id = device.id

    # Create room
    authenticated_socketio_client.get_received()
    fake_key = base64.b64encode(b'encrypted_key_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Message Test',
        'encrypted_keys': [
            {'user_id': user_id, 'device_id': device_id, 'encrypted_key': fake_key}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Message Test').first()
        room_id = room.id

    # Send encrypted message
    authenticated_socketio_client.get_received()
    fake_encrypted_content = base64.b64encode(b'Hello, encrypted world!').decode('utf-8')
    fake_iv = base64.b64encode(b'1234567890123456').decode('utf-8')

    authenticated_socketio_client.emit('send_message', {
        'room_id': room_id,
        'encrypted_content': fake_encrypted_content,
        'iv': fake_iv,
        'key_version': 1
    }, namespace='/')

    # Verify message in database (primary validation)
    with app.app_context():
        message = Message.query.filter_by(room_id=room_id).first()
        assert message is not None
        assert message.encrypted_content == fake_encrypted_content
        assert message.iv == fake_iv
        assert message.key_version == 1


def test_get_room_messages(authenticated_socketio_client, app):
    """Test retrieving room message history with encrypted_symmetric_keys"""
    # Get user info
    with app.app_context():
        user = User.query.filter_by(username='socketuser').first()
        device = user.devices[0]
        user_id = user.id
        device_id = device.id

    # Create room
    authenticated_socketio_client.get_received()
    fake_key = base64.b64encode(b'encrypted_key_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'History Test',
        'encrypted_keys': [
            {'user_id': user_id, 'device_id': device_id, 'encrypted_key': fake_key}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='History Test').first()
        room_id = room.id

    # Send a message
    authenticated_socketio_client.get_received()
    fake_encrypted_content = base64.b64encode(b'Test message').decode('utf-8')
    fake_iv = base64.b64encode(b'1234567890123456').decode('utf-8')

    authenticated_socketio_client.emit('send_message', {
        'room_id': room_id,
        'encrypted_content': fake_encrypted_content,
        'iv': fake_iv
    })
    authenticated_socketio_client.get_received()

    # Get messages using callback
    response = authenticated_socketio_client.emit('get_room_messages', {
        'room_id': room_id,
        'limit': 10
    }, namespace='/', callback=True)

    assert response is not None
    assert 'messages' in response
    assert len(response['messages']) == 1
    assert response['messages'][0]['encrypted_content'] == fake_encrypted_content

    # Verify encrypted_symmetric_keys are returned
    assert 'encrypted_symmetric_keys' in response
    # Convert string keys to int for comparison
    keys = {int(k): v for k, v in response['encrypted_symmetric_keys'].items()}
    assert 1 in keys
    assert keys[1] == fake_key
    assert 'current_key_version' in response
    assert response['current_key_version'] == 1


def test_send_message_to_non_participant_room(authenticated_socketio_client, second_authenticated_client, app):
    """Test that users can't send messages to rooms they're not in"""
    # Get user info
    with app.app_context():
        user = User.query.filter_by(username='socketuser').first()
        device = user.devices[0]
        user_id = user.id
        device_id = device.id

    # First user creates room (without second user)
    authenticated_socketio_client.get_received()
    fake_key = base64.b64encode(b'encrypted_key_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Private Room',
        'encrypted_keys': [
            {'user_id': user_id, 'device_id': device_id, 'encrypted_key': fake_key}
        ]
    })

    # Get room_id from database
    with app.app_context():
        room = Room.query.filter_by(name='Private Room').first()
        room_id = room.id

    # Second user tries to send message
    second_authenticated_client.get_received()
    second_authenticated_client.emit('send_message', {
        'room_id': room_id,
        'encrypted_content': 'unauthorized',
        'iv': 'test'
    }, namespace='/')

    # Verify message was NOT saved to database (primary validation)
    with app.app_context():
        message = Message.query.filter_by(
            room_id=room_id,
            encrypted_content='unauthorized'
        ).first()
        assert message is None  # Message should not be saved


def test_multiple_key_versions_in_get_room_messages(authenticated_socketio_client, second_authenticated_client, app):
    """Test that get_room_messages returns all key versions user has access to"""
    # Get user IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]
        user1_id = user1.id
        user2_id = user2.id
        device1_id = device1.id
        device2_id = device2.id

    # Create room with user1 (key version 1)
    authenticated_socketio_client.get_received()
    fake_key_1_v1 = base64.b64encode(b'key_user1_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Multi Version Test',
        'encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1_v1}
        ]
    })

    # Get room_id
    with app.app_context():
        room = Room.query.filter_by(name='Multi Version Test').first()
        room_id = room.id

    # Send message with v1
    authenticated_socketio_client.get_received()
    msg1_content = base64.b64encode(b'Message with v1').decode('utf-8')
    msg1_iv = base64.b64encode(b'1234567890123456').decode('utf-8')
    authenticated_socketio_client.emit('send_message', {
        'room_id': room_id,
        'encrypted_content': msg1_content,
        'iv': msg1_iv,
        'key_version': 1
    })
    authenticated_socketio_client.get_received()

    # Invite user2 (key rotation to v2)
    fake_key_1_v2 = base64.b64encode(b'key_user1_v2').decode('utf-8')
    fake_key_2_v2 = base64.b64encode(b'key_user2_v2').decode('utf-8')
    authenticated_socketio_client.emit('invite_to_room', {
        'room_id': room_id,
        'invited_user_ids': [user2_id],
        'new_encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1_v2},
            {'user_id': user2_id, 'device_id': device2_id, 'encrypted_key': fake_key_2_v2}
        ]
    })
    authenticated_socketio_client.get_received()

    # Send message with v2
    msg2_content = base64.b64encode(b'Message with v2').decode('utf-8')
    msg2_iv = base64.b64encode(b'6543210987654321').decode('utf-8')
    authenticated_socketio_client.emit('send_message', {
        'room_id': room_id,
        'encrypted_content': msg2_content,
        'iv': msg2_iv,
        'key_version': 2
    })
    authenticated_socketio_client.get_received()

    # User1 gets messages - should have both v1 and v2 keys
    response = authenticated_socketio_client.emit('get_room_messages', {'room_id': room_id}, namespace='/', callback=True)

    assert response is not None
    # Convert string keys to int for comparison
    keys = {int(k): v for k, v in response['encrypted_symmetric_keys'].items()}
    assert 1 in keys
    assert 2 in keys
    assert keys[1] == fake_key_1_v1
    assert keys[2] == fake_key_1_v2
    assert response['current_key_version'] == 2
    assert len(response['messages']) == 3  # 2 user messages + 1 system message (user joined)

    # User2 gets messages - should have ONLY v2 key (backward secrecy)
    response = second_authenticated_client.emit('get_room_messages', {'room_id': room_id}, namespace='/', callback=True)

    assert response is not None
    # Convert string keys to int for comparison
    keys = {int(k): v for k, v in response['encrypted_symmetric_keys'].items()}
    assert 1 not in keys  # User2 should NOT have v1 key
    assert 2 in keys
    assert keys[2] == fake_key_2_v2


def test_forward_secrecy_after_leave(authenticated_socketio_client, second_authenticated_client, app):
    """Test that leaving user cannot decrypt messages sent after they leave"""
    # Get user IDs
    with app.app_context():
        user1 = User.query.filter_by(username='socketuser').first()
        user2 = User.query.filter_by(username='seconduser').first()
        device1 = user1.devices[0]
        device2 = user2.devices[0]
        user1_id = user1.id
        user2_id = user2.id
        device1_id = device1.id
        device2_id = device2.id

    # Create room with both users (v1)
    authenticated_socketio_client.get_received()
    fake_key_1_v1 = base64.b64encode(b'key_user1_v1').decode('utf-8')
    fake_key_2_v1 = base64.b64encode(b'key_user2_v1').decode('utf-8')
    authenticated_socketio_client.emit('create_room', {
        'name': 'Forward Secrecy Test',
        'participant_ids': [user2_id],
        'encrypted_keys': [
            {'user_id': user1_id, 'device_id': device1_id, 'encrypted_key': fake_key_1_v1},
            {'user_id': user2_id, 'device_id': device2_id, 'encrypted_key': fake_key_2_v1}
        ]
    })

    # Get room_id
    with app.app_context():
        room = Room.query.filter_by(name='Forward Secrecy Test').first()
        room_id = room.id

    # User1 leaves room
    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('leave_room', {'room_id': room_id})
    authenticated_socketio_client.get_received()

    # User2 rotates key for forward secrecy
    second_authenticated_client.get_received()
    fake_key_2_v2 = base64.b64encode(b'key_user2_v2').decode('utf-8')
    second_authenticated_client.emit('rotate_room_key', {
        'room_id': room_id,
        'new_encrypted_keys': [
            {'user_id': user2_id, 'device_id': device2_id, 'encrypted_key': fake_key_2_v2}
        ]
    })
    second_authenticated_client.get_received()

    # User2 sends message with v2
    msg_content = base64.b64encode(b'Secret message after user1 left').decode('utf-8')
    msg_iv = base64.b64encode(b'1234567890123456').decode('utf-8')
    second_authenticated_client.emit('send_message', {
        'room_id': room_id,
        'encrypted_content': msg_content,
        'iv': msg_iv,
        'key_version': 2
    })

    # Verify in database that user1 does NOT have v2 key
    with app.app_context():
        key1_v2 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1_id,
            key_version=2
        ).first()
        assert key1_v2 is None  # Forward secrecy: user1 cannot decrypt v2 messages

        # User1 still has v1 key (can decrypt old messages)
        key1_v1 = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user1_id,
            key_version=1
        ).first()
        assert key1_v1 is not None

        # Message exists with v2
        message = Message.query.filter_by(
            room_id=room_id,
            encrypted_content=msg_content
        ).first()
        assert message is not None
        assert message.key_version == 2

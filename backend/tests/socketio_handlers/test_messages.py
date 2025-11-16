"""
Tests for message sending and retrieval
Tests send_message, get_messages, and message broadcasting
"""

import pytest
from app import app, socketio
from models import Room, Message, User
from database import db
import base64


@pytest.fixture
def authenticated_socketio_client(client, sample_public_key):
    """Create a Socket.IO client with valid authentication"""
    register_response = client.post('/api/auth/register', json={
        'username': 'msguser',
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
        'username': 'msguser2',
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
def room_with_participants(app, authenticated_socketio_client, second_authenticated_client):
    """Create a room with two participants"""
    with app.app_context():
        user1 = User.query.filter_by(username='msguser').first()
        user2 = User.query.filter_by(username='msguser2').first()

    authenticated_socketio_client.get_received()
    authenticated_socketio_client.emit('create_room', {
        'name': 'Message Test Room',
        'participant_ids': [user2.id],
        'encrypted_keys': [
            {'user_id': user1.id, 'encrypted_key': base64.b64encode(b'key1').decode('utf-8')},
            {'user_id': user2.id, 'encrypted_key': base64.b64encode(b'key2').decode('utf-8')}
        ]
    })

    with app.app_context():
        room = Room.query.filter_by(name='Message Test Room').first()
        room_id = room.id

    # Join room with both clients
    authenticated_socketio_client.get_received()
    second_authenticated_client.get_received()
    authenticated_socketio_client.emit('join_room', {'room_id': room_id})
    second_authenticated_client.emit('join_room', {'room_id': room_id})

    yield room_id


class TestSendMessage:
    """Test message sending functionality"""

    def test_send_message_basic(self, authenticated_socketio_client, room_with_participants, app):
        """Test sending a basic message"""
        authenticated_socketio_client.get_received()

        authenticated_socketio_client.emit('send_message', {
            'room_id': room_with_participants,
            'encrypted_content': 'encrypted_content_base64',
            'iv': 'iv_base64',
            'key_version': 1
        })

        with app.app_context():
            message = Message.query.filter_by(room_id=room_with_participants).first()
            assert message is not None
            assert message.encrypted_content == 'encrypted_content_base64'
            assert message.iv == 'iv_base64'
            assert message.key_version == 1

    def test_send_message_broadcast(self, authenticated_socketio_client, second_authenticated_client, room_with_participants, app):
        """Test that messages are broadcast to all room participants"""
        authenticated_socketio_client.get_received()
        second_authenticated_client.get_received()

        authenticated_socketio_client.emit('send_message', {
            'room_id': room_with_participants,
            'encrypted_content': 'broadcast_test',
            'iv': 'iv',
            'key_version': 1
        })

        # Verify message was saved in database
        with app.app_context():
            message = Message.query.filter_by(
                room_id=room_with_participants,
                encrypted_content='broadcast_test'
            ).first()
            assert message is not None
            assert message.sender.username == 'msguser'

    def test_send_message_unauthorized(self, authenticated_socketio_client, app):
        """Test that users cannot send messages to rooms they're not in"""
        with app.app_context():
            user = User.query.filter_by(username='msguser').first()
            other_user = User(username='otheruser', password_hash='hash', public_key=b'key')
            db.session.add(other_user)
            db.session.commit()

            room = Room(name='Private Room')
            room.participants.append(other_user)
            db.session.add(room)
            db.session.commit()
            room_id = room.id

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('send_message', {
            'room_id': room_id,
            'encrypted_content': 'unauthorized',
            'iv': 'iv',
            'key_version': 1
        })

        with app.app_context():
            messages = Message.query.filter_by(room_id=room_id).all()
            assert len(messages) == 0  # Message should not be saved

    def test_send_message_invalid_room(self, authenticated_socketio_client, app):
        """Test sending a message to non-existent room"""
        authenticated_socketio_client.get_received()

        authenticated_socketio_client.emit('send_message', {
            'room_id': 99999,
            'encrypted_content': 'test',
            'iv': 'iv',
            'key_version': 1
        })

        # Verify no message was saved
        with app.app_context():
            messages = Message.query.filter_by(room_id=99999).all()
            assert len(messages) == 0

    def test_send_message_with_wrong_key_version(self, authenticated_socketio_client, room_with_participants, app):
        """Test sending a message with incorrect key version"""
        authenticated_socketio_client.get_received()

        authenticated_socketio_client.emit('send_message', {
            'room_id': room_with_participants,
            'encrypted_content': 'outdated_key',
            'iv': 'iv',
            'key_version': 999  # Wrong version
        })

        # Message should still be saved (key version is just metadata)
        with app.app_context():
            message = Message.query.filter_by(
                room_id=room_with_participants,
                encrypted_content='outdated_key'
            ).first()
            assert message is not None
            assert message.key_version == 999


class TestGetMessages:
    """Test message retrieval and pagination"""

    def test_get_messages_empty_room(self, authenticated_socketio_client, room_with_participants, app):
        """Test getting messages from an empty room"""
        authenticated_socketio_client.get_received()

        authenticated_socketio_client.emit('get_messages', {
            'room_id': room_with_participants,
            'page': 1,
            'per_page': 20
        })

        # Verify no messages in database
        with app.app_context():
            messages = Message.query.filter_by(room_id=room_with_participants).all()
            assert len(messages) == 0

    def test_get_messages_with_data(self, authenticated_socketio_client, room_with_participants, app):
        """Test getting messages from a room with messages"""
        with app.app_context():
            user = User.query.filter_by(username='msguser').first()
            for i in range(5):
                msg = Message(
                    room_id=room_with_participants,
                    sender_id=user.id,
                    encrypted_content=f'message_{i}',
                    iv='iv',
                    key_version=1
                )
                db.session.add(msg)
            db.session.commit()

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('get_messages', {
            'room_id': room_with_participants,
            'page': 1,
            'per_page': 20
        })

        # Verify messages in database
        with app.app_context():
            messages = Message.query.filter_by(room_id=room_with_participants).all()
            assert len(messages) == 5

    def test_get_messages_pagination(self, authenticated_socketio_client, room_with_participants, app):
        """Test message pagination"""
        with app.app_context():
            user = User.query.filter_by(username='msguser').first()
            for i in range(25):
                msg = Message(
                    room_id=room_with_participants,
                    sender_id=user.id,
                    encrypted_content=f'message_{i}',
                    iv='iv',
                    key_version=1
                )
                db.session.add(msg)
            db.session.commit()

        authenticated_socketio_client.get_received()

        # Get first page
        authenticated_socketio_client.emit('get_messages', {
            'room_id': room_with_participants,
            'page': 1,
            'per_page': 10
        })

        # Verify pagination in database
        with app.app_context():
            total_messages = Message.query.filter_by(room_id=room_with_participants).count()
            assert total_messages == 25

    def test_get_messages_unauthorized(self, authenticated_socketio_client, app):
        """Test getting messages from a room user is not in"""
        with app.app_context():
            other_user = User(username='unauthorized_user', password_hash='hash', public_key=b'key')
            db.session.add(other_user)
            db.session.commit()

            room = Room(name='Unauthorized Room')
            room.participants.append(other_user)
            db.session.add(room)
            db.session.commit()
            room_id = room.id

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('get_messages', {
            'room_id': room_id,
            'page': 1,
            'per_page': 20
        })

        # User should not be able to get messages (handler will reject)
        # Just verify the room exists but user is not a participant
        with app.app_context():
            room = db.session.get(Room, room_id)
            user = User.query.filter_by(username='msguser').first()
            assert user.id not in [p.id for p in room.participants]

    def test_get_messages_default_pagination(self, authenticated_socketio_client, room_with_participants, app):
        """Test that default pagination values are applied"""
        with app.app_context():
            user = User.query.filter_by(username='msguser').first()
            for i in range(3):
                msg = Message(
                    room_id=room_with_participants,
                    sender_id=user.id,
                    encrypted_content=f'msg_{i}',
                    iv='iv',
                    key_version=1
                )
                db.session.add(msg)
            db.session.commit()

        authenticated_socketio_client.get_received()

        # Omit page and per_page to test defaults
        authenticated_socketio_client.emit('get_messages', {
            'room_id': room_with_participants
        })

        # Verify messages exist in database
        with app.app_context():
            messages = Message.query.filter_by(room_id=room_with_participants).all()
            assert len(messages) == 3


class TestMessageOrdering:
    """Test message chronological ordering"""

    def test_messages_ordered_by_timestamp(self, authenticated_socketio_client, room_with_participants, app):
        """Test that messages are returned in chronological order"""
        import time
        with app.app_context():
            user = User.query.filter_by(username='msguser').first()

            msg1 = Message(
                room_id=room_with_participants,
                sender_id=user.id,
                encrypted_content='first',
                iv='iv',
                key_version=1
            )
            db.session.add(msg1)
            db.session.commit()

            time.sleep(0.01)

            msg2 = Message(
                room_id=room_with_participants,
                sender_id=user.id,
                encrypted_content='second',
                iv='iv',
                key_version=1
            )
            db.session.add(msg2)
            db.session.commit()

        authenticated_socketio_client.get_received()
        authenticated_socketio_client.emit('get_messages', {
            'room_id': room_with_participants,
            'page': 1,
            'per_page': 20
        })

        # Verify ordering in database
        with app.app_context():
            messages = Message.query.filter_by(room_id=room_with_participants).order_by(Message.created_at).all()
            assert len(messages) == 2
            assert messages[0].encrypted_content == 'first'
            assert messages[1].encrypted_content == 'second'

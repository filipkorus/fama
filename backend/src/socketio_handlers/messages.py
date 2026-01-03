"""
Message handling WebSocket handlers
Handles sending and receiving encrypted messages and Session Keys
"""

from flask import request
from flask_socketio import emit
from logging import getLogger

from ..database import db
from ..models import User, Message, EncryptedSessionKey
from .connected_users_manager import SocketIOConnectedUsersManager

sio_conn_users = SocketIOConnectedUsersManager()

logger = getLogger('app')


def register_message_handlers(socketio):
    """Register message-related WebSocket handlers"""

    def validate_data_is_dict(data):
        if not isinstance(data, dict):
            emit('error', {'message': 'Invalid data format: expected JSON object'})
            return False
        return True

    @socketio.on('publish_session_key')
    def handle_publish_session_key(data):
        """
        Handle receiving a new Shared Secret (Session Key) from Sender.
        """
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        if not sender_id:
            emit('error', {'message': 'Not authenticated'})
            return

        recipient_id = data.get('recipient_id')
        capsule = data.get('capsule_mlkem')
        enc_secret = data.get('encrypted_shared_secret')
        key_nonce = data.get('key_nonce')

        if not all([recipient_id, capsule, enc_secret, key_nonce]):
            emit('error', {'message': 'Missing session key data'})
            return

        session_key = EncryptedSessionKey(
            sender_id=sender_id,
            recipient_id=recipient_id,
            capsule_mlkem=capsule,
            encrypted_shared_secret=enc_secret,
            key_nonce=key_nonce
        )

        try:
            db.session.add(session_key)
            db.session.commit()
            logger.info(f"Session Key stored: ID {session_key.id} | Sender: {sender_id} -> Recipient: {recipient_id}")

            emit('session_key_published', {
                'session_key_id': session_key.id,
                'recipient_id': recipient_id
            }, room=request.sid)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save session key: {str(e)}")
            emit('error', {'message': 'Failed to save session key'})

    @socketio.on('request_session_key')
    def handle_request_session_key(data):
        """
        Recipient requests the encrypted Shared Secret.
        """
        requester_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        if not requester_id:
            emit('error', {'message': 'Not authenticated'})
            return

        session_key_id = data.get('session_key_id')
        key_record = db.session.get(EncryptedSessionKey, session_key_id)

        if not key_record:
            emit('error', {'message': 'Session key not found'})
            return

        if key_record.recipient_id != requester_id and key_record.sender_id != requester_id:
            emit('error', {'message': 'Access denied'})
            return

        emit('session_key_data', {
            'session_key_id': key_record.id,
            'sender_id': key_record.sender_id,
            'capsule_mlkem': key_record.capsule_mlkem,
            'encrypted_shared_secret': key_record.encrypted_shared_secret,
            'key_nonce': key_record.key_nonce
        }, room=request.sid)

    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Handle sending a message using an existing Session Key.
        Expected data: {
            'recipient_id': <int>,
            'session_key_id': <int>,        # ID of the previously negotiated key
            'message_type': <str>,          # 'text' or 'attachment'
            'encrypted_content': <str>,     # Content encrypted with Shared Secret
            'nonce': <str>                  # AES IV for this specific message
        }
        """
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        sender_username = sio_conn_users.get_username_by_user_id(sender_id) if sender_id else 'unknown'

        if not sio_conn_users.is_authenticated(sid=request.sid):
            emit('error', {'message': 'Not authenticated'})
            return

        if not validate_data_is_dict(data):
            return

        recipient_id = data.get('recipient_id')
        session_key_id = data.get('session_key_id')
        message_type = data.get('message_type', 'text')  # Default to 'text' for backward compatibility
        encrypted_content = data.get('encrypted_content')
        nonce = data.get('nonce')

        if not all([recipient_id, session_key_id, encrypted_content, nonce]):
            logger.warning(f'send_message rejected: Missing required fields from {sender_username}')
            emit('error', {'message': 'Invalid message data'})
            return

        if message_type not in ['text', 'attachment']:
            emit('error', {'message': 'Invalid message_type. Must be "text" or "attachment"'})
            return

        session_key = db.session.get(EncryptedSessionKey, session_key_id)
        if not session_key:
            emit('error', {'message': 'Invalid Session Key ID'})
            return

        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            session_key_id=session_key_id,
            message_type=message_type,
            encrypted_content=encrypted_content,
            nonce=nonce
        )

        try:
            db.session.add(message)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f'Failed to save message: {str(e)}')
            emit('error', {'message': 'Failed to save message'})
            return

        recipient_sid = sio_conn_users.get_sid_by_user_id(user_id=recipient_id)
        if recipient_sid:
            sender_user = db.session.get(User, sender_id)
            sender_data = sender_user.to_dict_for_message(message_type) if sender_user else {
                'id': sender_id,
                'username': sender_username
            }

            emit('receive_message', {
                'id': message.id,
                'sender': sender_data,
                'recipient': {'id': recipient_id},
                'session_key_id': session_key_id,
                'message_type': message_type,
                'encrypted_content': encrypted_content,
                'nonce': nonce,
                'created_at': message.created_at.isoformat()
            }, room=recipient_sid)

            emit('message_delivered', {'message_id': message.id}, room=request.sid)
            message.mark_as_delivered()

        logger.info(f'Message {message.id} processed from {sender_username}')

    @socketio.on('get_messages')
    def handle_get_messages(data):
        """
        Get message history.
        Returns messages with 'session_key_id' so client can map decryption keys.
        """
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        if not sender_id:
            emit('error', {'message': 'Not authenticated'})
            return

        recipient_id = data.get('recipient_id')
        limit = data.get('limit', 50)
        offset = data.get('offset', 0)

        if not recipient_id:
            emit('error', {'message': 'recipient_id is required'})
            return

        try:
            messages = Message.query_messages_between(sender_id, recipient_id, limit=limit, offset=offset)

            for message in messages['messages']:
                if message['recipient_id'] == sender_id and not message['is_delivered']:
                    db.session.query(Message).filter_by(id=message['id']).update({"is_delivered": True})
            db.session.commit()

            messages['recipient_id'] = recipient_id
            emit('messages_history', messages, room=request.sid)

        except Exception as e:
            logger.error(f'get_messages error: {str(e)}')
            emit('error', {'message': 'Failed to fetch messages'})

    @socketio.on('get_recent_and_available_users')
    def handle_get_recent_and_available_users(data):
        """
        Fetch users with whom the current user has recently communicated and other available users.
        Returns:
        - recent_users: List of {id, last_message_date}
        - available_users: List of user IDs
        """
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        if not sender_id:
            emit('error', {'message': 'Not authenticated'})
            return

        try:
            result = Message.query_recent_and_available_users(sender_id)
            emit('recent_and_available_users', result, room=request.sid)
        except Exception as e:
            emit('error', {'message': 'Failed to fetch users'})

"""
Message handling WebSocket handlers
Handles sending and receiving encrypted messages
"""

from flask import request
from flask_socketio import emit
from logging import getLogger

from ..database import db
from ..models import User, Message
from .connected_users_manager import SocketIOConnectedUsersManager

sio_conn_users = SocketIOConnectedUsersManager()

logger = getLogger('app')


def register_message_handlers(socketio):
    """Register message-related WebSocket handlers"""

    def validate_data_is_dict(data):
        """
        Validate that the provided data is a dictionary.
        Emit an error message and return False if validation fails.
        """
        if not isinstance(data, dict):
            emit('error', {'message': 'Invalid data format: expected JSON object'})
            return False
        return True

    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Handle sending a message from one user to another
        Expected data: {
            'recipient_id': <int>,
            'encrypted_content': <str>,
            'capsule_mlkem': <str>,
            'nonce': <str>
        }
        """
        if not sio_conn_users.is_authenticated(sid=request.sid):
            emit('error', {'message': 'Not authenticated'})
            return

        sender_id = sio_conn_users.get_sender_id(sid=request.sid)
        if not sender_id:
            emit('error', {'message': 'Sender not found'})
            return

        if not validate_data_is_dict(data):
            return

        recipient_id = data.get('recipient_id')
        encrypted_content = data.get('encrypted_content')
        capsule_mlkem = data.get('capsule_mlkem')
        nonce = data.get('nonce')

        if not recipient_id or not encrypted_content or not capsule_mlkem or not nonce:
            emit('error', {'message': 'Invalid message data'})
            return

        if sender_id == recipient_id:
            emit('error', {'message': 'Cannot send message to yourself'})
            return

        recipient = db.session.get(User, recipient_id)
        if not recipient or not recipient.is_active:
            emit('error', {'message': 'Recipient not found'})
            return

        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            encrypted_content=encrypted_content,
            capsule_mlkem=capsule_mlkem,
            nonce=nonce
        )
        try:
            db.session.add(message)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            emit('error', {'message': 'Failed to save message'})
            return

        recipient_sid = sio_conn_users.get_sender_sid(user_id=recipient_id)
        if recipient_sid:
            emit('receive_message', {
                'id': message.id,
                'sender': {
                    'id': sender_id,
                    'username': sio_conn_users.get_sender_username(sid=request.sid)
                },
                'encrypted_content': encrypted_content,
                'capsule_mlkem': capsule_mlkem,
                'nonce': nonce,
                'is_delivered': True,
                'created_at': message.created_at.isoformat()
            }, room=recipient_sid)

            emit('message_delivered', {'message_id': message.id}, room=request.sid)

            message.mark_as_delivered()

        logger.info(f'Message from {sender_id} to {recipient_id} forwarded successfully')

    @socketio.on('get_messages')
    def handle_get_messages(data):
        """
        Get message history for a 1:1 chat and mark messages as delivered.

        Data should include:
        - recipient_id: int
        - limit: int (optional, default 50)
        - offset: int (optional, default 0)
        """
        if not sio_conn_users.is_authenticated(sid=request.sid):
            emit('error', {'message': 'Not authenticated'})
            return

        sender_id = sio_conn_users.get_sender_id(sid=request.sid)
        if not sender_id:
            emit('error', {'message': 'Sender not found'})
            return

        if not validate_data_is_dict(data):
            emit('error', {'message': 'Invalid data format'})
            return

        recipient_id = data.get('recipient_id')
        limit = data.get('limit', 50)
        offset = data.get('offset', 0)

        if not recipient_id:
            emit('error', {'message': 'recipient_id is required'})
            return

        try:
            recipient = db.session.get(User, recipient_id)
            if not recipient or not recipient.is_active:
                emit('error', {'message': 'Recipient not found'})
                return

            messages = Message.query_messages_between(sender_id, recipient_id, limit=limit, offset=offset)

            for message in messages['messages']:
                if message['recipient_id'] == sender_id and not message['is_delivered']:
                    db.session.query(Message).filter_by(id=message['id']).update({"is_delivered": True})
            db.session.commit()

            emit('messages_history', messages)

        except Exception as e:
            logger.error(f'Failed to get messages: {str(e)}')
            emit('error', {'message': f'Failed to get messages: {str(e)}'})

    @socketio.on('get_recent_and_available_users')
    def handle_get_recent_and_available_users(data):
        """
        Fetch users with whom the current user has recently communicated and other available users.
        Returns:
        - recent_users: List of {id, last_message_date}
        - available_users: List of user IDs
        """
        if not sio_conn_users.is_authenticated(sid=request.sid):
            emit('error', {'message': 'Not authenticated'})
            return

        sender_id = sio_conn_users.get_sender_id(sid=request.sid)
        if not sender_id:
            emit('error', {'message': 'Sender not found'})
            return

        try:
            result = Message.query_recent_and_available_users(sender_id)

            emit('recent_and_available_users', {
                'recent_users': result['recent_users'],
                'available_users': result['available_users']
            })

        except Exception as e:
            logger.error(f'Failed to fetch recent and available users: {str(e)}')
            emit('error', {'message': 'Failed to fetch users'})

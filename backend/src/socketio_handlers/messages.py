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
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        sender_username = sio_conn_users.get_username_by_user_id(sender_id) if sender_id else 'unknown'
        logger.info(f'send_message event received from {sender_username} ({sender_id})')
        
        if not sio_conn_users.is_authenticated(sid=request.sid):
            logger.warning(f'send_message rejected: Not authenticated from {sender_username} ({request.sid})')
            emit('error', {'message': 'Not authenticated'})
            return

        if not sender_id:
            logger.warning(f'send_message rejected: Sender not found for {request.sid}')
            emit('error', {'message': 'Sender not found'})
            return

        if not validate_data_is_dict(data):
            logger.warning(f'send_message rejected: Invalid data format from {sender_username}')
            return

        recipient_id = data.get('recipient_id')
        encrypted_content = data.get('encrypted_content')
        capsule_mlkem = data.get('capsule_mlkem')
        nonce = data.get('nonce')
        recipient_username = sio_conn_users.get_username_by_user_id(recipient_id) if recipient_id else 'unknown'

        logger.debug(f'send_message data - sender: {sender_username}, recipient: {recipient_username}')

        if not recipient_id or not encrypted_content or not capsule_mlkem or not nonce:
            logger.warning(f'send_message rejected: Missing required fields from {sender_username}')
            emit('error', {'message': 'Invalid message data'})
            return

        if sender_id == recipient_id:
            logger.warning(f'send_message rejected: {sender_username} tried to send message to themselves')
            emit('error', {'message': 'Cannot send message to yourself'})
            return

        recipient = db.session.get(User, recipient_id)
        if not recipient or not recipient.is_active:
            logger.warning(f'send_message rejected: Recipient {recipient_username} not found or inactive')
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
            logger.debug(f'send_message: Message {message.id} saved to database')
        except Exception as e:
            db.session.rollback()
            logger.error(f'send_message error: Failed to save message from {sender_username} to {recipient_username}: {str(e)}')
            emit('error', {'message': 'Failed to save message'})
            return

        recipient_sid = sio_conn_users.get_sid_by_user_id(user_id=recipient_id)
        if recipient_sid:
            logger.info(f'send_message: Delivering message {message.id} to {recipient_username} (online)')
            emit('receive_message', {
                'id': message.id,
                'sender': {
                    'id': sender_id,
                    'username': sender_username
                },
                'encrypted_content': encrypted_content,
                'capsule_mlkem': capsule_mlkem,
                'nonce': nonce,
                'is_delivered': True,
                'created_at': message.created_at.isoformat()
            }, room=recipient_sid)

            emit('message_delivered', {'message_id': message.id}, room=request.sid)

            message.mark_as_delivered()
            logger.info(f'send_message: Message {message.id} marked as delivered')
        else:
            logger.info(f'send_message: Recipient {recipient_username} is offline, message stored for later delivery')

        logger.info(f'send_message: Message from {sender_username} to {recipient_username} processed successfully')

    @socketio.on('get_messages')
    def handle_get_messages(data):
        """
        Get message history for a 1:1 chat and mark messages as delivered.

        Data should include:
        - recipient_id: int
        - limit: int (optional, default 50)
        - offset: int (optional, default 0)
        """
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        sender_username = sio_conn_users.get_username_by_user_id(sender_id) if sender_id else 'unknown'
        logger.info(f'get_messages event received from {sender_username} ({sender_id})')
        
        if not sio_conn_users.is_authenticated(sid=request.sid):
            logger.warning(f'get_messages rejected: Not authenticated from {sender_username} ({request.sid})')
            emit('error', {'message': 'Not authenticated'})
            return

        if not sender_id:
            logger.warning(f'get_messages rejected: Sender not found for {request.sid}')
            emit('error', {'message': 'Sender not found'})
            return

        if not validate_data_is_dict(data):
            logger.warning(f'get_messages rejected: Invalid data format from {sender_username}')
            emit('error', {'message': 'Invalid data format'})
            return

        recipient_id = data.get('recipient_id')
        limit = data.get('limit', 50)
        offset = data.get('offset', 0)
        recipient_username = sio_conn_users.get_username_by_user_id(recipient_id) if recipient_id else 'unknown'

        logger.debug(f'get_messages data - sender: {sender_username}, recipient: {recipient_username}, limit: {limit}, offset: {offset}')

        if not recipient_id:
            logger.warning(f'get_messages rejected: recipient_id is required from {sender_username}')
            emit('error', {'message': 'recipient_id is required'})
            return

        try:
            recipient = db.session.get(User, recipient_id)
            if not recipient or not recipient.is_active:
                logger.warning(f'get_messages rejected: Recipient {recipient_username} not found or inactive')
                emit('error', {'message': 'Recipient not found'})
                return

            logger.debug(f'get_messages: Querying messages between {sender_username} and {recipient_username}')
            messages = Message.query_messages_between(sender_id, recipient_id, limit=limit, offset=offset)

            for message in messages['messages']:
                if message['recipient_id'] == sender_id and not message['is_delivered']:
                    db.session.query(Message).filter_by(id=message['id']).update({"is_delivered": True})
            db.session.commit()
            logger.debug(f'get_messages: Marked {len([m for m in messages["messages"] if m["recipient_id"] == sender_id])} messages as delivered')

            logger.info(f'get_messages: Sent {len(messages["messages"])} messages to {sender_username}')
            emit('messages_history', messages, room=request.sid)

        except Exception as e:
            logger.error(f'get_messages error: Failed to get messages for {sender_username}: {str(e)}')
            emit('error', {'message': f'Failed to get messages: {str(e)}'})


    @socketio.on('get_recent_and_available_users')
    def handle_get_recent_and_available_users(data):
        """
        Fetch users with whom the current user has recently communicated and other available users.
        Returns:
        - recent_users: List of {id, last_message_date}
        - available_users: List of user IDs
        """
        sender_id = sio_conn_users.get_user_id_by_sid(sid=request.sid)
        sender_username = sio_conn_users.get_username_by_user_id(sender_id) if sender_id else 'unknown'
        logger.info(f'get_recent_and_available_users event received from {sender_username} ({sender_id})')
        
        if not sio_conn_users.is_authenticated(sid=request.sid):
            logger.warning(f'get_recent_and_available_users rejected: Not authenticated from {sender_username} ({request.sid})')
            emit('error', {'message': 'Not authenticated'})
            return

        if not sender_id:
            logger.warning(f'get_recent_and_available_users rejected: Sender not found for {request.sid}')
            emit('error', {'message': 'Sender not found'})
            return

        try:
            logger.debug(f'get_recent_and_available_users: Querying users for {sender_username}')
            result = Message.query_recent_and_available_users(sender_id)
            
            recent_count = len(result['recent_users'])
            available_count = len(result['available_users'])
            logger.info(f'get_recent_and_available_users: Found {recent_count} recent users and {available_count} available users for {sender_username}')

            emit('recent_and_available_users', {
                'recent_users': result['recent_users'],
                'available_users': result['available_users']
            }, room=request.sid)

        except Exception as e:
            logger.error(f'get_recent_and_available_users error: Failed to fetch users for {sender_username}: {str(e)}')
            emit('error', {'message': 'Failed to fetch users'})

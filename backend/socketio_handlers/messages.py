"""
Message handling WebSocket handlers
Handles sending and receiving encrypted messages
"""

from flask import request
from flask_socketio import emit
from datetime import datetime, timezone
from database import db
from models import Message, Room
from .connection import connected_users


def register_message_handlers(socketio):
    """Register message-related WebSocket handlers"""

    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Send an encrypted message to a room

        Data should include:
        - room_id: int
        - encrypted_content: string (Base64 AES-encrypted)
        - iv: string (Base64 initialization vector)
        - tag: string (Base64 authentication tag)
        - key_version: int (which symmetric key version was used)
        """
        if request.sid not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return

        user_data = connected_users[request.sid]
        room_id = data.get('room_id')
        encrypted_content = data.get('encrypted_content')
        iv = data.get('iv')
        tag = data.get('tag')
        key_version = data.get('key_version')

        if not all([room_id, encrypted_content, iv, key_version]):
            emit('error', {'message': 'room_id, encrypted_content, iv, and key_version are required'})
            return

        try:
            room = db.session.get(Room, room_id)
            if not room:
                emit('error', {'message': 'Room not found'})
                return

            # Verify user is participant
            user_id = user_data['user_id']
            participant_ids = [p.id for p in room.participants]
            if user_id not in participant_ids:
                emit('error', {'message': 'Not a participant in this room'})
                return

            # Create message
            message = Message(
                room_id=room_id,
                sender_id=user_id,
                encrypted_content=encrypted_content,
                iv=iv,
                key_version=key_version,
                message_type='user'
            )
            db.session.add(message)
            db.session.commit()

            # Broadcast message to room
            message_data = {
                'message_id': message.id,
                'room_id': room_id,
                'sender_id': user_id,
                'sender_username': user_data['username'],
                'encrypted_content': encrypted_content,
                'iv': iv,
                'key_version': key_version,
                'message_type': 'user',
                'created_at': message.created_at.isoformat()
            }

            emit('new_message', message_data, room=f'room_{room_id}')

            print(f'Message sent by {user_data["username"]} in room {room_id}')

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to send message: {str(e)}'})

    @socketio.on('get_messages')
    def handle_get_messages(data):
        """
        Get message history for a room

        Data should include:
        - room_id: int
        - limit: int (optional, default 50)
        - offset: int (optional, default 0)
        """
        if request.sid not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return

        user_data = connected_users[request.sid]
        room_id = data.get('room_id')
        limit = data.get('limit', 50)
        offset = data.get('offset', 0)

        if not room_id:
            emit('error', {'message': 'room_id is required'})
            return

        try:
            room = db.session.get(Room, room_id)
            if not room:
                emit('error', {'message': 'Room not found'})
                return

            # Verify user is participant
            user_id = user_data['user_id']
            participant_ids = [p.id for p in room.participants]
            if user_id not in participant_ids:
                emit('error', {'message': 'Not a participant in this room'})
                return

            # Get messages (ordered by timestamp, most recent first)
            messages = Message.query.filter_by(room_id=room_id)\
                .order_by(Message.timestamp.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()

            # Format message data
            message_list = []
            for msg in reversed(messages):  # Reverse to get chronological order
                message_data = {
                    'message_id': msg.id,
                    'room_id': room_id,
                    'sender_id': msg.sender_id,
                    'encrypted_content': msg.encrypted_content,
                    'iv': msg.iv,
                    'tag': msg.tag,
                    'key_version': msg.key_version,
                    'message_type': msg.message_type,
                    'timestamp': msg.timestamp.isoformat()
                }

                # Add sender username if not system message
                if msg.sender_id:
                    sender = db.session.get(db.Model, msg.sender_id)
                    if sender:
                        message_data['sender_username'] = sender.username

                message_list.append(message_data)

            emit('messages_history', {
                'room_id': room_id,
                'messages': message_list,
                'count': len(message_list),
                'offset': offset,
                'has_more': len(messages) == limit
            })

        except Exception as e:
            emit('error', {'message': f'Failed to get messages: {str(e)}'})

"""
WebSocket connection handlers
Handles connect and disconnect events
"""

from flask import request
from flask_socketio import emit, disconnect
from flask_jwt_extended import decode_token
from database import db
from models import User, Room, SymmetricKey

# Store connected users {session_id: {'username': str, 'user_id': int}}
connected_users = {}


def verify_socket_token(token):
    """Verify JWT token for WebSocket connection"""
    try:
        # Decode and verify token
        decoded = decode_token(token)
        user_id = int(decoded['sub'])

        # Check if user exists
        user = db.session.get(User, user_id)
        if not user:
            return None, "User not found"

        return {
            'user_id': user_id,
            'username': user.username
        }, None
    except Exception as e:
        return None, f"Invalid token: {str(e)}"


def register_connection_handlers(socketio):
    """Register connection-related WebSocket handlers"""

    @socketio.on('connect')
    def handle_connect(auth):
        """
        Handle WebSocket connection with JWT authentication
        Client must send: { "token": "Bearer <access_token>" } in auth parameter
        """
        if not auth or 'token' not in auth:
            print(f'Connection rejected: No token provided')
            disconnect()
            return False

        # Extract token (remove "Bearer " prefix if present)
        token = auth['token']
        if token.startswith('Bearer '):
            token = token[7:]

        # Verify token
        user_data, error = verify_socket_token(token)
        if error:
            print(f'Connection rejected: {error}')
            disconnect()
            return False

        # Get full user object for complete info
        user = db.session.get(User, user_data['user_id'])
        
        # Get all rooms user participates in
        rooms = Room.query.filter(Room.participants.contains(user)).all()
        rooms_data = []
        
        for room in rooms:
            # Get public keys of all participants in this room
            participants_data = []
            for participant in room.participants:
                participants_data.append({
                    'user_id': participant.id,
                    'username': participant.username,
                    'public_key': participant.public_key
                })

            # Get all encrypted symmetric key versions for this user in this room
            symmetric_keys = SymmetricKey.query.filter_by(
                room_id=room.id,
                user_id=user.id
            ).order_by(SymmetricKey.key_version.asc()).all()

            encrypted_keys = {
                key.key_version: key.encrypted_key
                for key in symmetric_keys
            }

            rooms_data.append({
                'room': room.to_dict(include_participants=False),
                'participants': participants_data,
                'encrypted_symmetric_keys': encrypted_keys
            })

        # Store user data
        connected_users[request.sid] = user_data
        print(f'User {user_data["username"]} connected: {request.sid}')

        emit('connected', {
            'message': 'Successfully connected',
            'user': user.to_dict(),
            'rooms': rooms_data
        })
        # After sending connected payload, inform the user about any rooms
        # that have pending key rotation so they (as a connected participant)
        # can initiate the rotation. We send `rotation_required` per room.
        for room in rooms:
            if getattr(room, 'rotation_pending', False):
                emit('rotation_required', {
                    'room_id': room.id,
                    'reason': 'pending_from_leave',
                })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        if request.sid in connected_users:
            user_data = connected_users[request.sid]
            print(f'User {user_data["username"]} disconnected: {request.sid}')
            del connected_users[request.sid]
        else:
            print(f'Unknown user disconnected: {request.sid}')

from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import JWTManager, decode_token, verify_jwt_in_request
from config import Config
from database import db
from models import User, Room, Message, SymmetricKey, UserDevice
from datetime import datetime, timezone
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize JWT
jwt = JWTManager(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Register blueprints
from api.auth import auth_bp
app.register_blueprint(auth_bp)

# Store connected users {session_id: {'username': str, 'user_id': int, 'device_id': int}}
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

        # Get user's most recent device (for now, just get first device)
        device = UserDevice.query.filter_by(user_id=user_id).first()
        if not device:
            return None, "No device found for user"

        return {
            'user_id': user_id,
            'username': user.username,
            'device_id': device.id
        }, None
    except Exception as e:
        return None, f"Invalid token: {str(e)}"


def create_system_message(room_id, content, key_version=None):
    """
    Create a system/informational message (e.g., user joined/left).
    Content should be a plain text that will be encrypted by participants.

    Note: In production, system messages should be encrypted server-side
    or signed to prevent tampering. For now, we store plain content.
    """
    import base64
    room = db.session.get(Room, room_id)
    if not room:
        return None

    # Use current key version if not specified
    if key_version is None:
        key_version = room.current_key_version

    # For system messages, we store the content as base64 encoded plain text
    # Client will recognize message_type='system' and won't try to decrypt
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    fake_iv = base64.b64encode(b'0' * 16).decode('utf-8')  # Dummy IV for system messages

    message = Message(
        room_id=room_id,
        sender_id=None,  # System message has no sender
        message_type='system',
        encrypted_content=encoded_content,
        iv=fake_iv,
        key_version=key_version
    )
    db.session.add(message)
    db.session.commit()

    return message


# Simple REST API health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Post-Quantum Cryptography WebSocket Server',
        'connected_users': len(connected_users)
    })

# WebSocket Events
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

    # Store user info
    connected_users[request.sid] = user_data

    print(f'Client connected: {user_data["username"]} (user_id={user_data["user_id"]}, device_id={user_data["device_id"]})')

    # Auto-join user to all their rooms
    user_rooms = Room.query.join(Room.participants).filter(User.id == user_data['user_id']).all()
    for room in user_rooms:
        join_room(f'room_{room.id}')
        print(f'User {user_data["username"]} auto-joined room {room.id}')

    # Send welcome message
    emit('connected', {
        'message': 'Successfully connected to WebSocket',
        'username': user_data['username'],
        'user_id': user_data['user_id'],
        'device_id': user_data['device_id']
    })

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        user_data = connected_users[request.sid]
        username = user_data['username']
        del connected_users[request.sid]
        print(f'Client disconnected: {username}')
        # Notify all users about disconnection
        emit('user_disconnected', {'username': username}, broadcast=True)
    else:
        print(f'Client disconnected: {request.sid}')


# ===== ROOM MANAGEMENT EVENTS =====

@socketio.on('create_room')
def handle_create_room(data):
    """
    Create a new chat room with E2E encryption setup

    Client should:
    1. Generate random AES-256 symmetric key
    2. Encrypt it with each participant's device ML-KEM public key
    3. Send encrypted_keys array with room creation request
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    user_id = user_data['user_id']

    room_name = data.get('name')
    participant_ids = data.get('participant_ids', [])  # List of user IDs to invite
    is_group = data.get('is_group', len(participant_ids) > 1)
    encrypted_keys = data.get('encrypted_keys', [])  # [{user_id, device_id, encrypted_key}]

    try:
        # Create room
        room = Room(name=room_name, is_group=is_group)
        db.session.add(room)

        # Add creator as participant
        creator = db.session.get(User, user_id)
        room.participants.append(creator)

        # Add other participants
        for participant_id in participant_ids:
            if participant_id != user_id:  # Don't add creator twice
                participant = db.session.get(User, participant_id)
                if participant:
                    room.participants.append(participant)

        db.session.commit()

        # Store encrypted symmetric keys for all participants (version 1)
        if encrypted_keys:
            for key_data in encrypted_keys:
                target_user_id = key_data.get('user_id')
                target_device_id = key_data.get('device_id')
                encrypted_key = key_data.get('encrypted_key')

                if not all([target_user_id, target_device_id, encrypted_key]):
                    continue

                # Verify user is participant
                if target_user_id not in [p.id for p in room.participants]:
                    continue

                sym_key = SymmetricKey(
                    room_id=room.id,
                    user_id=target_user_id,
                    device_id=target_device_id,
                    key_version=1,  # Initial key version
                    encrypted_key=encrypted_key
                )
                db.session.add(sym_key)

            db.session.commit()

        # Join socket.io room
        join_room(f'room_{room.id}')

        # Send response to creator
        room_data = {
            'room': room.to_dict(include_participants=True),
            'created_by': user_data['username'],
            'encryption_setup': len(encrypted_keys) > 0
        }
        emit('room_created', room_data)

        # Notify other participants (if any)
        if len(room.participants) > 1:
            emit('room_created', room_data, room=f'room_{room.id}', include_self=False)

        print(f'Room {room.id} created by {user_data["username"]} with {len(encrypted_keys)} encrypted keys')

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f'Failed to create room: {str(e)}'})


@socketio.on('invite_to_room')
def handle_invite_to_room(data):
    """
    Invite users to an existing room (only participants can invite).
    IMPORTANT: This triggers key rotation for forward/backward secrecy.
    All current participants must receive new encrypted keys with incremented key_version.
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')
    invited_user_ids = data.get('invited_user_ids', [])
    new_encrypted_keys = data.get('new_encrypted_keys', [])  # New keys for ALL participants (current + invited)

    if not room_id or not invited_user_ids:
        emit('error', {'message': 'room_id and invited_user_ids are required'})
        return

    if not new_encrypted_keys:
        emit('error', {'message': 'new_encrypted_keys is required for all participants (forward secrecy)'})
        return

    try:
        room = db.session.get(Room, room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        inviter = db.session.get(User, user_data['user_id'])

        # Security check: only participants can invite others
        if inviter not in room.participants:
            emit('error', {'message': 'Only participants can invite others to the room'})
            return

        # Add invited users to room
        invited_users = []
        for user_id in invited_user_ids:
            user = db.session.get(User, user_id)
            if user and user not in room.participants:
                room.participants.append(user)
                invited_users.append(user)

        if not invited_users:
            emit('error', {'message': 'No new users were added'})
            return

        # Increment key version (new symmetric key generation)
        room.current_key_version += 1
        new_version = room.current_key_version

        # Revoke old keys (mark as revoked)
        old_keys = SymmetricKey.query.filter_by(
            room_id=room_id,
            key_version=new_version - 1
        ).all()
        for old_key in old_keys:
            old_key.revoked_at = datetime.now(timezone.utc)

        # Store new encrypted symmetric keys for ALL participants (current + invited)
        for key_data in new_encrypted_keys:
            symmetric_key = SymmetricKey(
                room_id=room_id,
                user_id=key_data['user_id'],
                device_id=key_data['device_id'],
                key_version=new_version,
                encrypted_key=key_data['encrypted_key']
            )
            db.session.add(symmetric_key)

        db.session.commit()

        emit('users_invited', {
            'room_id': room.id,
            'invited_users': [{'id': u.id, 'username': u.username} for u in invited_users],
            'new_key_version': new_version
        })

        # Notify all participants about key rotation
        emit('key_rotated', {
            'room_id': room.id,
            'new_key_version': new_version,
            'reason': 'new_participants'
        }, room=f'room_{room.id}')

        # Notify about new members
        for user in invited_users:
            emit('user_joined_room', {
                'room_id': room.id,
                'user_id': user.id,
                'username': user.username
            }, room=f'room_{room.id}')

            # Create system message about user joining
            create_system_message(
                room_id=room_id,
                content=f"{user.username} joined the room",
                key_version=new_version
            )

        print(f'User {user_data["username"]} invited {len(invited_users)} users to room {room.id}, key rotated to v{new_version}')

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f'Failed to invite users: {str(e)}'})


@socketio.on('leave_room')
def handle_leave_room(data):
    """
    Leave a room.
    After leaving, remaining participants should call rotate_room_key for forward secrecy.
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')

    if not room_id:
        emit('error', {'message': 'room_id is required'})
        return

    try:
        room = db.session.get(Room, room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        user = db.session.get(User, user_data['user_id'])

        if user in room.participants:
            room.participants.remove(user)
            db.session.commit()

        # Leave socket.io room
        leave_room(f'room_{room.id}')

        emit('room_left', {'room_id': room.id})

        # Create system message about user leaving (using current key version)
        create_system_message(
            room_id=room_id,
            content=f"{user.username} left the room",
            key_version=room.current_key_version
        )

        # Notify other participants - they should rotate keys for forward secrecy
        emit('user_left_room', {
            'room_id': room.id,
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'requires_key_rotation': True  # Signal that key rotation is recommended
        }, room=f'room_{room.id}')

        print(f'User {user_data["username"]} left room {room.id}')

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f'Failed to leave room: {str(e)}'})


@socketio.on('rotate_room_key')
def handle_rotate_room_key(data):
    """
    Rotate symmetric key for a room (forward secrecy).
    This should be called by remaining participants after someone leaves.
    Can also be called by the first participant to connect if key rotation is pending.

    IMPORTANT: Only current participants can rotate keys.
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')
    new_encrypted_keys = data.get('new_encrypted_keys', [])  # New keys for ALL current participants

    if not room_id:
        emit('error', {'message': 'room_id is required'})
        return

    if not new_encrypted_keys:
        emit('error', {'message': 'new_encrypted_keys is required for all current participants'})
        return

    try:
        room = db.session.get(Room, room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        user = db.session.get(User, user_data['user_id'])

        # Security check: only participants can rotate keys
        if user not in room.participants:
            emit('error', {'message': 'Only participants can rotate room keys'})
            return

        if len(room.participants) == 0:
            emit('error', {'message': 'Cannot rotate keys in empty room'})
            return

        # Verify all current participants have new keys
        participant_ids = {p.id for p in room.participants}
        provided_user_ids = {k['user_id'] for k in new_encrypted_keys}

        if participant_ids != provided_user_ids:
            emit('error', {'message': 'Must provide keys for ALL current participants'})
            return

        # Increment key version
        room.current_key_version += 1
        new_version = room.current_key_version

        # Revoke old keys
        old_keys = SymmetricKey.query.filter_by(
            room_id=room_id,
            key_version=new_version - 1
        ).all()
        for old_key in old_keys:
            old_key.revoked_at = datetime.now(timezone.utc)

        # Store new encrypted symmetric keys for all current participants
        for key_data in new_encrypted_keys:
            symmetric_key = SymmetricKey(
                room_id=room_id,
                user_id=key_data['user_id'],
                device_id=key_data['device_id'],
                key_version=new_version,
                encrypted_key=key_data['encrypted_key']
            )
            db.session.add(symmetric_key)

        db.session.commit()

        # Notify all participants about key rotation
        emit('key_rotated', {
            'room_id': room.id,
            'new_key_version': new_version,
            'reason': 'manual_rotation',
            'rotated_by': user_data['username']
        }, room=f'room_{room.id}', include_self=True)

        print(f'Room {room.id} key rotated to v{new_version} by {user_data["username"]}')

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f'Failed to rotate key: {str(e)}'})





@socketio.on('get_room_messages')
def handle_get_room_messages(data):
    """
    Get message history for a room.
    Returns all encrypted symmetric key versions for this user/device to decrypt messages.
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')
    limit = data.get('limit', 50)  # Default 50 messages
    offset = data.get('offset', 0)

    if not room_id:
        emit('error', {'message': 'room_id is required'})
        return

    try:
        room = db.session.get(Room, room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        user = db.session.get(User, user_data['user_id'])

        # Check if user is a participant
        if user not in room.participants:
            emit('error', {'message': 'Not a participant of this room'})
            return

        # Get messages
        messages = Message.query.filter_by(room_id=room_id)\
            .order_by(Message.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()

        # Get ALL encrypted symmetric key versions for this user/device
        # User needs all versions to decrypt old messages encrypted with previous keys
        symmetric_keys = SymmetricKey.query.filter_by(
            room_id=room_id,
            user_id=user_data['user_id'],
            device_id=user_data['device_id']
        ).order_by(SymmetricKey.key_version.asc()).all()

        # Build key version map for client
        key_versions = {
            key.key_version: key.encrypted_key
            for key in symmetric_keys
        }

        return {
            'room_id': room_id,
            'messages': [msg.to_dict() for msg in reversed(messages)],
            'encrypted_symmetric_keys': key_versions,  # Map of version -> encrypted_key
            'current_key_version': room.current_key_version,
            'has_more': len(messages) == limit
        }

    except Exception as e:
        emit('error', {'message': f'Failed to get messages: {str(e)}'})


@socketio.on('get_rooms')
def handle_get_rooms(data):
    """Get all rooms for the current user"""
    if request.sid not in connected_users:
        return {'error': 'Not authenticated'}

    user_data = connected_users[request.sid]

    try:
        rooms = Room.query.join(Room.participants).filter(User.id == user_data['user_id']).all()

        return {
            'rooms': [room.to_dict(include_participants=True) for room in rooms]
        }

    except Exception as e:
        return {'error': f'Failed to get rooms: {str(e)}'}


# ===== KEY EXCHANGE EVENTS =====

@socketio.on('exchange_key')
def handle_exchange_key(data):
    """
    Exchange encrypted symmetric key with room participants
    Client sends encrypted symmetric key for each participant's device
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')
    encrypted_keys = data.get('encrypted_keys', [])  # List of {user_id, device_id, encrypted_key}

    if not room_id:
        emit('error', {'message': 'room_id is required'})
        return

    try:
        room = db.session.get(Room, room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        user = db.session.get(User, user_data['user_id'])

        # Check if user is a participant
        if user not in room.participants:
            emit('error', {'message': 'Not a participant of this room'})
            return

        # Store encrypted keys for each participant's device (current key version)
        current_version = room.current_key_version

        for key_data in encrypted_keys:
            target_user_id = key_data.get('user_id')
            target_device_id = key_data.get('device_id')
            encrypted_key = key_data.get('encrypted_key')
            key_version = key_data.get('key_version', current_version)  # Use provided version or current

            if not all([target_user_id, target_device_id, encrypted_key]):
                continue

            # Check if key already exists for this version
            existing_key = SymmetricKey.query.filter_by(
                room_id=room_id,
                user_id=target_user_id,
                device_id=target_device_id,
                key_version=key_version
            ).first()

            if existing_key:
                # Update existing key
                existing_key.encrypted_key = encrypted_key
            else:
                # Create new key entry
                sym_key = SymmetricKey(
                    room_id=room_id,
                    user_id=target_user_id,
                    device_id=target_device_id,
                    key_version=key_version,
                    encrypted_key=encrypted_key
                )
                db.session.add(sym_key)

        db.session.commit()

        # Send confirmation to sender
        key_data = {
            'room_id': room_id,
            'key_version': current_version,
            'from_user_id': user_data['user_id'],
            'from_username': user_data['username']
        }
        emit('key_exchanged', key_data)

        # Notify other room participants about key exchange
        emit('key_exchanged', key_data, room=f'room_{room_id}', include_self=False)

        print(f'Keys exchanged by {user_data["username"]} in room {room_id} (version {current_version})')

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f'Failed to exchange keys: {str(e)}'})


@socketio.on('get_room_keys')
def handle_get_room_keys(data):
    """Get all participants' public keys for a room (for key exchange)"""
    if request.sid not in connected_users:
        return {'error': 'Not authenticated'}

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')

    if not room_id:
        return {'error': 'room_id is required'}

    try:
        room = db.session.get(Room, room_id)
        if not room:
            return {'error': 'Room not found'}

        user = db.session.get(User, user_data['user_id'])

        # Check if user is a participant
        if user not in room.participants:
            return {'error': 'Not a participant of this room'}

        # Get all devices for all participants
        participant_keys = []
        for participant in room.participants:
            devices = UserDevice.query.filter_by(user_id=participant.id).all()
            for device in devices:
                participant_keys.append({
                    'user_id': participant.id,
                    'username': participant.username,
                    'device_id': device.id,
                    'device_name': device.device_name,
                    'public_key': device.public_key
                })

        return {
            'room_id': room_id,
            'participant_keys': participant_keys
        }

    except Exception as e:
        return {'error': f'Failed to get room keys: {str(e)}'}


# ===== ENCRYPTED MESSAGING =====

@socketio.on('send_message')
def handle_send_message(data):
    """
    Send encrypted message to a room.
    Client sends AES-encrypted message with IV and current key_version.
    """
    if request.sid not in connected_users:
        emit('error', {'message': 'Not authenticated'})
        return

    user_data = connected_users[request.sid]
    room_id = data.get('room_id')
    encrypted_content = data.get('encrypted_content')
    iv = data.get('iv')
    key_version = data.get('key_version')  # Client must specify which key version was used

    if not all([room_id, encrypted_content, iv]):
        emit('error', {'message': 'room_id, encrypted_content, and iv are required'})
        return

    try:
        room = db.session.get(Room, room_id)
        if not room:
            emit('error', {'message': 'Room not found'})
            return

        user = db.session.get(User, user_data['user_id'])

        # Check if user is a participant
        if user not in room.participants:
            emit('error', {'message': 'Not a participant of this room'})
            return

        # If key_version not provided, use current room key version
        if key_version is None:
            key_version = room.current_key_version

        # Save message to database
        message = Message(
            room_id=room_id,
            sender_id=user_data['user_id'],
            encrypted_content=encrypted_content,
            iv=iv,
            key_version=key_version
        )
        db.session.add(message)
        db.session.commit()

        # Send to sender (echo)
        message_payload = message.to_dict()
        emit('new_message', message_payload)

        # Broadcast to other room participants
        emit('new_message', message_payload, room=f'room_{room_id}', include_self=False)

        print(f'Encrypted message sent by {user_data["username"]} to room {room_id}')

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f'Failed to send message: {str(e)}'})

if __name__ == '__main__':
    # Create database tables only when running directly
    with app.app_context():
        db.create_all()

    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False') == 'True'
    )

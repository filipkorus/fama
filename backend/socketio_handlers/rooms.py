"""
Room management WebSocket handlers
Handles room creation, joining, inviting, and leaving
"""

from flask import request
from flask_socketio import emit, join_room, leave_room as socketio_leave_room
from datetime import datetime, timezone
from database import db
from models import User, Room, SymmetricKey
from .connection import connected_users
import base64


def create_system_message(room_id, content, key_version=None):
    """
    Create a system/informational message (e.g., user joined/left).
    Content should be a plain text that will be encrypted by participants.

    Note: In production, system messages should be encrypted server-side
    or signed to prevent tampering. For now, we store plain content.
    """
    from models import Message

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


def register_room_handlers(socketio):
    """Register room-related WebSocket handlers"""

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
        encrypted_keys = data.get('encrypted_keys', [])  # [{user_id, encrypted_key}]

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
                    encrypted_key = key_data.get('encrypted_key')

                    if not all([target_user_id, encrypted_key]):
                        continue

                    # Verify user is participant
                    if target_user_id not in [p.id for p in room.participants]:
                        continue

                    sym_key = SymmetricKey(
                        room_id=room.id,
                        user_id=target_user_id,
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

        try:
            room = db.session.get(Room, room_id)
            if not room:
                emit('error', {'message': 'Room not found'})
                return

            user = db.session.get(User, user_data['user_id'])

            # Security check: only participants can invite
            if user not in room.participants:
                emit('error', {'message': 'Only participants can invite to room'})
                return

            # Add invited users
            newly_added = []
            for invited_id in invited_user_ids:
                invited_user = db.session.get(User, invited_id)
                if invited_user and invited_user not in room.participants:
                    room.participants.append(invited_user)
                    newly_added.append(invited_user)

            if not newly_added:
                emit('error', {'message': 'No new users were added'})
                return

            # Increment key version for key rotation
            room.current_key_version += 1
            new_version = room.current_key_version

            # Revoke old keys
            old_keys = SymmetricKey.query.filter_by(
                room_id=room_id,
                key_version=new_version - 1
            ).all()
            for old_key in old_keys:
                old_key.revoked_at = datetime.now(timezone.utc)

            # Store new encrypted symmetric keys
            if new_encrypted_keys:
                for key_data in new_encrypted_keys:
                    target_user_id = key_data.get('user_id')
                    encrypted_key = key_data.get('encrypted_key')

                    if not all([target_user_id, encrypted_key]):
                        continue

                    # Verify user is participant
                    if target_user_id not in [p.id for p in room.participants]:
                        continue

                    sym_key = SymmetricKey(
                        room_id=room.id,
                        user_id=target_user_id,
                        key_version=new_version,
                        encrypted_key=encrypted_key
                    )
                    db.session.add(sym_key)

            db.session.commit()

            # Create system message
            invited_names = ', '.join([u.username for u in newly_added])
            create_system_message(
                room_id,
                f'{invited_names} joined the room',
                key_version=new_version
            )

            # Notify all participants about new members and key rotation
            notification = {
                'room_id': room.id,
                'invited_users': [u.to_dict() for u in newly_added],
                'invited_by': user_data['username'],
                'new_key_version': new_version
            }

            emit('users_invited', notification, room=f'room_{room.id}')

            # Additionally notify invited users individually (if they are connected)
            for invited_user in newly_added:
                # Find encrypted key for this invited user (if provided)
                invited_key = None
                if new_encrypted_keys:
                    invited_key = next(
                        (k.get('encrypted_key') for k in new_encrypted_keys if k.get('user_id') == invited_user.id),
                        None
                    )

                # Emit a targeted event to all connected sessions of the invited user
                for sid, conn_user in connected_users.items():
                    if conn_user['user_id'] == invited_user.id:
                        emit('invited_to_room', {
                            'room': room.to_dict(include_participants=True),
                            'invited_by': user_data['username'],
                            'encrypted_key': invited_key,
                            'new_key_version': new_version
                        }, room=sid)

            print(f'Users invited to room {room.id}, key rotated to v{new_version}')

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to invite users: {str(e)}'})

    @socketio.on('join_room')
    def handle_join_room(data):
        """Join an existing room (must be a participant)"""
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

            # Check if user is participant
            if user not in room.participants:
                emit('error', {'message': 'Not a participant in this room'})
                return

            # Join socket.io room
            join_room(f'room_{room.id}')

            # Send room info to user
            emit('room_joined', {
                'room': room.to_dict(include_participants=True)
            })

            # Notify others
            emit('user_joined', {
                'room_id': room.id,
                'user': user.to_dict()
            }, room=f'room_{room.id}', include_self=False)

            print(f'User {user_data["username"]} joined room {room.id}')

        except Exception as e:
            emit('error', {'message': f'Failed to join room: {str(e)}'})

    @socketio.on('leave_room')
    def handle_leave_room(data):
        """
        Leave a room (triggers key rotation for forward secrecy).
        Remaining participants must generate new keys.
        """
        if request.sid not in connected_users:
            emit('error', {'message': 'Not authenticated'})
            return

        user_data = connected_users[request.sid]
        room_id = data.get('room_id')
        new_encrypted_keys = data.get('new_encrypted_keys', [])  # New keys for remaining participants

        if not room_id:
            emit('error', {'message': 'room_id is required'})
            return

        try:
            room = db.session.get(Room, room_id)
            if not room:
                emit('error', {'message': 'Room not found'})
                return

            user = db.session.get(User, user_data['user_id'])

            # Check if user is participant
            if user not in room.participants:
                emit('error', {'message': 'Not a participant in this room'})
                return

            # Remove user from participants
            room.participants.remove(user)

            # If room is now empty, delete it
            if len(room.participants) == 0:
                db.session.delete(room)
                db.session.commit()

                socketio_leave_room(f'room_{room.id}')
                emit('room_deleted', {'room_id': room.id})
                print(f'Room {room.id} deleted (no participants left)')
                return

            # Remove leaving user's keys immediately
            SymmetricKey.query.filter_by(
                room_id=room_id,
                user_id=user.id
            ).delete()

            # Mark room as requiring key rotation. Actual rotation should be
            # performed by a remaining participant (first connected or the
            # first one who connects later). This preserves the server from
            # performing rotation on behalf of clients.
            room.rotation_pending = True
            db.session.commit()

            # Create system message (note: key_version not incremented yet)
            create_system_message(
                room_id,
                f'{user_data["username"]} left the room',
                key_version=room.current_key_version
            )

            # Leave socket.io room
            socketio_leave_room(f'room_{room.id}')

            # Notify remaining participants that a user left (rotation required)
            emit('user_left', {
                'room_id': room.id,
                'user_id': user.id,
                'username': user_data['username'],
                'rotation_required': True
            }, room=f'room_{room.id}')

            # Attempt to notify one currently connected participant individually
            # so they can perform the rotation. If none are connected, the
            # `rotation_pending` flag ensures the first participant who connects
            # will be informed by the connect handler.
            notified = False
            for sid, conn_user in connected_users.items():
                if conn_user['user_id'] in [p.id for p in room.participants]:
                    emit('rotation_required', {
                        'room_id': room.id,
                        'reason': 'user_left',
                        'left_user': {'id': user.id, 'username': user.username}
                    }, room=sid)
                    notified = True
                    break

            emit('room_left', {'room_id': room.id})

            if notified:
                print(f'User {user_data["username"]} left room {room.id}, rotation requested from a connected participant')
            else:
                print(f'User {user_data["username"]} left room {room.id}, rotation pending for first connecting participant')

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to leave room: {str(e)}'})

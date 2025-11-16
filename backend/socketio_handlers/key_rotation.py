"""
Key rotation WebSocket handlers and utilities
Handles symmetric key rotation for rooms
"""

from flask import request
from flask_socketio import emit
from datetime import datetime, timezone
from database import db
from models import Room, SymmetricKey, User
from .connection import connected_users


def rotate_room_keys_for_user(user_id):
    """
    Helper function to rotate keys for all rooms when needed.
    Returns list of room IDs that were rotated.
    
    NOTE: This function does NOT store the new encrypted keys.
    The calling code must handle key distribution.
    
    Args:
        user_id: ID of the user
    """
    user = db.session.get(User, user_id)
    if not user:
        return []
    
    # Get all rooms user participates in
    user_rooms = Room.query.filter(Room.participants.contains(user)).all()
    
    rotated_rooms = []
    for room in user_rooms:
        # Increment key version
        room.current_key_version += 1
        new_version = room.current_key_version
        
        # Revoke old keys
        old_keys = SymmetricKey.query.filter_by(
            room_id=room.id,
            key_version=new_version - 1
        ).all()
        for old_key in old_keys:
            old_key.revoked_at = datetime.now(timezone.utc)
        
        rotated_rooms.append(room.id)
    
    return rotated_rooms


def register_key_rotation_handlers(socketio):
    """Register key rotation-related WebSocket handlers"""
    
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

            # Clear pending flag since rotation is being performed
            if getattr(room, 'rotation_pending', False):
                room.rotation_pending = False

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
                    key_version=new_version,
                    encrypted_key=key_data['encrypted_key']
                )
                db.session.add(symmetric_key)

            db.session.commit()

            # Notify all participants about key rotation
            # Include encrypted key for each participant
            for participant in room.participants:
                # Find encrypted key for this participant's device
                participant_key = next(
                    (k for k in new_encrypted_keys
                     if k['user_id'] == participant.id),
                    None
                )

                # Send to specific user's session(s)
                for sid, conn_user in connected_users.items():
                    if conn_user['user_id'] == participant.id:
                        emit('key_rotated', {
                            'room_id': room.id,
                            'new_key_version': new_version,
                            'reason': 'manual_rotation',
                            'rotated_by': user_data['username'],
                            'encrypted_key': participant_key['encrypted_key'] if participant_key else None
                        }, room=sid)

            print(f'Room {room.id} key rotated to v{new_version} by {user_data["username"]}')

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'Failed to rotate key: {str(e)}'})

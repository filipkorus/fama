"""
WebSocket connection handlers
Handles connect and disconnect events
"""

from flask import request
from flask_socketio import emit, disconnect
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from logging import getLogger

from ..database import db
from ..models import User
from .connected_users_manager import SocketIOConnectedUsersManager

sio_conn_users = SocketIOConnectedUsersManager()

logger = getLogger()

def verify_socket_token(token):
    """
    Verify JWT token sent during WebSocket connection
    Returns user data if valid, else None and error message.
    """
    try:
        decoded = decode_token(token)

        if decoded.get('type') != 'access':
            return None, "Invalid token type: expected access token"

        user_id = decoded['sub']
        user = db.session.get(User, int(user_id))

        if not user:
            return None, "User not found"

        if not user.is_active:
            return None, "User account is disabled"

        return {
            'user_id': user.id,
            'username': user.username
        }, None

    except JWTExtendedException:
         return None, "Invalid token format"

    except Exception as e:
        error_msg = str(e)

        if "Invalid or expired token" in error_msg or "Signature has expired" in error_msg:
            logger.warning(f"JWT Validation Failed: {error_msg}")
            return None, "Invalid or expired token"

        logger.error(f"CRITICAL WebSocket Auth Error: {type(e)} - {error_msg}")
        return None, "Authentication failed due to internal error"


def register_connection_handlers(socketio):
    """Register connection-related WebSocket handlers"""

    @socketio.on('connect')
    def handle_connect(auth):
        """
        Handle WebSocket connection with JWT authentication
        Client must send: { "token": "Bearer <access_token>" } in auth parameter
        """
        if not auth or 'token' not in auth:
            logger.warning('Connection rejected: No token provided')
            disconnect()
            return False

        token = auth['token']
        if token.startswith('Bearer '):
            token = token[7:]

        user_data, error = verify_socket_token(token)
        if error:
            logger.warning(f'Connection rejected: {error}')
            disconnect()
            return False

        sio_conn_users.add_user(sid=request.sid, user_id=user_data['user_id'])
        logger.info(f'User {user_data["username"]} connected: {request.sid}')

        emit('connected', {
            'message': 'Successfully connected',
            'user': {
                'id': user_data['user_id'],
                'username': user_data['username']
            }
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        sio_conn_users.remove_user(request.sid)
        logger.info(f'User disconnected: {request.sid}')

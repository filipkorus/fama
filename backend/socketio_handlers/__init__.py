"""
WebSocket handlers module
Contains all Socket.IO event handlers organized by functionality
"""

from .connection import register_connection_handlers
from .rooms import register_room_handlers
from .messages import register_message_handlers
from .key_rotation import register_key_rotation_handlers

__all__ = [
    'register_connection_handlers',
    'register_room_handlers',
    'register_message_handlers',
    'register_key_rotation_handlers'
]


def register_all_handlers(socketio):
    """Register all WebSocket handlers"""
    register_connection_handlers(socketio)
    register_room_handlers(socketio)
    register_message_handlers(socketio)
    register_key_rotation_handlers(socketio)

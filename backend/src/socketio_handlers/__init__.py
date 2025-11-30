"""
WebSocket handlers module
Contains all Socket.IO event handlers organized by functionality
"""

from .connection import register_connection_handlers
from .messages import register_message_handlers

__all__ = [
    'register_connection_handlers',
    'register_message_handlers'
]


def register_all_handlers(socketio):
    """Register all WebSocket handlers"""
    register_connection_handlers(socketio)
    register_message_handlers(socketio)

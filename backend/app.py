from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_jwt_extended import JWTManager
from config import Config
from database import db
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

# Store connected users {session_id: username}
connected_users = {}

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
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('message', 'Welcome to the server!')

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        username = connected_users[request.sid]
        del connected_users[request.sid]
        print(f'Client disconnected: {username}')
        # Notify all users about disconnection
        emit('user_disconnected', {'username': username}, broadcast=True)
    else:
        print(f'Client disconnected: {request.sid}')

@socketio.on('register')
def handle_register(data):
    """Register user with username"""
    username = data.get('username', f'User_{request.sid[:8]}')
    connected_users[request.sid] = username

    print(f'User registered: {username}')

    # Send confirmation to user
    emit('registered', {
        'username': username,
        'users_online': list(connected_users.values())
    })

    # Notify all other users
    emit('user_connected', {
        'username': username,
        'users_online': list(connected_users.values())
    }, broadcast=True, include_self=False)

@socketio.on('message')
def handle_message(data):
    """Handle incoming messages from clients"""
    message_text = data if isinstance(data, str) else data.get('message', '')
    target_user = data.get('to') if isinstance(data, dict) else None

    sender = connected_users.get(request.sid, f'User_{request.sid[:8]}')

    print(f'Message from {sender}: {message_text}')

    message_data = {
        'from': sender,
        'message': message_text,
        'timestamp': os.time.time() if hasattr(os, 'time') else None
    }

    if target_user:
        # Private message - send only to target user
        target_sid = None
        for sid, username in connected_users.items():
            if username == target_user:
                target_sid = sid
                break

        if target_sid:
            message_data['type'] = 'private'
            emit('message', message_data, room=target_sid)
            # Echo back to sender
            emit('message', {**message_data, 'to': target_user})
            print(f'Private message sent from {sender} to {target_user}')
        else:
            emit('error', {'message': f'User {target_user} not found'})
    else:
        # Broadcast message to all users
        message_data['type'] = 'broadcast'
        emit('message', message_data, broadcast=True, include_self=False)
        # Echo back to sender
        emit('message', {**message_data, 'echo': True})

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

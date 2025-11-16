"""
Main application entry point
Initializes Flask, SocketIO, database, and registers all blueprints and handlers
"""

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from database import db
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app, origins=Config.CORS_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ORIGINS)

# Register REST API blueprints
from api import auth_bp, users_bp
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)

# Register WebSocket handlers
from socketio_handlers import register_all_handlers
register_all_handlers(socketio)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=Config.BACKEND_PORT, debug=Config.DEBUG)

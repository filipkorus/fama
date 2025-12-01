from flask import Flask, request
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
import logging

from .config import Config
from .database import db
from .api import auth_bp, users_bp, files_bp
from .socketio_handlers import register_all_handlers

logging.basicConfig(
    level=Config.LOGGER_LEVEL,
    format=Config.LOGGER_FORMAT,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app, origins=Config.CORS_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ORIGINS)

app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(files_bp)

@app.before_request
def log_request():
    logger.info(
        f"{request.remote_addr} {request.method} {request.path}"
    )

register_all_handlers(socketio)

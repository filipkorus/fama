from src.app import app, socketio
from src.config import Config

if __name__ == '__main__':
    print(f"Starting server on port {Config.BACKEND_PORT}")
    socketio.run(app, host='0.0.0.0', port=Config.BACKEND_PORT, debug=Config.DEBUG)

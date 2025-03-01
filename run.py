from app import create_app
from app.sockets import socketio
import os

app = create_app()

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    os.makedirs('.flask_session', exist_ok=True)
    
    # Run the Flask app
    socketio.run(app, debug=True) 
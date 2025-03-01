from flask import Flask
from flask_socketio import SocketIO
from flask_session import Session
from flask_dance.contrib.google import make_google_blueprint, google
from datetime import timedelta
import os
from dotenv import load_dotenv
from app.models import db

# Load environment variables
load_dotenv()

socketio = SocketIO(manage_session=False)

def create_app():
    app = Flask(__name__)
    
    # Config
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-12345')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
    app.config['SESSION_FILE_DIR'] = '.flask_session/'
    
    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trading.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Flask-Session
    Session(app)
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize SocketIO
    socketio.init_app(app)

    # Configure Google OAuth
    google_bp = make_google_blueprint(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scope=["profile", "email"],
        redirect_to="main.google_login"
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    # Create database tables
    with app.app_context():
        db.create_all()

    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)

    # Add context processor for google
    @app.context_processor
    def inject_google():
        return dict(google=google)

    return app 
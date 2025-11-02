import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

db = SQLAlchemy()

def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///scootgo.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()

    with app.app_context():
        from .auth import auth_bp
        from .scooters import scooters_bp
        from .trips import trips_bp
        from .main import main_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(scooters_bp)
        app.register_blueprint(trips_bp)
        app.register_blueprint(main_bp)

    return app

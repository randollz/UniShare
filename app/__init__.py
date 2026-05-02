import sys
import os

from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# Allow importing database.py and validators.py from the project root.
# This shim is removed once the ORM layer replaces raw SQL (feature/orm-routes).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import Config
from app.extensions import db, migrate, login_manager


def create_app(config_class=Config):
    application = Flask(__name__)
    application.config.from_object(config_class)

    # Initialise extensions
    db.init_app(application)
    migrate.init_app(application, db)
    login_manager.init_app(application)

    # Register models so Alembic can detect them
    from app import models  # noqa: F401

    # User loader required by Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register all HTTP routes
    from app import routes
    routes.register_routes(application)

    return application

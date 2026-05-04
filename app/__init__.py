import sys
import os

from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# Allow importing database.py and validators.py from the project root
# (will be removed once the ORM layer replaces raw SQL in feature/orm-models)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import Config


def create_app(config_class=Config):
    application = Flask(__name__)
    application.config.from_object(config_class)

    from app import routes
    routes.register_routes(application)

    return application

from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

from app.config import Config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_class=Config):
    application = Flask(__name__)
    application.config.from_object(config_class)

    # Initialise extensions
    db.init_app(application)
    migrate.init_app(application, db)
    login_manager.init_app(application)
    csrf.init_app(application)

    # Register models so Alembic can detect them
    from app import models  # noqa: F401

    # User loader required by Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Context processor
    from flask_login import current_user
    from app.models import Message

    @application.context_processor
    def inject_globals():
        unread = 0
        if current_user.is_authenticated:
            unread = Message.query.filter_by(
                receiver_id=current_user.id, read=0
            ).count()
        user = current_user if current_user.is_authenticated else None
        return {'unread_count': unread, 'current_user': user}

    # Error handlers
    @application.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @application.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # Register all HTTP routes via blueprints
    from app.routes import register_blueprints
    register_blueprints(application)

    return application

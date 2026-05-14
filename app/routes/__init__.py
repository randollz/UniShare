from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.listings import listings_bp
from app.routes.notes import notes_bp
from app.routes.sessions import sessions_bp
from app.routes.bounties import bounties_bp
from app.routes.feed import feed_bp
from app.routes.messages import messages_bp
from app.routes.users import users_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(bounties_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(users_bp)

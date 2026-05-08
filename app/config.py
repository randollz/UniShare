import os

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
default_database_location = 'sqlite:///' + os.path.join(basedir, 'app.db')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or default_database_location
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # tokens valid for the lifetime of the session
    # WTF_CSRF_SECRET_KEY falls back to SECRET_KEY if not set

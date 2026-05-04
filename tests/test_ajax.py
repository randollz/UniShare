"""Tests for the AJAX /api/search_users endpoint."""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False


@pytest.fixture(scope='module')
def app():
    application = create_app(config_class=TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope='module')
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        yield
        _db.session.rollback()


def _create_user(app, first, last, email, password='pass1234'):
    with app.app_context():
        user = User(first_name=first, last_name=last, email=email, password_hash='')
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user.id


def _login(client, email, password='pass1234'):
    client.get('/logout')  # ensure any previous session is cleared first
    client.post('/login', data={'email': email, 'password': password,
                                'action': 'login'}, follow_redirects=True)


class TestSearchUsersEndpoint:
    def test_requires_login(self, client):
        """Unauthenticated requests must be redirected."""
        with client.session_transaction() as sess:
            sess.clear()
        rv = client.get('/api/search_users?q=alice', follow_redirects=False)
        assert rv.status_code in (301, 302, 401)

    def test_returns_json_array(self, client, app):
        """Returns a JSON array when authenticated."""
        _create_user(app, 'Search', 'User', 'searchuser@example.com')
        _login(client, 'searchuser@example.com')
        rv = client.get('/api/search_users?q=Search')
        assert rv.status_code == 200
        assert rv.content_type.startswith('application/json')
        assert isinstance(rv.get_json(), list)

    def test_short_query_returns_empty(self, client, app):
        """Queries shorter than 2 chars return an empty list."""
        _create_user(app, 'Short', 'Query', 'shortq@example.com')
        _login(client, 'shortq@example.com')
        rv = client.get('/api/search_users?q=a')
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_filters_by_name(self, client, app):
        """Results include users whose name matches the query."""
        _create_user(app, 'Uniquename', 'Person', 'uniquename@example.com')
        _create_user(app, 'Searcher', 'Two', 'searcher2@example.com')
        _login(client, 'searcher2@example.com')
        rv = client.get('/api/search_users?q=Uniquename')
        data = rv.get_json()
        assert any('Uniquename' in u['name'] for u in data)

    def test_excludes_current_user(self, client, app):
        """Logged-in user should not appear in their own search results."""
        _create_user(app, 'Selfcheck', 'User', 'selfcheck@example.com')
        _login(client, 'selfcheck@example.com')
        rv = client.get('/api/search_users?q=Selfcheck')
        data = rv.get_json()
        assert not any('Selfcheck' in u['name'] for u in data)

    def test_response_shape(self, client, app):
        """Each result object has id, name, and email fields."""
        _create_user(app, 'Shape', 'Test', 'shapetest@example.com')
        _create_user(app, 'ShapeSearcher', 'X', 'shapesearcher@example.com')
        _login(client, 'shapesearcher@example.com')
        rv = client.get('/api/search_users?q=Shape')
        data = rv.get_json()
        for u in data:
            assert 'id' in u
            assert 'name' in u
            assert 'email' in u

"""Unit tests for the AJAX /api/search_users endpoint."""
import unittest
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


def _create_user(app, first, last, email, password='pass1234'):
    with app.app_context():
        user = User(first_name=first, last_name=last, email=email, password_hash='')
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user.id


def _login(client, email, password='pass1234'):
    client.get('/logout')
    client.post('/login', data={'email': email, 'password': password,
                                'action': 'login'}, follow_redirects=True)


class TestSearchUsersEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = create_app(config_class=TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        _db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        _db.session.remove()
        _db.drop_all()
        self.ctx.pop()

    def test_requires_login(self):
        """Unauthenticated requests must be redirected."""
        with self.client.session_transaction() as sess:
            sess.clear()
        rv = self.client.get('/api/search_users?q=alice', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302, 401), "Search endpoint should redirect unauthenticated users")

    def test_returns_json_array(self):
        """Returns a JSON array when authenticated."""
        _create_user(self.app, 'Search', 'User', 'searchuser@example.com')
        _login(self.client, 'searchuser@example.com')
        rv = self.client.get('/api/search_users?q=Search')
        self.assertEqual(rv.status_code, 200, "Search should return 200 for authenticated users")
        self.assertTrue(rv.content_type.startswith('application/json'), "Response content type should be JSON")
        self.assertIsInstance(rv.get_json(), list, "Response body should be a JSON array")

    def test_short_query_returns_empty(self):
        """Queries shorter than 2 chars return an empty list."""
        _create_user(self.app, 'Short', 'Query', 'shortq@example.com')
        _login(self.client, 'shortq@example.com')
        rv = self.client.get('/api/search_users?q=a')
        self.assertEqual(rv.status_code, 200, "Short query should still return 200")
        self.assertEqual(rv.get_json(), [], "Query shorter than 2 chars should return an empty list")

    def test_filters_by_name(self):
        """Results include users whose name matches the query."""
        _create_user(self.app, 'Uniquename', 'Person', 'uniquename@example.com')
        _create_user(self.app, 'Searcher', 'Two', 'searcher2@example.com')
        _login(self.client, 'searcher2@example.com')
        rv = self.client.get('/api/search_users?q=Uniquename')
        data = rv.get_json()
        self.assertTrue(
            any('Uniquename' in u['name'] for u in data),
            "Search results should include users whose name matches the query"
        )

    def test_excludes_current_user(self):
        """Logged-in user should not appear in their own search results."""
        _create_user(self.app, 'Selfcheck', 'User', 'selfcheck@example.com')
        _login(self.client, 'selfcheck@example.com')
        rv = self.client.get('/api/search_users?q=Selfcheck')
        data = rv.get_json()
        self.assertFalse(
            any('Selfcheck' in u['name'] for u in data),
            "Logged-in user should not appear in their own search results"
        )

    def test_response_shape(self):
        """Each result object has id, name, and email fields."""
        _create_user(self.app, 'Shape', 'Test', 'shapetest@example.com')
        _create_user(self.app, 'ShapeSearcher', 'X', 'shapesearcher@example.com')
        _login(self.client, 'shapesearcher@example.com')
        rv = self.client.get('/api/search_users?q=Shape')
        data = rv.get_json()
        for u in data:
            self.assertIn('id', u, "Each result should have an 'id' field")
            self.assertIn('name', u, "Each result should have a 'name' field")
            self.assertIn('email', u, "Each result should have an 'email' field")

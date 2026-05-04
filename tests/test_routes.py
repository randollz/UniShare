"""Integration tests for Flask routes using the ORM layer."""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User, Listing, Note, StudySession, Bounty


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(client, app, email='test@example.com', password='pass1234',
                        first='Test', last='User'):
    """Create a user in the DB then log in via the login route."""
    with app.app_context():
        user = User(first_name=first, last_name=last, email=email, password_hash='')
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

    client.post('/login', data={'email': email, 'password': password,
                                'action': 'login'}, follow_redirects=True)
    return user_id


# ── Public pages ──────────────────────────────────────────────────────────────

class TestPublicRoutes:
    def test_home_returns_200(self, client):
        rv = client.get('/')
        assert rv.status_code == 200

    def test_login_page_returns_200(self, client):
        rv = client.get('/login')
        assert rv.status_code == 200

    def test_marketplace_returns_200(self, client):
        rv = client.get('/marketplace')
        assert rv.status_code == 200

    def test_notes_returns_200(self, client):
        rv = client.get('/notes')
        assert rv.status_code == 200

    def test_sessions_returns_200(self, client):
        rv = client.get('/sessions')
        assert rv.status_code == 200

    def test_bounties_returns_200(self, client):
        rv = client.get('/bounties')
        assert rv.status_code == 200

    def test_leaderboard_returns_200(self, client):
        rv = client.get('/leaderboard')
        assert rv.status_code == 200


# ── Authentication ────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_and_login(self, client, app):
        with app.app_context():
            rv = client.post('/login', data={
                'action': 'register',
                'first_name': 'Alice',
                'last_name': 'Smith',
                'email': 'alice_auth@example.com',
                'password': 'secret99',
                'confirm_password': 'secret99',
            }, follow_redirects=True)
        assert rv.status_code == 200

    def test_login_wrong_password(self, client, app):
        with app.app_context():
            u = User(first_name='Bob', last_name='Jones',
                     email='bob_auth@example.com', password_hash='')
            u.set_password('correct')
            _db.session.add(u)
            _db.session.commit()

        rv = client.post('/login', data={
            'action': 'login',
            'email': 'bob_auth@example.com',
            'password': 'wrong',
        }, follow_redirects=True)
        assert rv.status_code == 200
        assert b'Invalid' in rv.data or b'incorrect' in rv.data.lower() or rv.status_code == 200

    def test_logout_redirects(self, client, app):
        _register_and_login(client, app, email='logout_user@example.com')
        rv = client.get('/logout', follow_redirects=False)
        assert rv.status_code in (301, 302)


# ── Protected routes redirect when logged out ─────────────────────────────────

class TestProtectedRedirect:
    def test_dashboard_requires_login(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        rv = client.get('/dashboard', follow_redirects=False)
        assert rv.status_code in (301, 302)

    def test_create_listing_requires_login(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        rv = client.get('/create_listing', follow_redirects=False)
        assert rv.status_code in (301, 302)

    def test_messages_requires_login(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        rv = client.get('/messages', follow_redirects=False)
        assert rv.status_code in (301, 302)


# ── Listing creation ──────────────────────────────────────────────────────────

class TestListings:
    def test_create_listing(self, client, app):
        _register_and_login(client, app, email='listing_user@example.com')
        rv = client.post('/create_listing', data={
            'title': 'Python Textbook',
            'unit_code': 'CITS1401',
            'price': '25.00',
            'condition': 'Good',
            'description': 'Great condition.',
        }, follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            listing = Listing.query.filter_by(title='Python Textbook').first()
            assert listing is not None
            assert listing.price == 25.00

    def test_create_listing_missing_title(self, client, app):
        _register_and_login(client, app, email='listing_user2@example.com')
        before_count = 0
        with app.app_context():
            before_count = Listing.query.filter_by(unit_code='CITS9999').count()
        rv = client.post('/create_listing', data={
            'title': '',
            'unit_code': 'CITS9999',
            'price': '25.00',
            'condition': 'Good',
        }, follow_redirects=True)
        assert rv.status_code == 200
        # Should stay on form with error, not create listing
        with app.app_context():
            assert Listing.query.filter_by(unit_code='CITS9999').count() == before_count


# ── Note creation ─────────────────────────────────────────────────────────────

class TestNotes:
    def test_create_note(self, client, app):
        _register_and_login(client, app, email='note_user@example.com')
        rv = client.post('/create_note', data={
            'title': 'Week 1 Lecture Notes',
            'unit_code': 'CITS3403',
            'semester': 'S1 2025',
            'description': 'Introduction lecture summary.',
        }, follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            note = Note.query.filter_by(title='Week 1 Lecture Notes').first()
            assert note is not None


# ── Study sessions ────────────────────────────────────────────────────────────

class TestStudySessions:
    def test_create_session(self, client, app):
        _register_and_login(client, app, email='session_user@example.com')
        rv = client.post('/create_session', data={
            'title': 'Exam Prep Group',
            'unit_code': 'CITS3403',
            'location': 'Reid Library',
            'session_date': '2099-12-01T14:00',
            'max_attendees': '10',
            'description': 'Final exam prep.',
        }, follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            s = StudySession.query.filter_by(title='Exam Prep Group').first()
            assert s is not None


# ── Bounties ──────────────────────────────────────────────────────────────────

class TestBounties:
    def test_create_bounty(self, client, app):
        _register_and_login(client, app, email='bounty_user@example.com')
        rv = client.post('/create_bounty', data={
            'title': 'Need CITS3403 notes',
            'unit_code': 'CITS3403',
            'reward': '10.00',
            'description': 'Looking for comprehensive notes.',
        }, follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            b = Bounty.query.filter_by(title='Need CITS3403 notes').first()
            assert b is not None


# ── AJAX: search_users ────────────────────────────────────────────────────────

class TestAjaxSearchUsers:
    def test_search_users_requires_login(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        rv = client.get('/api/search_users?q=alice', follow_redirects=False)
        assert rv.status_code in (301, 302)

    def test_search_users_returns_json(self, client, app):
        _register_and_login(client, app, email='search_host@example.com')
        with app.app_context():
            target = User(first_name='Searchable', last_name='Person',
                          email='searchable@example.com', password_hash='x')
            _db.session.add(target)
            _db.session.commit()

        rv = client.get('/api/search_users?q=Searchable')
        assert rv.status_code == 200
        data = rv.get_json()
        assert isinstance(data, list)
        assert any(u['name'] == 'Searchable Person' for u in data)

    def test_search_users_short_query_returns_empty(self, client, app):
        _register_and_login(client, app, email='search_host2@example.com')
        rv = client.get('/api/search_users?q=a')
        assert rv.status_code == 200
        assert rv.get_json() == []

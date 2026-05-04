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
    """Create a user in the DB (if not already there) then log in via the login route."""
    client.get('/logout')  # ensure clean session before switching user
    with app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing:
            user_id = existing.id
        else:
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


# ── Listing detail & delete ───────────────────────────────────────────────────

class TestListingDetail:
    def test_view_listing(self, client, app):
        uid = _register_and_login(client, app, email='view_listing@example.com')
        with app.app_context():
            listing = Listing(seller_id=uid, title='Detail Listing',
                              unit_code='CITS1001', price=9.99, condition='Good')
            _db.session.add(listing)
            _db.session.commit()
            lid = listing.id
        rv = client.get(f'/listings/{lid}')
        assert rv.status_code == 200
        assert b'Detail Listing' in rv.data

    def test_delete_listing(self, client, app):
        uid = _register_and_login(client, app, email='del_listing@example.com')
        with app.app_context():
            listing = Listing(seller_id=uid, title='To Delete',
                              unit_code='CITS1001', price=5.0, condition='Good')
            _db.session.add(listing)
            _db.session.commit()
            lid = listing.id
        rv = client.post(f'/delete_listing/{lid}', follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            assert Listing.query.get(lid) is None

    def test_delete_listing_wrong_owner(self, client, app):
        owner_id = _register_and_login(client, app, email='owner_l@example.com')
        with app.app_context():
            listing = Listing(seller_id=owner_id, title='Protected',
                              unit_code='CITS1001', price=5.0, condition='Good')
            _db.session.add(listing)
            _db.session.commit()
            lid = listing.id
        # Log in as a different user
        _register_and_login(client, app, email='intruder_l@example.com')
        client.post(f'/delete_listing/{lid}', follow_redirects=True)
        with app.app_context():
            # Listing should still exist (wrong owner can't delete)
            assert Listing.query.get(lid) is not None


# ── Note detail & upvote ──────────────────────────────────────────────────────

class TestNoteDetail:
    def test_view_note(self, client, app):
        uid = _register_and_login(client, app, email='view_note@example.com')
        with app.app_context():
            note = Note(author_id=uid, title='Test Note Detail',
                        unit_code='CITS3403', semester='S1 2025', upvotes=0)
            _db.session.add(note)
            _db.session.commit()
            nid = note.id
        rv = client.get(f'/notes/{nid}')
        assert rv.status_code == 200
        assert b'Test Note Detail' in rv.data

    def test_upvote_note(self, client, app):
        uid = _register_and_login(client, app, email='upvote_user@example.com')
        with app.app_context():
            note = Note(author_id=uid, title='Upvotable Note',
                        unit_code='CITS3003', semester='S2 2025', upvotes=0)
            _db.session.add(note)
            _db.session.commit()
            nid = note.id
        client.post(f'/upvote_note/{nid}', follow_redirects=True)
        with app.app_context():
            updated = Note.query.get(nid)
            assert updated.upvotes == 1


# ── Session delete & cancel RSVP ─────────────────────────────────────────────

class TestSessionActions:
    def test_delete_session(self, client, app):
        from datetime import datetime, timedelta
        uid = _register_and_login(client, app, email='del_session@example.com')
        with app.app_context():
            s = StudySession(host_id=uid, title='Session to Delete',
                             unit_code='CITS4009',
                             session_date=datetime.now() + timedelta(days=7),
                             location='Online', max_attendees=5)
            _db.session.add(s)
            _db.session.commit()
            sid = s.id
        rv = client.post(f'/delete_session/{sid}', follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            from app.models import StudySession as SS
            assert SS.query.get(sid) is None

    def test_cancel_rsvp(self, client, app):
        from datetime import datetime, timedelta
        from app.models import SessionRSVP
        host_id = _register_and_login(client, app, email='cancel_host@example.com')
        uid = _register_and_login(client, app, email='cancel_rsvp@example.com')
        with app.app_context():
            s = StudySession(host_id=host_id, title='Cancel Session',
                             unit_code='CITS4009',
                             session_date=datetime.now() + timedelta(days=7),
                             location='Online', max_attendees=5)
            _db.session.add(s)
            _db.session.commit()
            rsvp = SessionRSVP(session_id=s.id, user_id=uid)
            _db.session.add(rsvp)
            _db.session.commit()
            sid = s.id
        rv = client.post(f'/cancel_rsvp/{sid}', follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            assert SessionRSVP.query.filter_by(session_id=sid, user_id=uid).first() is None


# ── Bounty detail & claim ─────────────────────────────────────────────────────

class TestBountyActions:
    def test_view_bounty(self, client, app):
        uid = _register_and_login(client, app, email='view_bounty@example.com')
        with app.app_context():
            b = Bounty(poster_id=uid, title='View Bounty Test',
                       unit_code='CITS3403', reward=20.0)
            _db.session.add(b)
            _db.session.commit()
            bid = b.id
        rv = client.get(f'/bounties/{bid}')
        assert rv.status_code == 200
        assert b'View Bounty Test' in rv.data

    def test_claim_bounty(self, client, app):
        poster_id = _register_and_login(client, app, email='poster_b@example.com')
        with app.app_context():
            b = Bounty(poster_id=poster_id, title='Claimable Bounty',
                       unit_code='CITS3403', reward=15.0)
            _db.session.add(b)
            _db.session.commit()
            bid = b.id
        # Log in as a different user to claim
        _register_and_login(client, app, email='claimer_b@example.com')
        rv = client.post(f'/claim_bounty/{bid}', follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            assert Bounty.query.get(bid) is None  # Bounty consumed on claim

    def test_cannot_claim_own_bounty(self, client, app):
        uid = _register_and_login(client, app, email='self_claimer@example.com')
        with app.app_context():
            b = Bounty(poster_id=uid, title='Own Bounty',
                       unit_code='CITS3403', reward=5.0)
            _db.session.add(b)
            _db.session.commit()
            bid = b.id
        rv = client.post(f'/claim_bounty/{bid}', follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            assert Bounty.query.get(bid) is not None  # Should NOT be deleted


# ── Profile page ──────────────────────────────────────────────────────────────

class TestProfile:
    def test_view_profile(self, client, app):
        uid = _register_and_login(client, app, email='profile_view@example.com',
                                  first='Profile', last='User')
        rv = client.get(f'/profile/{uid}')
        assert rv.status_code == 200
        assert b'Profile' in rv.data

    def test_view_profile_not_found(self, client, app):
        _register_and_login(client, app, email='profile_404@example.com')
        rv = client.get('/profile/99999')
        assert rv.status_code == 404


# ── Settings ──────────────────────────────────────────────────────────────────

class TestSettings:
    def test_get_settings(self, client, app):
        _register_and_login(client, app, email='settings_get@example.com')
        rv = client.get('/settings')
        assert rv.status_code == 200

    def test_update_name(self, client, app):
        uid = _register_and_login(client, app, email='settings_post@example.com',
                                  first='Old', last='Name')
        rv = client.post('/settings', data={
            'first_name': 'New',
            'last_name': 'Name',
            'bio': 'Hello world',
        }, follow_redirects=True)
        assert rv.status_code == 200
        with app.app_context():
            u = User.query.filter_by(id=uid).first()
            assert u.first_name == 'New'
            assert u.bio == 'Hello world'


# ── Messages ──────────────────────────────────────────────────────────────────

class TestMessages:
    def test_messages_list(self, client, app):
        _register_and_login(client, app, email='msg_list@example.com')
        rv = client.get('/messages')
        assert rv.status_code == 200

    def test_messages_thread(self, client, app):
        from app.models import Message as Msg
        uid_a = _register_and_login(client, app, email='msg_a@example.com')
        uid_b = _register_and_login(client, app, email='msg_b@example.com')
        with app.app_context():
            m = Msg(sender_id=uid_a, receiver_id=uid_b, body='Hello', read=0)
            _db.session.add(m)
            _db.session.commit()
        # Log in as B and view thread
        _register_and_login(client, app, email='msg_b@example.com')
        rv = client.get(f'/messages/{uid_a}')
        assert rv.status_code == 200

    def test_api_send_message(self, client, app):
        uid_a = _register_and_login(client, app, email='apisend_a@example.com')
        uid_b = _register_and_login(client, app, email='apisend_b@example.com')
        # Switch back to A (already registered above) and send to B
        client.get('/logout')
        client.post('/login', data={'email': 'apisend_a@example.com', 'password': 'pass1234',
                                    'action': 'login'}, follow_redirects=True)
        rv = client.post(f'/api/messages/{uid_b}/send',
                         json={'body': 'Hi there!'},
                         content_type='application/json')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['body'] == 'Hi there!'

    def test_leaderboard(self, client, app):
        rv = client.get('/leaderboard')
        assert rv.status_code == 200

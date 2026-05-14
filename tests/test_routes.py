"""Unit tests for Flask routes using the ORM layer."""
import unittest
from datetime import datetime, timedelta
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


def _register_and_login(client, app, email='test@example.com', password='pass1234',
                        first='Test', last='User'):
    """Create a user in the DB (if not already there) then log in via the login route."""
    client.get('/logout')
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

class TestPublicRoutes(unittest.TestCase):
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

    def test_home_returns_200(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200, "Homepage should return 200")

    def test_login_page_returns_200(self):
        rv = self.client.get('/login')
        self.assertEqual(rv.status_code, 200, "Login page should return 200")

    def test_marketplace_returns_200(self):
        rv = self.client.get('/marketplace')
        self.assertEqual(rv.status_code, 200, "Marketplace should return 200 for public users")

    def test_notes_returns_200(self):
        rv = self.client.get('/notes')
        self.assertEqual(rv.status_code, 200, "Notes page should return 200 for public users")

    def test_sessions_returns_200(self):
        rv = self.client.get('/sessions')
        self.assertEqual(rv.status_code, 200, "Sessions page should return 200 for public users")

    def test_bounties_returns_200(self):
        rv = self.client.get('/bounties')
        self.assertEqual(rv.status_code, 200, "Bounties page should return 200 for public users")

    def test_leaderboard_returns_200(self):
        rv = self.client.get('/leaderboard')
        self.assertEqual(rv.status_code, 200, "Leaderboard should return 200 for public users")


# ── Authentication ────────────────────────────────────────────────────────────

class TestAuth(unittest.TestCase):
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

    def test_register_and_login(self):
        rv = self.client.post('/login', data={
            'action': 'register',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice_auth@example.com',
            'password': 'secret99',
            'confirm_password': 'secret99',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Successful registration should return 200")

    def test_login_wrong_password(self):
        u = User(first_name='Bob', last_name='Jones',
                 email='bob_auth@example.com', password_hash='')
        u.set_password('correct')
        _db.session.add(u)
        _db.session.commit()
        rv = self.client.post('/login', data={
            'action': 'login',
            'email': 'bob_auth@example.com',
            'password': 'wrong',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Failed login should return 200 with error message")
        self.assertTrue(
            b'Invalid' in rv.data or b'invalid' in rv.data.lower(),
            "Failed login response should contain an error message"
        )

    def test_logout_redirects(self):
        _register_and_login(self.client, self.app, email='logout_user@example.com')
        rv = self.client.get('/logout', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302), "Logout should redirect the user")


# ── Protected routes redirect when logged out ─────────────────────────────────

class TestProtectedRedirect(unittest.TestCase):
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

    def test_dashboard_requires_login(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        rv = self.client.get('/dashboard', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302), "Dashboard should redirect unauthenticated users")

    def test_create_listing_requires_login(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        rv = self.client.get('/create_listing', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302), "Create listing should redirect unauthenticated users")

    def test_messages_requires_login(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        rv = self.client.get('/messages', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302), "Messages should redirect unauthenticated users")


# ── Listing creation ──────────────────────────────────────────────────────────

class TestListings(unittest.TestCase):
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

    def test_create_listing(self):
        _register_and_login(self.client, self.app, email='listing_user@example.com')
        rv = self.client.post('/create_listing', data={
            'title': 'Python Textbook',
            'unit_code': 'CITS1401',
            'price': '25.00',
            'condition': 'Good',
            'description': 'Great condition.',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Listing creation should succeed")
        with self.app.app_context():
            listing = Listing.query.filter_by(title='Python Textbook').first()
            self.assertIsNotNone(listing, "Created listing should exist in the database")
            self.assertEqual(listing.price, 25.00, "Listing price should match the submitted value")

    def test_create_listing_missing_title(self):
        _register_and_login(self.client, self.app, email='listing_user2@example.com')
        with self.app.app_context():
            before_count = Listing.query.filter_by(unit_code='CITS9999').count()
        rv = self.client.post('/create_listing', data={
            'title': '',
            'unit_code': 'CITS9999',
            'price': '25.00',
            'condition': 'Good',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Form with missing title should return 200")
        with self.app.app_context():
            self.assertEqual(
                Listing.query.filter_by(unit_code='CITS9999').count(),
                before_count,
                "No listing should be created when the title field is empty"
            )


# ── Note creation ─────────────────────────────────────────────────────────────

class TestNotes(unittest.TestCase):
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

    def test_create_note(self):
        _register_and_login(self.client, self.app, email='note_user@example.com')
        rv = self.client.post('/create_note', data={
            'title': 'Week 1 Lecture Notes',
            'unit_code': 'CITS3403',
            'semester': 'S1 2025',
            'description': 'Introduction lecture summary.',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Note creation should succeed")
        with self.app.app_context():
            note = Note.query.filter_by(title='Week 1 Lecture Notes').first()
            self.assertIsNotNone(note, "Created note should exist in the database")


# ── Study sessions ────────────────────────────────────────────────────────────

class TestStudySessions(unittest.TestCase):
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

    def test_create_session(self):
        _register_and_login(self.client, self.app, email='session_user@example.com')
        rv = self.client.post('/create_session', data={
            'title': 'Exam Prep Group',
            'unit_code': 'CITS3403',
            'location': 'Reid Library',
            'session_date': '2099-12-01T14:00',
            'max_attendees': '10',
            'description': 'Final exam prep.',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Session creation should succeed")
        with self.app.app_context():
            s = StudySession.query.filter_by(title='Exam Prep Group').first()
            self.assertIsNotNone(s, "Created session should exist in the database")


# ── Bounties ──────────────────────────────────────────────────────────────────

class TestBounties(unittest.TestCase):
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

    def test_create_bounty(self):
        _register_and_login(self.client, self.app, email='bounty_user@example.com')
        rv = self.client.post('/create_bounty', data={
            'title': 'Need CITS3403 notes',
            'unit_code': 'CITS3403',
            'reward': '10.00',
            'description': 'Looking for comprehensive notes.',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Bounty creation should succeed")
        with self.app.app_context():
            b = Bounty.query.filter_by(title='Need CITS3403 notes').first()
            self.assertIsNotNone(b, "Created bounty should exist in the database")


# ── AJAX: search_users ────────────────────────────────────────────────────────

class TestAjaxSearchUsers(unittest.TestCase):
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

    def test_search_users_requires_login(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        rv = self.client.get('/api/search_users?q=alice', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302), "Search endpoint should redirect unauthenticated users")

    def test_search_users_returns_json(self):
        _register_and_login(self.client, self.app, email='search_host@example.com')
        with self.app.app_context():
            target = User(first_name='Searchable', last_name='Person',
                          email='searchable@example.com', password_hash='x')
            _db.session.add(target)
            _db.session.commit()
        rv = self.client.get('/api/search_users?q=Searchable')
        self.assertEqual(rv.status_code, 200, "Search should return 200 for authenticated users")
        data = rv.get_json()
        self.assertIsInstance(data, list, "Search response should be a JSON array")
        self.assertTrue(
            any(u['name'] == 'Searchable Person' for u in data),
            "Search results should include the matching user"
        )

    def test_search_users_short_query_returns_empty(self):
        _register_and_login(self.client, self.app, email='search_host2@example.com')
        rv = self.client.get('/api/search_users?q=a')
        self.assertEqual(rv.status_code, 200, "Short query should still return 200")
        self.assertEqual(rv.get_json(), [], "Query shorter than 2 chars should return an empty list")


# ── Listing detail & delete ───────────────────────────────────────────────────

class TestListingDetail(unittest.TestCase):
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

    def test_view_listing(self):
        uid = _register_and_login(self.client, self.app, email='view_listing@example.com')
        with self.app.app_context():
            listing = Listing(seller_id=uid, title='Detail Listing',
                              unit_code='CITS1001', price=9.99, condition='Good')
            _db.session.add(listing)
            _db.session.commit()
            lid = listing.id
        rv = self.client.get(f'/listings/{lid}')
        self.assertEqual(rv.status_code, 200, "Listing detail page should return 200")
        self.assertIn(b'Detail Listing', rv.data, "Listing title should appear on the page")

    def test_delete_listing(self):
        uid = _register_and_login(self.client, self.app, email='del_listing@example.com')
        with self.app.app_context():
            listing = Listing(seller_id=uid, title='To Delete',
                              unit_code='CITS1001', price=5.0, condition='Good')
            _db.session.add(listing)
            _db.session.commit()
            lid = listing.id
        rv = self.client.post(f'/delete_listing/{lid}', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Delete should redirect with 200")
        with self.app.app_context():
            self.assertIsNone(Listing.query.get(lid), "Deleted listing should not exist in the database")

    def test_delete_listing_wrong_owner(self):
        owner_id = _register_and_login(self.client, self.app, email='owner_l@example.com')
        with self.app.app_context():
            listing = Listing(seller_id=owner_id, title='Protected',
                              unit_code='CITS1001', price=5.0, condition='Good')
            _db.session.add(listing)
            _db.session.commit()
            lid = listing.id
        _register_and_login(self.client, self.app, email='intruder_l@example.com')
        self.client.post(f'/delete_listing/{lid}', follow_redirects=True)
        with self.app.app_context():
            self.assertIsNotNone(
                Listing.query.get(lid),
                "Listing should not be deleted by a user who does not own it"
            )


# ── Note detail & upvote ──────────────────────────────────────────────────────

class TestNoteDetail(unittest.TestCase):
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

    def test_view_note(self):
        uid = _register_and_login(self.client, self.app, email='view_note@example.com')
        with self.app.app_context():
            note = Note(author_id=uid, title='Test Note Detail',
                        unit_code='CITS3403', semester='S1 2025', upvotes=0)
            _db.session.add(note)
            _db.session.commit()
            nid = note.id
        rv = self.client.get(f'/notes/{nid}')
        self.assertEqual(rv.status_code, 200, "Note detail page should return 200")
        self.assertIn(b'Test Note Detail', rv.data, "Note title should appear on the page")

    def test_upvote_note(self):
        uid = _register_and_login(self.client, self.app, email='upvote_user@example.com')
        with self.app.app_context():
            note = Note(author_id=uid, title='Upvotable Note',
                        unit_code='CITS3003', semester='S2 2025', upvotes=0)
            _db.session.add(note)
            _db.session.commit()
            nid = note.id
        self.client.post(f'/upvote_note/{nid}', follow_redirects=True)
        with self.app.app_context():
            updated = Note.query.get(nid)
            self.assertEqual(updated.upvotes, 1, "Upvote count should increment by 1")


# ── Session delete & cancel RSVP ─────────────────────────────────────────────

class TestSessionActions(unittest.TestCase):
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

    def test_delete_session(self):
        uid = _register_and_login(self.client, self.app, email='del_session@example.com')
        with self.app.app_context():
            s = StudySession(host_id=uid, title='Session to Delete',
                             unit_code='CITS4009',
                             session_date=datetime.now() + timedelta(days=7),
                             location='Online', max_attendees=5)
            _db.session.add(s)
            _db.session.commit()
            sid = s.id
        rv = self.client.post(f'/delete_session/{sid}', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Delete session should redirect with 200")
        with self.app.app_context():
            self.assertIsNone(StudySession.query.get(sid), "Deleted session should not exist in the database")

    def test_cancel_rsvp(self):
        from app.models import SessionRSVP
        host_id = _register_and_login(self.client, self.app, email='cancel_host@example.com')
        uid = _register_and_login(self.client, self.app, email='cancel_rsvp@example.com')
        with self.app.app_context():
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
        rv = self.client.post(f'/cancel_rsvp/{sid}', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Cancel RSVP should redirect with 200")
        with self.app.app_context():
            self.assertIsNone(
                SessionRSVP.query.filter_by(session_id=sid, user_id=uid).first(),
                "RSVP record should be removed after cancellation"
            )


# ── RSVP creation & capacity enforcement ─────────────────────────────────────

class TestRSVP(unittest.TestCase):
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

    def test_rsvp_creates_record(self):
        from app.models import SessionRSVP
        host_id = _register_and_login(self.client, self.app, email='rsvp_host@example.com')
        with self.app.app_context():
            s = StudySession(host_id=host_id, title='RSVP Session',
                             unit_code='CITS3403',
                             session_date=datetime.now() + timedelta(days=7),
                             location='Online', max_attendees=5)
            _db.session.add(s)
            _db.session.commit()
            sid = s.id
        attendee_id = _register_and_login(self.client, self.app, email='rsvp_attendee@example.com')
        rv = self.client.post(f'/rsvp_session/{sid}', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "RSVP should succeed and redirect")
        with self.app.app_context():
            rsvp = SessionRSVP.query.filter_by(session_id=sid, user_id=attendee_id).first()
            self.assertIsNotNone(rsvp, "RSVP record should be created in the database")

    def test_rsvp_blocked_when_full(self):
        from app.models import SessionRSVP
        host_id = _register_and_login(self.client, self.app, email='rsvp_full_host@example.com')
        first_id = _register_and_login(self.client, self.app, email='rsvp_first@example.com')
        with self.app.app_context():
            s = StudySession(host_id=host_id, title='Full Session',
                             unit_code='CITS3403',
                             session_date=datetime.now() + timedelta(days=7),
                             location='Online', max_attendees=1)
            _db.session.add(s)
            _db.session.commit()
            rsvp = SessionRSVP(session_id=s.id, user_id=first_id)
            _db.session.add(rsvp)
            _db.session.commit()
            sid = s.id
        _register_and_login(self.client, self.app, email='rsvp_second@example.com')
        rv = self.client.post(f'/rsvp_session/{sid}', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Over-capacity RSVP should still redirect with 200")
        with self.app.app_context():
            count = SessionRSVP.query.filter_by(session_id=sid).count()
            self.assertEqual(count, 1, "Session should have only 1 RSVP when at capacity")


# ── Bounty detail & claim ─────────────────────────────────────────────────────

class TestBountyActions(unittest.TestCase):
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

    def test_view_bounty(self):
        uid = _register_and_login(self.client, self.app, email='view_bounty@example.com')
        with self.app.app_context():
            b = Bounty(poster_id=uid, title='View Bounty Test',
                       unit_code='CITS3403', reward=20.0)
            _db.session.add(b)
            _db.session.commit()
            bid = b.id
        rv = self.client.get(f'/bounties/{bid}')
        self.assertEqual(rv.status_code, 200, "Bounty detail page should return 200")
        self.assertIn(b'View Bounty Test', rv.data, "Bounty title should appear on the page")

    def test_claim_bounty(self):
        poster_id = _register_and_login(self.client, self.app, email='poster_b@example.com')
        with self.app.app_context():
            b = Bounty(poster_id=poster_id, title='Claimable Bounty',
                       unit_code='CITS3403', reward=15.0)
            _db.session.add(b)
            _db.session.commit()
            bid = b.id
        _register_and_login(self.client, self.app, email='claimer_b@example.com')
        rv = self.client.post(f'/bounties/{bid}/claim', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Claim bounty should succeed")
        with self.app.app_context():
            bounty = Bounty.query.get(bid)
            self.assertIsNotNone(bounty, "Bounty should still exist after being claimed")
            self.assertEqual(bounty.status, 'claimed', "Bounty status should be updated to 'claimed'")

    def test_cannot_claim_own_bounty(self):
        uid = _register_and_login(self.client, self.app, email='self_claimer@example.com')
        with self.app.app_context():
            b = Bounty(poster_id=uid, title='Own Bounty',
                       unit_code='CITS3403', reward=5.0)
            _db.session.add(b)
            _db.session.commit()
            bid = b.id
        rv = self.client.post(f'/bounties/{bid}/claim', follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Claiming own bounty should return 200")
        with self.app.app_context():
            self.assertIsNotNone(
                Bounty.query.get(bid),
                "User should not be able to claim their own bounty"
            )


# ── Profile page ──────────────────────────────────────────────────────────────

class TestProfile(unittest.TestCase):
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

    def test_view_profile(self):
        uid = _register_and_login(self.client, self.app, email='profile_view@example.com',
                                  first='Profile', last='User')
        rv = self.client.get(f'/profile/{uid}')
        self.assertEqual(rv.status_code, 200, "Profile page should return 200")
        self.assertIn(b'Profile', rv.data, "Profile name should appear on the page")

    def test_view_profile_not_found(self):
        _register_and_login(self.client, self.app, email='profile_404@example.com')
        rv = self.client.get('/profile/99999')
        self.assertEqual(rv.status_code, 404, "Non-existent profile should return 404")


# ── Settings ──────────────────────────────────────────────────────────────────

class TestSettings(unittest.TestCase):
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

    def test_get_settings(self):
        _register_and_login(self.client, self.app, email='settings_get@example.com')
        rv = self.client.get('/settings')
        self.assertEqual(rv.status_code, 200, "Settings page should return 200 for authenticated users")

    def test_update_name(self):
        uid = _register_and_login(self.client, self.app, email='settings_post@example.com',
                                  first='Old', last='Name')
        rv = self.client.post('/settings', data={
            'first_name': 'New',
            'last_name': 'Name',
            'bio': 'Hello world',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200, "Settings update should succeed")
        with self.app.app_context():
            u = User.query.filter_by(id=uid).first()
            self.assertEqual(u.first_name, 'New', "First name should be updated in the database")
            self.assertEqual(u.bio, 'Hello world', "Bio should be updated in the database")


# ── Messages ──────────────────────────────────────────────────────────────────

class TestMessages(unittest.TestCase):
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

    def test_messages_list(self):
        _register_and_login(self.client, self.app, email='msg_list@example.com')
        rv = self.client.get('/messages')
        self.assertEqual(rv.status_code, 200, "Messages list should return 200")

    def test_messages_thread(self):
        from app.models import Message as Msg
        uid_a = _register_and_login(self.client, self.app, email='msg_a@example.com')
        uid_b = _register_and_login(self.client, self.app, email='msg_b@example.com')
        with self.app.app_context():
            m = Msg(sender_id=uid_a, receiver_id=uid_b, body='Hello', read=0)
            _db.session.add(m)
            _db.session.commit()
        _register_and_login(self.client, self.app, email='msg_b@example.com')
        rv = self.client.get(f'/messages/{uid_a}')
        self.assertEqual(rv.status_code, 200, "Message thread should return 200")

    def test_api_send_message(self):
        _register_and_login(self.client, self.app, email='apisend_a@example.com')
        uid_b = _register_and_login(self.client, self.app, email='apisend_b@example.com')
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'apisend_a@example.com', 'password': 'pass1234',
                                         'action': 'login'}, follow_redirects=True)
        rv = self.client.post(f'/api/messages/{uid_b}/send',
                              json={'body': 'Hi there!'},
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200, "API message send should return 200")
        data = rv.get_json()
        self.assertEqual(data['body'], 'Hi there!', "Response should echo the sent message body")

    def test_leaderboard(self):
        rv = self.client.get('/leaderboard')
        self.assertEqual(rv.status_code, 200, "Leaderboard should return 200")


# ── Session detail & comments ─────────────────────────────────────────────────

class TestSessionDetail(unittest.TestCase):
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

    def _make_session(self, host_id):
        with self.app.app_context():
            s = StudySession(host_id=host_id, title='Detail Test Session',
                             unit_code='CITS3403',
                             session_date=datetime.now() + timedelta(days=7),
                             location='Reid Library', max_attendees=10)
            _db.session.add(s)
            _db.session.commit()
            return s.id

    def test_view_session_page(self):
        uid = _register_and_login(self.client, self.app, email='viewsess@example.com')
        sid = self._make_session(uid)
        rv = self.client.get(f'/sessions/{sid}')
        self.assertEqual(rv.status_code, 200, "Session detail page should return 200")
        self.assertIn(b'Detail Test Session', rv.data, "Session title should appear on the page")

    def test_session_comment(self):
        from app.models import SessionComment
        host_id = _register_and_login(self.client, self.app, email='sess_host_c@example.com')
        _register_and_login(self.client, self.app, email='sess_commenter@example.com')
        sid = self._make_session(host_id)
        rv = self.client.post(f'/sessions/{sid}/comment',
                              json={'body': 'Will there be coffee?'},
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200, "Comment creation should return 200")
        data = rv.get_json()
        self.assertEqual(data['body'], 'Will there be coffee?', "Response should echo the comment body")
        with self.app.app_context():
            self.assertEqual(
                SessionComment.query.filter_by(session_id=sid).count(),
                1,
                "One comment should exist in the database"
            )

    def test_delete_session_comment(self):
        from app.models import SessionComment
        uid = _register_and_login(self.client, self.app, email='sess_del_comment@example.com')
        sid = self._make_session(uid)
        rv = self.client.post(f'/sessions/{sid}/comment',
                              json={'body': 'To be deleted'},
                              content_type='application/json')
        cid = rv.get_json()['id']
        rv2 = self.client.post(f'/session-comments/{cid}/delete')
        self.assertTrue(rv2.get_json()['ok'], "Comment deletion should return ok=True")
        with self.app.app_context():
            self.assertIsNone(SessionComment.query.get(cid), "Deleted comment should not exist in the database")


# ── Listing comments ──────────────────────────────────────────────────────────

class TestListingComments(unittest.TestCase):
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

    def _make_listing(self, uid):
        with self.app.app_context():
            listing = Listing(seller_id=uid, title='Comment Listing', unit_code='CITS3403',
                              price=20.0, condition='Good', description='test')
            _db.session.add(listing)
            _db.session.commit()
            return listing.id

    def test_listing_comment(self):
        from app.models import ListingComment
        seller_id = _register_and_login(self.client, self.app, email='list_sell_c@example.com')
        _register_and_login(self.client, self.app, email='list_buyer_c@example.com')
        lid = self._make_listing(seller_id)
        rv = self.client.post(f'/listings/{lid}/comment',
                              json={'body': 'Is this still available?'},
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200, "Listing comment creation should return 200")
        data = rv.get_json()
        self.assertEqual(data['body'], 'Is this still available?', "Response should echo the comment body")
        with self.app.app_context():
            self.assertEqual(
                ListingComment.query.filter_by(listing_id=lid).count(),
                1,
                "One comment should exist for the listing"
            )

    def test_delete_listing_comment(self):
        from app.models import ListingComment
        uid = _register_and_login(self.client, self.app, email='list_del_c@example.com')
        lid = self._make_listing(uid)
        rv = self.client.post(f'/listings/{lid}/comment',
                              json={'body': 'To delete'},
                              content_type='application/json')
        cid = rv.get_json()['id']
        rv2 = self.client.post(f'/listing-comments/{cid}/delete')
        self.assertTrue(rv2.get_json()['ok'], "Comment deletion should return ok=True")
        with self.app.app_context():
            self.assertIsNone(ListingComment.query.get(cid), "Deleted comment should not exist in the database")


# ── Bounty comments ───────────────────────────────────────────────────────────

class TestBountyComments(unittest.TestCase):
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

    def _make_bounty(self, uid):
        with self.app.app_context():
            b = Bounty(poster_id=uid, title='Comment Bounty',
                       description='Need help', reward=5.0)
            _db.session.add(b)
            _db.session.commit()
            return b.id

    def test_bounty_comment(self):
        from app.models import BountyComment
        poster_id = _register_and_login(self.client, self.app, email='bounty_post_c@example.com')
        _register_and_login(self.client, self.app, email='bounty_comm@example.com')
        bid = self._make_bounty(poster_id)
        rv = self.client.post(f'/bounties/{bid}/comment',
                              json={'body': 'I can help with this!'},
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200, "Bounty comment creation should return 200")
        data = rv.get_json()
        self.assertEqual(data['body'], 'I can help with this!', "Response should echo the comment body")
        with self.app.app_context():
            self.assertEqual(
                BountyComment.query.filter_by(bounty_id=bid).count(),
                1,
                "One comment should exist for the bounty"
            )

    def test_delete_bounty_comment(self):
        from app.models import BountyComment
        uid = _register_and_login(self.client, self.app, email='bounty_del_c@example.com')
        bid = self._make_bounty(uid)
        rv = self.client.post(f'/bounties/{bid}/comment',
                              json={'body': 'Delete me'},
                              content_type='application/json')
        cid = rv.get_json()['id']
        rv2 = self.client.post(f'/bounty-comments/{cid}/delete')
        self.assertTrue(rv2.get_json()['ok'], "Comment deletion should return ok=True")
        with self.app.app_context():
            self.assertIsNone(BountyComment.query.get(cid), "Deleted comment should not exist in the database")


# ── Universal search ──────────────────────────────────────────────────────────

class TestSearch(unittest.TestCase):
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

    def _make_listing(self, uid, title='Unique Listing Title', unit='CITS1401'):
        l = Listing(title=title, description='Search test description',
                    unit_code=unit, price=10.0, condition='Good', seller_id=uid)
        _db.session.add(l)
        _db.session.commit()
        return l.id

    def _make_note(self, uid, title='Unique Note Title', unit='CITS2200'):
        n = Note(title=title, description='Search test note desc',
                 unit_code=unit, semester='S1', author_id=uid)
        _db.session.add(n)
        _db.session.commit()
        return n.id

    def test_search_page_loads(self):
        _register_and_login(self.client, self.app, email='search_a@example.com')
        rv = self.client.get('/search')
        self.assertEqual(rv.status_code, 200, "GET /search should return 200")

    def test_search_empty_query_is_graceful(self):
        _register_and_login(self.client, self.app, email='search_b@example.com')
        rv = self.client.get('/search?q=')
        self.assertEqual(rv.status_code, 200, "Empty query should still return 200")
        self.assertNotIn(b'No results', rv.data,
                         "Empty query should not show 'No results' empty-state message")

    def test_search_returns_matching_listing(self):
        uid = _register_and_login(self.client, self.app, email='search_c@example.com')
        self._make_listing(uid, title='Quantum Physics Textbook')
        rv = self.client.get('/search?q=Quantum+Physics')
        self.assertEqual(rv.status_code, 200, "Search page should return 200")
        self.assertIn(b'Quantum Physics Textbook', rv.data,
                      "Matching listing title should appear in search results")

    def test_search_returns_matching_note(self):
        uid = _register_and_login(self.client, self.app, email='search_d@example.com')
        self._make_note(uid, title='Algorithms Lecture Notes')
        rv = self.client.get('/search?q=Algorithms+Lecture')
        self.assertEqual(rv.status_code, 200, "Search page should return 200")
        self.assertIn(b'Algorithms Lecture Notes', rv.data,
                      "Matching note title should appear in search results")

    def test_search_no_results_shows_empty_state(self):
        _register_and_login(self.client, self.app, email='search_e@example.com')
        rv = self.client.get('/search?q=xyznosuchthing99999')
        self.assertEqual(rv.status_code, 200, "Search page should return 200 even with no results")
        self.assertIn(b'No results', rv.data,
                      "Zero-result search should show the empty-state message")

    def test_search_requires_login(self):
        self.client.get('/logout')
        rv = self.client.get('/search?q=test', follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302),
                      "Unauthenticated search request should redirect to login")

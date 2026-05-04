"""Unit tests for SQLAlchemy ORM models."""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User, Listing, Note, StudySession, SessionRSVP, Bounty, Rating


@pytest.fixture(scope='module')
def app():
    """Create a test application with an in-memory SQLite database."""
    class TestConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SECRET_KEY = 'test-secret'

    application = create_app(config_class=TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Roll back after each test so tests are isolated."""
    with app.app_context():
        yield
        _db.session.rollback()


# ── User model ────────────────────────────────────────────────

class TestUser:
    def test_set_and_check_password(self, app):
        with app.app_context():
            user = User(first_name='Alice', last_name='Smith',
                        email='alice@test.com', password_hash='')
            user.set_password('secret123')
            assert user.check_password('secret123') is True
            assert user.check_password('wrong') is False

    def test_password_is_hashed(self, app):
        with app.app_context():
            user = User(first_name='Bob', last_name='Jones',
                        email='bob@test.com', password_hash='')
            user.set_password('mypassword')
            assert user.password_hash != 'mypassword'
            assert len(user.password_hash) > 20

    def test_get_average_rating_no_ratings(self, app):
        with app.app_context():
            user = User(first_name='Carol', last_name='Lee',
                        email='carol@test.com', password_hash='',
                        rating_sum=0, rating_count=0)
            assert user.get_average_rating() is None

    def test_get_average_rating_with_ratings(self, app):
        with app.app_context():
            user = User(first_name='Dan', last_name='Wu',
                        email='dan@test.com', password_hash='',
                        rating_sum=18, rating_count=4)
            assert user.get_average_rating() == 4.5

    def test_repr(self, app):
        with app.app_context():
            user = User(first_name='Eve', last_name='Brown',
                        email='eve@test.com', password_hash='')
            assert 'eve@test.com' in repr(user)

    def test_defaults(self, app):
        with app.app_context():
            user = User(first_name='Frank', last_name='Green',
                        email='frank@test.com', password_hash='x')
            _db.session.add(user)
            _db.session.flush()
            assert user.xp == 0
            assert user.rank == 'Newbie'
            assert user.rating_sum == 0
            assert user.rating_count == 0
            assert user.bio == ''


# ── Listing model ─────────────────────────────────────────────

class TestListing:
    def _make_user(self):
        user = User(first_name='Test', last_name='User',
                    email='testuser_listing@test.com', password_hash='x')
        _db.session.add(user)
        _db.session.flush()
        return user

    def test_create_listing(self, app):
        with app.app_context():
            user = self._make_user()
            listing = Listing(seller_id=user.id, title='Textbook',
                              unit_code='CITS3403', price=45.00, condition='Good')
            _db.session.add(listing)
            _db.session.flush()
            assert listing.id is not None
            assert listing.seller_id == user.id

    def test_seller_relationship(self, app):
        with app.app_context():
            user = self._make_user()
            listing = Listing(seller_id=user.id, title='Notes Pack',
                              unit_code='CITS2200', price=10.00, condition='Like New')
            _db.session.add(listing)
            _db.session.flush()
            assert listing.seller.email == user.email

    def test_repr(self, app):
        with app.app_context():
            listing = Listing(seller_id=1, title='My Book',
                              unit_code='MATH1012', price=20.0, condition='Fair')
            assert 'My Book' in repr(listing)


# ── Note model ────────────────────────────────────────────────

class TestNote:
    def _make_user(self):
        user = User(first_name='Note', last_name='Author',
                    email='noteauthor@test.com', password_hash='x')
        _db.session.add(user)
        _db.session.flush()
        return user

    def test_create_note(self, app):
        with app.app_context():
            user = self._make_user()
            note = Note(author_id=user.id, title='Lecture Summary',
                        unit_code='CITS3403', semester='S1 2025',
                        description='All 12 weeks condensed.')
            _db.session.add(note)
            _db.session.flush()
            assert note.id is not None
            assert note.upvotes == 0

    def test_author_relationship(self, app):
        with app.app_context():
            user = self._make_user()
            note = Note(author_id=user.id, title='Cheat Sheet',
                        unit_code='STAT2401')
            _db.session.add(note)
            _db.session.flush()
            assert note.author.email == user.email


# ── StudySession model ────────────────────────────────────────

class TestStudySession:
    def _make_user(self, email='sessionhost@test.com'):
        user = User(first_name='Host', last_name='User',
                    email=email, password_hash='x')
        _db.session.add(user)
        _db.session.flush()
        return user

    def test_create_session(self, app):
        with app.app_context():
            host = self._make_user()
            session = StudySession(host_id=host.id, title='Study Group',
                                   unit_code='CITS3403', max_attendees=10)
            _db.session.add(session)
            _db.session.flush()
            assert session.id is not None
            assert session.host.email == host.email

    def test_attendee_count(self, app):
        with app.app_context():
            host = self._make_user('host2@test.com')
            attendee = self._make_user('attendee@test.com')
            session = StudySession(host_id=host.id, title='RSVP Test',
                                   unit_code='MATH1012')
            _db.session.add(session)
            _db.session.flush()

            rsvp = SessionRSVP(session_id=session.id, user_id=attendee.id)
            _db.session.add(rsvp)
            _db.session.flush()

            assert session.attendee_count() == 1


# ── Rating model ──────────────────────────────────────────────

class TestRating:
    def test_rating_relationships(self, app):
        with app.app_context():
            rater = User(first_name='Rater', last_name='A',
                         email='rater@test.com', password_hash='x')
            rated = User(first_name='Rated', last_name='B',
                         email='rated@test.com', password_hash='x')
            _db.session.add_all([rater, rated])
            _db.session.flush()

            listing = Listing(seller_id=rated.id, title='Item',
                              unit_code='CITS1001', price=5.0, condition='Good')
            _db.session.add(listing)
            _db.session.flush()

            rating = Rating(rater_id=rater.id, rated_id=rated.id,
                            listing_id=listing.id, score=5, comment='Great!')
            _db.session.add(rating)
            _db.session.flush()

            assert rating.rater.email == 'rater@test.com'
            assert rating.rated.email == 'rated@test.com'
            assert rating.listing.title == 'Item'

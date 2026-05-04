from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    first_name   = db.Column(db.String(64),  nullable=False)
    last_name    = db.Column(db.String(64),  nullable=False)
    email        = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    xp           = db.Column(db.Integer, default=0)
    rank         = db.Column(db.String(64),  default='Newbie')
    rating_sum   = db.Column(db.Integer, default=0)
    rating_count = db.Column(db.Integer, default=0)
    bio          = db.Column(db.Text,    default='')

    # Relationships
    listings      = db.relationship('Listing',     back_populates='seller',  lazy='dynamic')
    notes         = db.relationship('Note',        back_populates='author',  lazy='dynamic')
    hosted_sessions = db.relationship('StudySession', back_populates='host', lazy='dynamic')
    rsvps         = db.relationship('SessionRSVP', back_populates='user',    lazy='dynamic')
    bounties      = db.relationship('Bounty',      back_populates='poster',  lazy='dynamic')
    saved_listings = db.relationship('SavedListing', back_populates='user',  lazy='dynamic')
    ratings_given    = db.relationship('Rating', foreign_keys='Rating.rater_id', back_populates='rater', lazy='dynamic')
    ratings_received = db.relationship('Rating', foreign_keys='Rating.rated_id', back_populates='rated', lazy='dynamic')
    sent_messages    = db.relationship('Message', foreign_keys='Message.sender_id',   back_populates='sender',   lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', back_populates='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_average_rating(self):
        if self.rating_count == 0:
            return None
        return round(self.rating_sum / self.rating_count, 1)

    def __repr__(self):
        return f'<User {self.email}>'


class Listing(db.Model):
    __tablename__ = 'listings'

    id          = db.Column(db.Integer,   primary_key=True)
    seller_id   = db.Column(db.Integer,   db.ForeignKey('users.id'), nullable=False)
    title       = db.Column(db.String(100), nullable=False)
    unit_code   = db.Column(db.String(16),  nullable=False)
    price       = db.Column(db.Float,     nullable=False)
    condition   = db.Column(db.String(32), nullable=False)
    description = db.Column(db.Text,      default='')
    created_at  = db.Column(db.DateTime,  server_default=db.func.now())

    seller        = db.relationship('User',        back_populates='listings')
    saved_by      = db.relationship('SavedListing', back_populates='listing', lazy='dynamic')
    ratings       = db.relationship('Rating',      back_populates='listing',  lazy='dynamic')

    def __repr__(self):
        return f'<Listing {self.title}>'


class Note(db.Model):
    __tablename__ = 'notes'

    id          = db.Column(db.Integer,    primary_key=True)
    author_id   = db.Column(db.Integer,    db.ForeignKey('users.id'), nullable=False)
    title       = db.Column(db.String(150), nullable=False)
    unit_code   = db.Column(db.String(16),  nullable=False)
    semester    = db.Column(db.String(50),  default='')
    description = db.Column(db.Text,       default='')
    upvotes     = db.Column(db.Integer,    default=0)
    created_at  = db.Column(db.DateTime,   server_default=db.func.now())

    author = db.relationship('User', back_populates='notes')

    def __repr__(self):
        return f'<Note {self.title}>'


class StudySession(db.Model):
    """Study group / session. Named StudySession to avoid conflict with Flask's session."""
    __tablename__ = 'sessions'

    id            = db.Column(db.Integer,    primary_key=True)
    host_id       = db.Column(db.Integer,    db.ForeignKey('users.id'), nullable=False)
    title         = db.Column(db.String(150), nullable=False)
    unit_code     = db.Column(db.String(16),  nullable=False)
    location      = db.Column(db.String(200), default='')
    session_date  = db.Column(db.DateTime)
    max_attendees = db.Column(db.Integer,    default=10)
    description   = db.Column(db.Text,       default='')
    created_at    = db.Column(db.DateTime,   server_default=db.func.now())

    host  = db.relationship('User',        back_populates='hosted_sessions')
    rsvps = db.relationship('SessionRSVP', back_populates='session', lazy='dynamic',
                             cascade='all, delete-orphan')

    def attendee_count(self):
        return self.rsvps.count()

    def __repr__(self):
        return f'<StudySession {self.title}>'


class SessionRSVP(db.Model):
    __tablename__ = 'session_rsvps'

    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'),    primary_key=True)

    session = db.relationship('StudySession', back_populates='rsvps')
    user    = db.relationship('User',         back_populates='rsvps')

    def __repr__(self):
        return f'<SessionRSVP session={self.session_id} user={self.user_id}>'


class Bounty(db.Model):
    __tablename__ = 'bounties'

    id          = db.Column(db.Integer,    primary_key=True)
    poster_id   = db.Column(db.Integer,    db.ForeignKey('users.id'), nullable=False)
    title       = db.Column(db.String(150), nullable=False)
    unit_code   = db.Column(db.String(16),  default='')
    reward      = db.Column(db.Float,      default=0)
    description = db.Column(db.Text,       default='')
    created_at  = db.Column(db.DateTime,   server_default=db.func.now())

    poster = db.relationship('User', back_populates='bounties')

    def __repr__(self):
        return f'<Bounty {self.title}>'


class SavedListing(db.Model):
    __tablename__ = 'saved_listings'

    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'),    primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), primary_key=True)

    user    = db.relationship('User',    back_populates='saved_listings')
    listing = db.relationship('Listing', back_populates='saved_by')

    def __repr__(self):
        return f'<SavedListing user={self.user_id} listing={self.listing_id}>'


class Rating(db.Model):
    __tablename__ = 'ratings'

    id         = db.Column(db.Integer, primary_key=True)
    rater_id   = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    rated_id   = db.Column(db.Integer, db.ForeignKey('users.id'),    nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    score      = db.Column(db.Integer, nullable=False)
    comment    = db.Column(db.Text,    default='')

    rater   = db.relationship('User',    foreign_keys=[rater_id],   back_populates='ratings_given')
    rated   = db.relationship('User',    foreign_keys=[rated_id],   back_populates='ratings_received')
    listing = db.relationship('Listing', back_populates='ratings')

    def __repr__(self):
        return f'<Rating {self.score} by user={self.rater_id}>'


class Message(db.Model):
    __tablename__ = 'messages'

    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body        = db.Column(db.Text,    nullable=False)
    created_at  = db.Column(db.DateTime, server_default=db.func.now())
    read        = db.Column(db.Integer, default=0)

    sender   = db.relationship('User', foreign_keys=[sender_id],   back_populates='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='received_messages')

    def __repr__(self):
        return f'<Message from={self.sender_id} to={self.receiver_id}>'

"""
Business logic extracted from routes.
Each function validates, persists, and returns a result or raises ValueError.
"""
import datetime
from app.extensions import db
from app.models import (Listing, Note, StudySession, SessionRSVP,
                        Bounty, Rating, Message, User)
from validators import (validate_required_text, validate_optional_text,
                        validate_unit_code, validate_price, validate_positive_int,
                        validate_session_date, validate_choice, LISTING_CONDITIONS)


def create_listing(seller_id, form):
    title,       err = validate_required_text(form.get('title'), 'Title', max_len=100)
    if err: raise ValueError(err)
    unit_code,   err = validate_unit_code(form.get('unit_code'))
    if err: raise ValueError(err)
    price,       err = validate_price(form.get('price'))
    if err: raise ValueError(err)
    condition,   err = validate_choice(form.get('condition'), 'Condition', LISTING_CONDITIONS)
    if err: raise ValueError(err)
    description, err = validate_optional_text(form.get('description'), 'Description', max_len=2000)
    if err: raise ValueError(err)

    listing = Listing(seller_id=seller_id, title=title, unit_code=unit_code,
                      price=price, condition=condition, description=description)
    db.session.add(listing)
    db.session.commit()
    return listing


def create_note(author_id, form):
    title,       err = validate_required_text(form.get('title'), 'Title', max_len=150)
    if err: raise ValueError(err)
    unit_code,   err = validate_unit_code(form.get('unit_code'))
    if err: raise ValueError(err)
    semester,    err = validate_optional_text(form.get('semester'), 'Semester', max_len=50)
    if err: raise ValueError(err)
    description, err = validate_optional_text(form.get('description'), 'Description', max_len=2000)
    if err: raise ValueError(err)

    note = Note(author_id=author_id, title=title, unit_code=unit_code,
                semester=semester, description=description)
    db.session.add(note)
    db.session.commit()
    return note


def create_study_session(host_id, form):
    title,         err = validate_required_text(form.get('title'), 'Title', max_len=150)
    if err: raise ValueError(err)
    unit_code,     err = validate_unit_code(form.get('unit_code'))
    if err: raise ValueError(err)
    location,      err = validate_optional_text(form.get('location'), 'Location', max_len=200)
    if err: raise ValueError(err)
    session_date_str, err = validate_session_date(form.get('session_date'))
    if err: raise ValueError(err)
    try:
        session_date = datetime.datetime.strptime(session_date_str, '%Y-%m-%dT%H:%M')
    except (ValueError, TypeError):
        raise ValueError('Session date must be a valid date and time.')
    max_attendees, err = validate_positive_int(form.get('max_attendees', '10'),
                                               'Max attendees', min_value=2, max_value=200)
    if err: raise ValueError(err)
    description,   err = validate_optional_text(form.get('description'), 'Description', max_len=2000)
    if err: raise ValueError(err)

    study_session = StudySession(host_id=host_id, title=title, unit_code=unit_code,
                                 location=location, session_date=session_date,
                                 max_attendees=max_attendees, description=description)
    db.session.add(study_session)
    db.session.commit()
    return study_session


def rsvp_session(session_id, user_id):
    """Returns True if RSVP created, False if already exists."""
    existing = SessionRSVP.query.get((session_id, user_id))
    if existing:
        return False
    rsvp = SessionRSVP(session_id=session_id, user_id=user_id)
    db.session.add(rsvp)
    db.session.commit()
    return True


def cancel_rsvp(session_id, user_id):
    rsvp = SessionRSVP.query.get((session_id, user_id))
    if rsvp:
        db.session.delete(rsvp)
        db.session.commit()


def create_bounty(poster_id, form):
    title,       err = validate_required_text(form.get('title'), 'Title', max_len=150)
    if err: raise ValueError(err)
    description, err = validate_optional_text(form.get('description'), 'Description', max_len=2000)
    if err: raise ValueError(err)
    reward,      err = validate_price(form.get('reward'), field_label='Reward', allow_zero=True)
    if err: raise ValueError(err)

    raw_unit = (form.get('unit_code') or '').strip()
    if raw_unit:
        unit_code, err = validate_unit_code(raw_unit)
        if err: raise ValueError(err)
    else:
        unit_code = ''

    bounty = Bounty(poster_id=poster_id, title=title, unit_code=unit_code,
                    reward=reward, description=description)
    db.session.add(bounty)
    db.session.commit()
    return bounty


def submit_rating(rater_id, listing_id, score, comment):
    """Returns the new Rating, or raises ValueError on business-rule violations."""
    listing = Listing.query.get(listing_id)
    if not listing:
        raise ValueError('Listing not found.')
    if listing.seller_id == rater_id:
        raise ValueError('You cannot rate yourself.')
    if Rating.query.filter_by(rater_id=rater_id, listing_id=listing_id).first():
        raise ValueError('You have already rated this transaction.')

    rating = Rating(rater_id=rater_id, rated_id=listing.seller_id,
                    listing_id=listing_id, score=score, comment=comment)
    db.session.add(rating)

    seller = User.query.get(listing.seller_id)
    seller.rating_sum   += score
    seller.rating_count += 1

    db.session.commit()
    return rating


def send_message(sender_id, receiver_id, body):
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, body=body)
    db.session.add(msg)
    db.session.commit()
    return msg

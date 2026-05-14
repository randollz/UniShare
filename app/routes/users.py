from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (User, Listing, Note, SavedListing, StudySession, Bounty,
                        Post, PostLike, PostComment, SessionRSVP)

users_bp = Blueprint('users', __name__)


@users_bp.route('/profile/<int:user_id>')
def profile(user_id):
    profile_user = User.query.get_or_404(user_id)
    listings   = Listing.query.filter_by(seller_id=user_id).order_by(Listing.created_at.desc()).all()
    notes_list = Note.query.filter_by(author_id=user_id).order_by(Note.upvotes.desc()).all()
    return render_template('profiles.html',
                           profile_user=profile_user,
                           listings=listings,
                           notes=notes_list,
                           avg_rating=profile_user.get_average_rating())


@users_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name  = request.form.get('last_name',  current_user.last_name)
        current_user.bio        = request.form.get('bio',        current_user.bio or '')
        db.session.commit()
        flash('Settings saved.', 'success')
        return redirect(url_for('users.settings'))
    return render_template('settings.html', user=current_user)


@users_bp.route('/api/search_users')
@login_required
def search_users():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    like  = f'%{q}%'
    users = (User.query
             .filter(
                 (User.first_name.like(like)) |
                 (User.last_name.like(like))  |
                 (User.email.like(like))
             )
             .filter(User.id != current_user.id)
             .limit(10)
             .all())
    return jsonify([
        {'id': u.id, 'name': f'{u.first_name} {u.last_name}', 'email': u.email}
        for u in users
    ])


@users_bp.route('/activity')
@login_required
def activity():
    import datetime as dt
    uid = current_user.id

    events = []

    for p in Post.query.filter_by(author_id=uid).order_by(Post.created_at.desc()).limit(30):
        events.append({
            'type': 'post', 'time': p.created_at,
            'label': 'You shared a post',
            'excerpt': p.body[:120] + ('…' if len(p.body) > 120 else ''),
            'link': url_for('feed.dashboard'),
            'badge': p.post_type,
        })

    for c in PostComment.query.filter_by(author_id=uid).order_by(PostComment.created_at.desc()).limit(30):
        post = Post.query.get(c.post_id)
        author_name = f'{post.author.first_name} {post.author.last_name}' if post else 'someone'
        events.append({
            'type': 'comment', 'time': c.created_at,
            'label': f'You commented on {author_name}\'s post',
            'excerpt': c.body[:120] + ('…' if len(c.body) > 120 else ''),
            'link': url_for('feed.dashboard'),
            'badge': None,
        })

    for lk in PostLike.query.filter_by(user_id=uid).order_by(PostLike.created_at.desc()).limit(30):
        post = Post.query.get(lk.post_id)
        if post:
            author_name = f'{post.author.first_name} {post.author.last_name}'
            events.append({
                'type': 'like', 'time': lk.created_at,
                'label': f'You liked {author_name}\'s post',
                'excerpt': post.body[:80] + ('…' if len(post.body) > 80 else ''),
                'link': url_for('feed.dashboard'),
                'badge': None,
            })

    for rsvp in SessionRSVP.query.filter_by(user_id=uid).all():
        sess = StudySession.query.get(rsvp.session_id)
        if sess:
            events.append({
                'type': 'rsvp', 'time': sess.created_at,
                'label': f'You joined "{sess.title}"',
                'excerpt': f'{sess.unit_code} · {sess.location}',
                'link': url_for('sessions.study_sessions'),
                'badge': None,
            })

    events.sort(key=lambda e: e['time'] or dt.datetime.min, reverse=True)
    events = events[:60]

    now = dt.datetime.now(dt.timezone.utc)
    for e in events:
        t = e['time']
        if t is None:
            e['time_str'] = 'some time ago'
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        diff = now - t
        secs = int(diff.total_seconds())
        if secs < 60:
            e['time_str'] = 'just now'
        elif secs < 3600:
            e['time_str'] = f'{secs // 60}m ago'
        elif secs < 86400:
            e['time_str'] = f'{secs // 3600}h ago'
        else:
            e['time_str'] = f'{secs // 86400}d ago'

    return render_template('activity.html', events=events)


@users_bp.route('/my-listings')
@login_required
def my_listings_page():
    my_listings = (Listing.query
                   .filter_by(seller_id=current_user.id)
                   .order_by(Listing.created_at.desc())
                   .all())
    saved = (SavedListing.query
             .filter_by(user_id=current_user.id)
             .order_by(SavedListing.listing_id.desc())
             .all())
    saved_listings = [sl.listing for sl in saved]
    my_sessions = (StudySession.query
                   .filter_by(host_id=current_user.id)
                   .order_by(StudySession.session_date.desc())
                   .all())
    my_bounties = (Bounty.query
                   .filter_by(poster_id=current_user.id)
                   .order_by(Bounty.created_at.desc())
                   .all())
    return render_template('my_listings.html',
                           my_listings=my_listings,
                           saved_listings=saved_listings,
                           my_sessions=my_sessions,
                           my_bounties=my_bounties)

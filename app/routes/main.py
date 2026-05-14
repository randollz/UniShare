from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required

from app.extensions import db
from app.models import User, Listing, Note, StudySession, Bounty

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    stats = {
        'users':    User.query.count(),
        'listings': Listing.query.count(),
        'notes':    Note.query.count(),
    }
    recent_listings = Listing.query.order_by(Listing.created_at.desc()).limit(3).all()
    top_users       = User.query.order_by(User.xp.desc()).limit(5).all()

    from sqlalchemy import func
    notes_by_unit = (
        db.session.query(Note.unit_code, func.count(Note.id).label('count'))
        .group_by(Note.unit_code)
        .order_by(func.count(Note.id).desc())
        .limit(6)
        .all()
    )

    return render_template('index.html',
                           stats=stats,
                           recent_listings=recent_listings,
                           notes_by_unit=notes_by_unit,
                           top_users=top_users)


@main_bp.route('/about')
def about():
    return redirect(url_for('main.index'))


@main_bp.route('/privacy')
def privacy():
    return redirect(url_for('main.index'))


@main_bp.route('/contact')
def contact():
    return redirect(url_for('main.index'))


@main_bp.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.xp.desc()).all()
    return render_template('leaderboard.html', users=users)


@main_bp.route('/search')
@login_required
def search():
    from sqlalchemy import or_
    q = request.args.get('q', '').strip()
    results = {'listings': [], 'notes': [], 'sessions': [], 'bounties': []}
    if len(q) >= 2:
        like = f'%{q}%'
        results['listings'] = Listing.query.filter(
            or_(Listing.title.ilike(like), Listing.description.ilike(like))
        ).order_by(Listing.created_at.desc()).limit(10).all()
        results['notes'] = Note.query.filter(
            or_(Note.title.ilike(like), Note.description.ilike(like))
        ).order_by(Note.created_at.desc()).limit(10).all()
        results['sessions'] = StudySession.query.filter(
            or_(StudySession.title.ilike(like), StudySession.unit_code.ilike(like))
        ).order_by(StudySession.session_date.desc()).limit(10).all()
        results['bounties'] = Bounty.query.filter(
            or_(Bounty.title.ilike(like), Bounty.description.ilike(like))
        ).order_by(Bounty.created_at.desc()).limit(10).all()
    total = sum(len(v) for v in results.values())
    return render_template('search.html', q=q, results=results, total=total)

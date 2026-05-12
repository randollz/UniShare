import os
import uuid

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import StudySession, SessionRSVP, SessionComment
from app import controllers

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/sessions')
def study_sessions():
    unit = request.args.get('unit', '').strip().upper()

    from app.models import User
    query = StudySession.query.join(User, User.id == StudySession.host_id)
    if unit:
        query = query.filter(StudySession.unit_code == unit)
    sessions_list = query.order_by(StudySession.session_date.asc()).all()

    for s in sessions_list:
        s.rsvp_count = s.attendee_count()

    joined_ids = set()
    if current_user.is_authenticated:
        joined_ids = {
            r.session_id
            for r in SessionRSVP.query.filter_by(user_id=current_user.id).all()
        }

    return render_template('sessions.html',
                           sessions=sessions_list,
                           joined_ids=joined_ids,
                           unit=unit)


@sessions_bp.route('/create_session', methods=['GET', 'POST'])
@login_required
def create_session():
    if request.method == 'POST':
        try:
            study_session = controllers.create_study_session(current_user.id, request.form)
            img = request.files.get('image')
            if img and img.filename:
                if img.mimetype in {'image/jpeg', 'image/png'}:
                    data = img.read()
                    if len(data) <= 10 * 1024 * 1024:
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'sessions')
                        os.makedirs(upload_dir, exist_ok=True)
                        fname = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                        with open(os.path.join(upload_dir, fname), 'wb') as f:
                            f.write(data)
                        study_session.image_path = f"uploads/sessions/{fname}"
                        study_session.image_name = img.filename
                        db.session.commit()
            flash('Study session posted!', 'success')
            return redirect(url_for('sessions.study_sessions'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('create_session.html', errors={}, form=request.form)


@sessions_bp.route('/rsvp_session/<int:session_id>', methods=['POST'])
@login_required
def rsvp_session(session_id):
    created = controllers.rsvp_session(session_id, current_user.id)
    if created == 'full':
        flash("That session is already full.", 'error')
    elif created:
        flash("You're in!", 'success')
    else:
        flash("You're already signed up for that session.", 'info')
    return redirect(url_for('sessions.study_sessions'))


@sessions_bp.route('/delete_session/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    s = StudySession.query.filter_by(id=session_id, host_id=current_user.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()
        flash('Session deleted.', 'success')
    return redirect(url_for('sessions.study_sessions'))


@sessions_bp.route('/cancel_rsvp/<int:session_id>', methods=['POST'])
@login_required
def cancel_rsvp(session_id):
    controllers.cancel_rsvp(session_id, current_user.id)
    flash('RSVP cancelled.', 'info')
    return redirect(url_for('sessions.study_sessions'))


@sessions_bp.route('/sessions/<int:session_id>')
@login_required
def view_session(session_id):
    study_session = StudySession.query.get_or_404(session_id)
    is_host = study_session.host_id == current_user.id
    is_rsvped = SessionRSVP.query.get((session_id, current_user.id)) is not None
    return render_template('session_detail.html',
                           session=study_session,
                           is_host=is_host,
                           is_rsvped=is_rsvped)


@sessions_bp.route('/sessions/<int:session_id>/comment', methods=['POST'])
@login_required
def session_comment(session_id):
    study_session = StudySession.query.get_or_404(session_id)
    body = (request.json or {}).get('body', '').strip()
    if not body or len(body) > 500:
        return jsonify({'error': 'invalid'}), 400
    comment = SessionComment(session_id=session_id, author_id=current_user.id, body=body)
    db.session.add(comment)
    study_session.comments_count += 1
    db.session.commit()
    return jsonify({
        'id':       comment.id,
        'body':     comment.body,
        'author':   f'{current_user.first_name} {current_user.last_name}',
        'initials': f'{current_user.first_name[0]}{current_user.last_name[0]}',
        'time':     'just now',
        'count':    study_session.comments_count,
    })


@sessions_bp.route('/session-comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_session_comment(comment_id):
    comment = SessionComment.query.get_or_404(comment_id)
    if comment.author_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403
    comment.session.comments_count = max(0, comment.session.comments_count - 1)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'ok': True})

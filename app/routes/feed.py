import os
import uuid

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (Listing, SavedListing, StudySession, SessionRSVP,
                        Post, PostLike, PostComment, User)

feed_bp = Blueprint('feed', __name__)

VALID_POST_TYPES = {'general', 'event', 'news', 'resource'}
ALLOWED_IMAGE_MIMES = {'image/jpeg', 'image/png'}
MAX_POST_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@feed_bp.route('/dashboard')
@login_required
def dashboard():
    my_listings = (Listing.query
                   .filter_by(seller_id=current_user.id)
                   .order_by(Listing.created_at.desc())
                   .all())

    saved = (db.session.query(Listing)
             .join(SavedListing, SavedListing.listing_id == Listing.id)
             .filter(SavedListing.user_id == current_user.id)
             .all())

    my_sessions = (db.session.query(StudySession)
                   .join(SessionRSVP, SessionRSVP.session_id == StudySession.id)
                   .filter(SessionRSVP.user_id == current_user.id)
                   .order_by(StudySession.session_date.asc())
                   .all())

    top_users = User.query.order_by(User.xp.desc()).limit(5).all()

    page = request.args.get('page', 1, type=int)
    posts = (Post.query
             .order_by(Post.created_at.desc())
             .paginate(page=page, per_page=20, error_out=False))

    liked_ids = {
        pl.post_id for pl in
        PostLike.query.filter_by(user_id=current_user.id).all()
    }

    return render_template('dashboard.html',
                           user=current_user,
                           my_listings=my_listings,
                           saved=saved,
                           my_sessions=my_sessions,
                           top_users=top_users,
                           posts=posts,
                           liked_ids=liked_ids)


@feed_bp.route('/feed')
@login_required
def feed():
    return redirect(url_for('feed.dashboard'))


@feed_bp.route('/feed/create', methods=['POST'])
@login_required
def feed_create():
    body      = request.form.get('body', '').strip()
    post_type = request.form.get('post_type', 'general').strip()
    if not body:
        flash('Post body cannot be empty.', 'error')
        return redirect(url_for('feed.dashboard'))
    if post_type not in VALID_POST_TYPES:
        post_type = 'general'

    post = Post(author_id=current_user.id, body=body, post_type=post_type)

    attachment = request.files.get('attachment')
    if attachment and attachment.filename:
        if attachment.mimetype not in ALLOWED_IMAGE_MIMES:
            flash('Only JPG and PNG images are supported.', 'error')
            return redirect(url_for('feed.dashboard'))
        data = attachment.read()
        if len(data) > MAX_POST_IMAGE_BYTES:
            flash('Image must be under 10 MB.', 'error')
            return redirect(url_for('feed.dashboard'))
        filename = f"{uuid.uuid4().hex}_{secure_filename(attachment.filename)}"
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'posts')
        os.makedirs(upload_dir, exist_ok=True)
        with open(os.path.join(upload_dir, filename), 'wb') as f:
            f.write(data)
        post.image_path = f"uploads/posts/{filename}"
        post.image_name = attachment.filename

    elif (link_url := request.form.get('link_url', '').strip()):
        if link_url.startswith(('http://', 'https://')):
            post.link_url = link_url
            try:
                import requests as _requests
                from bs4 import BeautifulSoup
                resp = _requests.get(link_url, timeout=3,
                                    headers={'User-Agent': 'UniShare/1.0'})
                soup = BeautifulSoup(resp.text, 'html.parser')

                def _og(prop):
                    tag = soup.find('meta', property=f'og:{prop}')
                    if tag:
                        return (tag.get('content') or '').strip() or None
                    return None

                post.link_title       = _og('title') or (soup.title.string.strip() if soup.title else None)
                post.link_description = _og('description')
                post.link_image_url   = _og('image')
            except Exception:
                pass

    db.session.add(post)
    current_user.xp += 5
    db.session.commit()
    flash('Post shared!', 'success')
    return redirect(url_for('feed.dashboard'))


@feed_bp.route('/feed/<int:post_id>/like', methods=['POST'])
@login_required
def feed_like(post_id):
    post = Post.query.get_or_404(post_id)
    existing = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
        post.likes_count = max(0, post.likes_count - 1)
        liked = False
    else:
        db.session.add(PostLike(user_id=current_user.id, post_id=post_id))
        post.likes_count += 1
        liked = True
    db.session.commit()
    return jsonify({'liked': liked, 'count': post.likes_count})


@feed_bp.route('/feed/<int:post_id>/comment', methods=['POST'])
@login_required
def feed_comment(post_id):
    post = Post.query.get_or_404(post_id)
    body = (request.json or {}).get('body', '').strip()
    if not body or len(body) > 500:
        return jsonify({'error': 'invalid'}), 400
    comment = PostComment(post_id=post_id, author_id=current_user.id, body=body)
    db.session.add(comment)
    post.comments_count += 1
    db.session.commit()
    return jsonify({
        'id':       comment.id,
        'body':     comment.body,
        'author':   f'{current_user.first_name} {current_user.last_name}',
        'initials': f'{current_user.first_name[0]}{current_user.last_name[0]}',
        'time':     'just now',
        'count':    post.comments_count,
    })


@feed_bp.route('/feed/<int:post_id>/delete', methods=['POST'])
@login_required
def feed_delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted.', 'success')
    return redirect(url_for('feed.dashboard'))

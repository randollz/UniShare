import os
import uuid

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, Response, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Bounty, BountyComment
from app import controllers

bounties_bp = Blueprint('bounties', __name__)


@bounties_bp.route('/bounties')
def bounties():
    bounties_list = Bounty.query.order_by(Bounty.created_at.desc()).all()
    return render_template('bounties.html', bounties=bounties_list)


@bounties_bp.route('/create_bounty', methods=['GET', 'POST'])
@login_required
def create_bounty():
    if request.method == 'POST':
        try:
            bounty = controllers.create_bounty(current_user.id, request.form)
            img = request.files.get('image')
            if img and img.filename:
                if img.mimetype in {'image/jpeg', 'image/png'}:
                    data = img.read()
                    if len(data) <= 10 * 1024 * 1024:
                        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'bounties')
                        os.makedirs(upload_dir, exist_ok=True)
                        fname = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                        with open(os.path.join(upload_dir, fname), 'wb') as f:
                            f.write(data)
                        bounty.image_path = f"uploads/bounties/{fname}"
                        bounty.image_name = img.filename
                        db.session.commit()
            flash('Bounty posted!', 'success')
            return redirect(url_for('bounties.bounties'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('create_bounty.html', errors={}, form=request.form)


@bounties_bp.route('/bounties/<int:bounty_id>/claim', methods=['POST'])
@login_required
def claim_bounty(bounty_id):
    bounty = Bounty.query.get_or_404(bounty_id)
    if bounty.poster_id == current_user.id:
        flash("You can't claim your own bounty.", 'error')
    elif bounty.status != 'open':
        flash('This bounty is no longer open.', 'error')
    else:
        bounty.status = 'claimed'
        bounty.claimer_id = current_user.id
        db.session.commit()
        flash('Bounty claimed!', 'success')
    return redirect(url_for('bounties.view_bounty', bounty_id=bounty_id))


@bounties_bp.route('/bounties/<int:bounty_id>/delete', methods=['POST'])
@login_required
def delete_bounty(bounty_id):
    bounty = Bounty.query.filter_by(id=bounty_id, poster_id=current_user.id).first()
    if bounty and bounty.status == 'open':
        db.session.delete(bounty)
        db.session.commit()
        flash('Bounty deleted.', 'success')
    return redirect(url_for('users.my_listings_page'))


@bounties_bp.route('/bounties/<int:bounty_id>')
def view_bounty(bounty_id):
    bounty = Bounty.query.get_or_404(bounty_id)
    return render_template('bounty_detail.html', bounty=bounty)


@bounties_bp.route('/bounties/<int:bounty_id>/download')
def download_bounty(bounty_id):
    bounty = Bounty.query.get_or_404(bounty_id)
    unit_line = bounty.unit_code if bounty.unit_code else 'General'
    content = (
        f"{bounty.title}\n\n"
        f"Unit: {unit_line}\n"
        f"Reward: ${bounty.reward:.2f}\n\n"
        f"{bounty.description}"
    )
    return Response(content, mimetype='text/plain',
                    headers={'Content-Disposition': f'attachment; filename=bounty-{bounty_id}.txt'})


@bounties_bp.route('/bounties/<int:bounty_id>/comment', methods=['POST'])
@login_required
def bounty_comment(bounty_id):
    bounty = Bounty.query.get_or_404(bounty_id)
    body = (request.json or {}).get('body', '').strip()
    if not body or len(body) > 500:
        return jsonify({'error': 'invalid'}), 400
    comment = BountyComment(bounty_id=bounty_id, author_id=current_user.id, body=body)
    db.session.add(comment)
    bounty.comments_count += 1
    db.session.commit()
    return jsonify({
        'id':       comment.id,
        'body':     comment.body,
        'author':   f'{current_user.first_name} {current_user.last_name}',
        'initials': f'{current_user.first_name[0]}{current_user.last_name[0]}',
        'time':     'just now',
        'count':    bounty.comments_count,
    })


@bounties_bp.route('/bounty-comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_bounty_comment(comment_id):
    comment = BountyComment.query.get_or_404(comment_id)
    if comment.author_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403
    comment.bounty.comments_count = max(0, comment.bounty.comments_count - 1)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'ok': True})

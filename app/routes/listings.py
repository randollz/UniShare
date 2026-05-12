import os
import uuid

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, Response, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Listing, SavedListing, ListingComment, ListingImage
from app import controllers
from app.validators import LISTING_CONDITIONS

listings_bp = Blueprint('listings', __name__)


@listings_bp.route('/marketplace')
def marketplace():
    q         = request.args.get('q', '').strip()
    unit      = request.args.get('unit', '').strip().upper()
    condition = request.args.get('condition', '').strip()
    sort      = request.args.get('sort', '').strip()

    from app.models import User
    query = Listing.query.join(User, User.id == Listing.seller_id)

    if q:
        like = f'%{q}%'
        query = query.filter(
            (Listing.title.like(like)) | (Listing.description.like(like))
        )
    if unit:
        query = query.filter(Listing.unit_code == unit)
    if condition:
        query = query.filter(Listing.condition == condition)

    if sort == 'price_asc':
        query = query.order_by(Listing.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Listing.price.desc())
    else:
        query = query.order_by(Listing.created_at.desc())

    listings = query.all()

    saved_ids = set()
    if current_user.is_authenticated:
        saved_ids = {
            sl.listing_id
            for sl in SavedListing.query.filter_by(user_id=current_user.id).all()
        }

    recent_listings = (Listing.query
                       .order_by(Listing.created_at.desc())
                       .limit(3).all())

    from sqlalchemy import func
    price_stats = (
        db.session.query(
            db.func.substr(Listing.unit_code, 1, 4).label('unit_prefix'),
            db.func.round(db.func.avg(Listing.price), 0).label('avg_price'),
            func.count(Listing.id).label('n'),
        )
        .group_by('unit_prefix')
        .order_by(func.count(Listing.id).desc())
        .limit(5)
        .all()
    )

    active_count = Listing.query.count()

    return render_template('marketplace.html',
                           listings=listings,
                           saved_ids=saved_ids,
                           recent_listings=recent_listings,
                           price_stats=price_stats,
                           active_count=active_count,
                           q=q, unit=unit, condition=condition, sort=sort)


@listings_bp.route('/create_listing', methods=['GET', 'POST'])
@login_required
def create_listing():
    if request.method == 'POST':
        try:
            listing = controllers.create_listing(current_user.id, request.form)
            images = request.files.getlist('images[]')
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'listings')
            os.makedirs(upload_dir, exist_ok=True)
            order = 0
            for img in images[:5]:
                if not img or not img.filename:
                    continue
                if img.mimetype not in {'image/jpeg', 'image/png'}:
                    continue
                data = img.read()
                if len(data) > 10 * 1024 * 1024:
                    continue
                fname = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                with open(os.path.join(upload_dir, fname), 'wb') as f:
                    f.write(data)
                db.session.add(ListingImage(
                    listing_id=listing.id,
                    file_path=f"uploads/listings/{fname}",
                    file_name=img.filename,
                    display_order=order,
                ))
                order += 1
            db.session.commit()
            flash('Listing posted!', 'success')
            return redirect(url_for('listings.marketplace'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('create_listing.html',
                           errors={}, form=request.form,
                           conditions=LISTING_CONDITIONS)


@listings_bp.route('/delete_listing/<int:listing_id>', methods=['POST'])
@login_required
def delete_listing(listing_id):
    listing = Listing.query.filter_by(id=listing_id, seller_id=current_user.id).first()
    if listing:
        db.session.delete(listing)
        db.session.commit()
    return redirect(url_for('feed.dashboard'))


@listings_bp.route('/save_listing/<int:listing_id>', methods=['POST'])
@login_required
def save_listing(listing_id):
    if not SavedListing.query.get((current_user.id, listing_id)):
        db.session.add(SavedListing(user_id=current_user.id, listing_id=listing_id))
        db.session.commit()
    return redirect(url_for('listings.marketplace'))


@listings_bp.route('/unsave_listing/<int:listing_id>', methods=['POST'])
@login_required
def unsave_listing(listing_id):
    sl = SavedListing.query.get((current_user.id, listing_id))
    if sl:
        db.session.delete(sl)
        db.session.commit()
    return redirect(url_for('listings.marketplace'))


@listings_bp.route('/listings/<int:listing_id>')
def view_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    return render_template('listing_detail.html', listing=listing)


@listings_bp.route('/listings/<int:listing_id>/download')
def download_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    content = (
        f"{listing.title}\n\n"
        f"Unit: {listing.unit_code}\n"
        f"Price: ${listing.price:.2f}\n"
        f"Condition: {listing.condition}\n\n"
        f"{listing.description}"
    )
    return Response(content, mimetype='text/plain',
                    headers={'Content-Disposition': f'attachment; filename=listing-{listing_id}.txt'})


@listings_bp.route('/listings/<int:listing_id>/comment', methods=['POST'])
@login_required
def listing_comment(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    body = (request.json or {}).get('body', '').strip()
    if not body or len(body) > 500:
        return jsonify({'error': 'invalid'}), 400
    comment = ListingComment(listing_id=listing_id, author_id=current_user.id, body=body)
    db.session.add(comment)
    listing.comments_count += 1
    db.session.commit()
    return jsonify({
        'id':       comment.id,
        'body':     comment.body,
        'author':   f'{current_user.first_name} {current_user.last_name}',
        'initials': f'{current_user.first_name[0]}{current_user.last_name[0]}',
        'time':     'just now',
        'count':    listing.comments_count,
    })


@listings_bp.route('/listing-comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_listing_comment(comment_id):
    comment = ListingComment.query.get_or_404(comment_id)
    if comment.author_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403
    comment.listing.comments_count = max(0, comment.listing.comments_count - 1)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'ok': True})


@listings_bp.route('/rate_user/<int:listing_id>', methods=['POST'])
@login_required
def rate_user(listing_id):
    try:
        score   = int(request.form.get('score', 5))
        comment = request.form.get('comment', '').strip()
        controllers.submit_rating(current_user.id, listing_id, score, comment)
        flash('Rating submitted!', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('listings.marketplace'))

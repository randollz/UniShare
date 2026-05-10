import os
import uuid

from flask import (render_template, request, redirect,
                   url_for, session, flash, jsonify, Response, send_from_directory, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (User, Listing, Note, StudySession, SessionRSVP,
                        Bounty, SavedListing, SavedNote, Rating, Message, Post, PostLike, PostComment,
                        ListingImage, ListingComment, BountyComment, SessionComment)
from app import controllers
from validators import LISTING_CONDITIONS


def register_routes(app):

    # ── Context processors ──────────────────────────────────────

    @app.context_processor
    def inject_globals():
        unread = 0
        if current_user.is_authenticated:
            unread = Message.query.filter_by(
                receiver_id=current_user.id, read=0
            ).count()
        user = current_user if current_user.is_authenticated else None
        return {'unread_count': unread, 'current_user': user}

    # ── Error handlers ──────────────────────────────────────────

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # ── Auth ────────────────────────────────────────────────────

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'login':
                email    = request.form.get('email', '').strip().lower()
                password = request.form.get('password', '')
                user = User.query.filter_by(email=email).first()
                if user and user.check_password(password):
                    login_user(user)
                    return redirect(url_for('dashboard'))
                flash('Invalid email or password.', 'error')

            elif action == 'register':
                first_name = request.form.get('first_name', '').strip()
                last_name  = request.form.get('last_name', '').strip()
                email      = request.form.get('email', '').strip().lower()
                password   = request.form.get('password', '')
                if User.query.filter_by(email=email).first():
                    flash('An account with that email already exists.', 'error')
                else:
                    user = User(first_name=first_name, last_name=last_name, email=email)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    login_user(user)
                    return redirect(url_for('dashboard'))

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

    # ── Index ───────────────────────────────────────────────────

    @app.route('/')
    def index():
        stats = {
            'users':    User.query.count(),
            'listings': Listing.query.count(),
            'notes':    Note.query.count(),
        }
        recent_listings = Listing.query.order_by(Listing.created_at.desc()).limit(3).all()
        top_users       = User.query.order_by(User.xp.desc()).limit(5).all()

        # Notes grouped by unit code
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

    # ── Dashboard ───────────────────────────────────────────────

    @app.route('/dashboard')
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

    # ── Marketplace ─────────────────────────────────────────────

    @app.route('/marketplace')
    def marketplace():
        q         = request.args.get('q', '').strip()
        unit      = request.args.get('unit', '').strip().upper()
        condition = request.args.get('condition', '').strip()
        sort      = request.args.get('sort', '').strip()

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

    @app.route('/create_listing', methods=['GET', 'POST'])
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
                return redirect(url_for('marketplace'))
            except ValueError as e:
                flash(str(e), 'error')
        return render_template('create_listing.html',
                               errors={}, form=request.form,
                               conditions=LISTING_CONDITIONS)

    @app.route('/delete_listing/<int:listing_id>', methods=['POST'])
    @login_required
    def delete_listing(listing_id):
        listing = Listing.query.filter_by(id=listing_id, seller_id=current_user.id).first()
        if listing:
            db.session.delete(listing)
            db.session.commit()
        return redirect(url_for('dashboard'))

    @app.route('/save_listing/<int:listing_id>', methods=['POST'])
    @login_required
    def save_listing(listing_id):
        if not SavedListing.query.get((current_user.id, listing_id)):
            db.session.add(SavedListing(user_id=current_user.id, listing_id=listing_id))
            db.session.commit()
        return redirect(url_for('marketplace'))

    @app.route('/unsave_listing/<int:listing_id>', methods=['POST'])
    @login_required
    def unsave_listing(listing_id):
        sl = SavedListing.query.get((current_user.id, listing_id))
        if sl:
            db.session.delete(sl)
            db.session.commit()
        return redirect(url_for('marketplace'))

    @app.route('/listings/<int:listing_id>')
    def view_listing(listing_id):
        listing = Listing.query.get_or_404(listing_id)
        return render_template('listing_detail.html', listing=listing)

    @app.route('/listings/<int:listing_id>/download')
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

    # ── Notes ───────────────────────────────────────────────────

    @app.route('/notes')
    def notes():
        q    = request.args.get('q', '').strip()
        unit = request.args.get('unit', '').strip().upper()

        query = Note.query
        if q:
            like = f'%{q}%'
            query = query.filter((Note.title.like(like)) | (Note.description.like(like)))
        if unit:
            query = query.filter(Note.unit_code == unit)
        notes_list = query.order_by(Note.upvotes.desc(), Note.created_at.desc()).all()

        return render_template('notes.html', notes=notes_list, q=q, unit=unit)

    @app.route('/create_note', methods=['GET', 'POST'])
    @login_required
    def create_note():
        if request.method == 'POST':
            try:
                note = controllers.create_note(current_user.id, request.form)
                attachment = request.files.get('attachment')
                if attachment and attachment.filename:
                    allowed_mimes = {'application/pdf', 'application/msword',
                                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                     'image/jpeg', 'image/png'}
                    mime = attachment.mimetype
                    if mime not in allowed_mimes:
                        flash('Unsupported file type. Please upload PDF, DOCX, JPG or PNG.', 'error')
                        return render_template('create_note.html', errors={}, form=request.form)
                    attachment.seek(0, 2)
                    if attachment.tell() > 10 * 1024 * 1024:
                        flash('File is too large (max 10 MB).', 'error')
                        return render_template('create_note.html', errors={}, form=request.form)
                    attachment.seek(0)
                    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'notes')
                    os.makedirs(upload_dir, exist_ok=True)
                    fname = f"{uuid.uuid4().hex}_{secure_filename(attachment.filename)}"
                    attachment.save(os.path.join(upload_dir, fname))
                    note.file_path = f"uploads/notes/{fname}"
                    note.file_name = attachment.filename
                    db.session.commit()
                flash('Notes shared!', 'success')
                return redirect(url_for('notes'))
            except ValueError as e:
                flash(str(e), 'error')
        return render_template('create_note.html', errors={}, form=request.form)

    @app.route('/upvote_note/<int:note_id>', methods=['POST'])
    @login_required
    def upvote_note(note_id):
        note = Note.query.get_or_404(note_id)
        note.upvotes += 1
        db.session.commit()
        return redirect(url_for('notes'))

    @app.route('/notes/<int:note_id>')
    def view_note(note_id):
        note = Note.query.get_or_404(note_id)
        is_saved = False
        if current_user and current_user.is_authenticated:
            is_saved = SavedNote.query.filter_by(
                user_id=current_user.id, note_id=note_id).first() is not None
        return render_template('note_detail.html', note=note, is_saved=is_saved)

    @app.route('/notes/<int:note_id>/download')
    def download_note(note_id):
        note = Note.query.get_or_404(note_id)
        if note.file_path:
            directory = os.path.join(current_app.static_folder, 'uploads', 'notes')
            filename = os.path.basename(note.file_path)
            return send_from_directory(directory, filename,
                                       as_attachment=True,
                                       download_name=note.file_name or filename)
        content = (
            f"{note.title}\n\n"
            f"Unit: {note.unit_code}\n"
            f"Semester: {note.semester}\n\n"
            f"{note.description}"
        )
        return Response(content, mimetype='text/plain',
                        headers={'Content-Disposition': f'attachment; filename=note-{note_id}.txt'})

    # ── Study Sessions ──────────────────────────────────────────

    @app.route('/sessions')
    def study_sessions():
        unit = request.args.get('unit', '').strip().upper()

        query = StudySession.query.join(User, User.id == StudySession.host_id)
        if unit:
            query = query.filter(StudySession.unit_code == unit)
        sessions_list = query.order_by(StudySession.session_date.asc()).all()

        # Annotate each session with RSVP count for the template
        for s in sessions_list:
            s.rsvp_count = s.attendee_count()

        # Mark which sessions the current user has RSVPed to
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

    @app.route('/create_session', methods=['GET', 'POST'])
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
                return redirect(url_for('study_sessions'))
            except ValueError as e:
                flash(str(e), 'error')
        return render_template('create_session.html', errors={}, form=request.form)

    @app.route('/rsvp_session/<int:session_id>', methods=['POST'])
    @login_required
    def rsvp_session(session_id):
        created = controllers.rsvp_session(session_id, current_user.id)
        if created:
            flash("You're in!", 'success')
        else:
            flash("You're already signed up for that session.", 'info')
        return redirect(url_for('study_sessions'))

    @app.route('/delete_session/<int:session_id>', methods=['POST'])
    @login_required
    def delete_session(session_id):
        s = StudySession.query.filter_by(id=session_id, host_id=current_user.id).first()
        if s:
            db.session.delete(s)
            db.session.commit()
            flash('Session deleted.', 'success')
        return redirect(url_for('study_sessions'))

    @app.route('/cancel_rsvp/<int:session_id>', methods=['POST'])
    @login_required
    def cancel_rsvp(session_id):
        controllers.cancel_rsvp(session_id, current_user.id)
        flash('RSVP cancelled.', 'info')
        return redirect(url_for('study_sessions'))

    @app.route('/sessions/<int:session_id>')
    @login_required
    def view_session(session_id):
        study_session = StudySession.query.get_or_404(session_id)
        is_host = study_session.host_id == current_user.id
        is_rsvped = SessionRSVP.query.get((session_id, current_user.id)) is not None
        return render_template('session_detail.html',
                               session=study_session,
                               is_host=is_host,
                               is_rsvped=is_rsvped)

    # ── Ratings ─────────────────────────────────────────────────

    @app.route('/rate_user/<int:listing_id>', methods=['POST'])
    @login_required
    def rate_user(listing_id):
        try:
            score   = int(request.form.get('score', 5))
            comment = request.form.get('comment', '').strip()
            controllers.submit_rating(current_user.id, listing_id, score, comment)
            flash('Rating submitted!', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        return redirect(url_for('marketplace'))

    # ── Leaderboard ─────────────────────────────────────────────

    @app.route('/leaderboard')
    def leaderboard():
        users = User.query.order_by(User.xp.desc()).all()
        return render_template('leaderboard.html', users=users)

    # ── Messages ────────────────────────────────────────────────

    @app.route('/messages')
    @login_required
    def messages():
        from sqlalchemy import or_, case
        contacts = (
            db.session.query(User)
            .join(Message, or_(
                (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
                (Message.receiver_id == User.id) & (Message.sender_id == current_user.id),
            ))
            .filter(User.id != current_user.id)
            .distinct()
            .order_by(User.first_name)
            .all()
        )
        return render_template('messages.html', contacts=contacts, active_user_id=None)

    @app.route('/messages/<int:other_id>')
    @login_required
    def messages_thread(other_id):
        # Mark incoming messages as read
        Message.query.filter_by(
            sender_id=other_id, receiver_id=current_user.id, read=0
        ).update({'read': 1})
        db.session.commit()

        from sqlalchemy import or_
        thread = (
            Message.query
            .filter(or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == other_id),
                (Message.sender_id == other_id) & (Message.receiver_id == current_user.id),
            ))
            .order_by(Message.created_at.asc())
            .all()
        )

        other_user = User.query.get_or_404(other_id)

        contacts = (
            db.session.query(User)
            .join(Message, or_(
                (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
                (Message.receiver_id == User.id) & (Message.sender_id == current_user.id),
            ))
            .filter(User.id != current_user.id)
            .distinct()
            .order_by(User.first_name)
            .all()
        )

        return render_template('messages.html',
                               contacts=contacts,
                               thread=thread,
                               other_user=other_user,
                               active_user_id=other_id)

    @app.route('/messages/<int:other_id>/send', methods=['POST'])
    @login_required
    def messages_send(other_id):
        body = (request.json.get('body', '').strip()
                if request.is_json else request.form.get('body', '').strip())
        if not body:
            return jsonify({'error': 'empty'}), 400
        controllers.send_message(current_user.id, other_id, body)
        return jsonify({'ok': True})

    @app.route('/messages/<int:other_id>/poll')
    @login_required
    def messages_poll(other_id):
        after_id = int(request.args.get('after', 0))
        from sqlalchemy import or_
        rows = (
            Message.query
            .filter(or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == other_id),
                (Message.sender_id == other_id) & (Message.receiver_id == current_user.id),
            ))
            .filter(Message.id > after_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        Message.query.filter(
            Message.sender_id == other_id,
            Message.receiver_id == current_user.id,
            Message.id > after_id
        ).update({'read': 1})
        db.session.commit()
        return jsonify([
            {'id': m.id, 'sender_id': m.sender_id, 'body': m.body,
             'created_at': str(m.created_at)}
            for m in rows
        ])

    @app.route('/api/messages/<int:other_id>/send', methods=['POST'])
    @login_required
    def api_messages_send(other_id):
        body = (request.json.get('body', '').strip()
                if request.is_json else request.form.get('body', '').strip())
        if not body:
            return jsonify({'error': 'empty'}), 400
        msg = controllers.send_message(current_user.id, other_id, body)
        return jsonify({
            'id':          msg.id,
            'body':        msg.body,
            'created_at':  str(msg.created_at),
            'sender_id':   current_user.id,
            'sender_name': f'{current_user.first_name} {current_user.last_name}',
        })

    @app.route('/api/messages/<int:other_id>/poll')
    @login_required
    def api_messages_poll(other_id):
        since = request.args.get('since', '1970-01-01 00:00:00')
        from sqlalchemy import or_
        rows = (
            Message.query
            .filter(or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == other_id),
                (Message.sender_id == other_id) & (Message.receiver_id == current_user.id),
            ))
            .filter(Message.created_at > since)
            .order_by(Message.created_at.asc())
            .all()
        )
        Message.query.filter(
            Message.sender_id == other_id,
            Message.receiver_id == current_user.id,
            Message.created_at > since
        ).update({'read': 1})
        db.session.commit()
        return jsonify([
            {'id': m.id, 'sender_id': m.sender_id, 'body': m.body,
             'created_at': str(m.created_at)}
            for m in rows
        ])

    # ── Bounties ────────────────────────────────────────────────

    @app.route('/bounties')
    def bounties():
        bounties_list = Bounty.query.order_by(Bounty.created_at.desc()).all()
        return render_template('bounties.html', bounties=bounties_list)

    @app.route('/create_bounty', methods=['GET', 'POST'])
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
                return redirect(url_for('bounties'))
            except ValueError as e:
                flash(str(e), 'error')
        return render_template('create_bounty.html', errors={}, form=request.form)

    @app.route('/bounties/<int:bounty_id>/claim', methods=['POST'])
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
        return redirect(url_for('view_bounty', bounty_id=bounty_id))

    @app.route('/bounties/<int:bounty_id>/delete', methods=['POST'])
    @login_required
    def delete_bounty(bounty_id):
        bounty = Bounty.query.filter_by(id=bounty_id, poster_id=current_user.id).first()
        if bounty and bounty.status == 'open':
            db.session.delete(bounty)
            db.session.commit()
            flash('Bounty deleted.', 'success')
        return redirect(url_for('my_listings_page'))

    @app.route('/bounties/<int:bounty_id>')
    def view_bounty(bounty_id):
        bounty = Bounty.query.get_or_404(bounty_id)
        return render_template('bounty_detail.html', bounty=bounty)

    @app.route('/bounties/<int:bounty_id>/download')
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

    # ── Profile ─────────────────────────────────────────────────

    @app.route('/profile/<int:user_id>')
    def profile(user_id):
        profile_user = User.query.get_or_404(user_id)
        listings   = Listing.query.filter_by(seller_id=user_id).order_by(Listing.created_at.desc()).all()
        notes_list = Note.query.filter_by(author_id=user_id).order_by(Note.upvotes.desc()).all()
        return render_template('profiles.html',
                               profile_user=profile_user,
                               listings=listings,
                               notes=notes_list,
                               avg_rating=profile_user.get_average_rating())

    # ── Settings ─────────────────────────────────────────────────

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        if request.method == 'POST':
            current_user.first_name = request.form.get('first_name', current_user.first_name)
            current_user.last_name  = request.form.get('last_name',  current_user.last_name)
            current_user.bio        = request.form.get('bio',        current_user.bio or '')
            db.session.commit()
            flash('Settings saved.', 'success')
            return redirect(url_for('settings'))
        return render_template('settings.html', user=current_user)

    # ── AJAX: user search ────────────────────────────────────────

    @app.route('/api/search_users')
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

    # ── Social Feed ─────────────────────────────────────────────

    VALID_POST_TYPES = {'general', 'event', 'news', 'resource'}

    @app.route('/feed')
    @login_required
    def feed():
        return redirect(url_for('dashboard'))

    ALLOWED_IMAGE_MIMES = {'image/jpeg', 'image/png'}
    MAX_POST_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

    @app.route('/feed/create', methods=['POST'])
    @login_required
    def feed_create():
        body      = request.form.get('body', '').strip()
        post_type = request.form.get('post_type', 'general').strip()
        if not body:
            flash('Post body cannot be empty.', 'error')
            return redirect(url_for('dashboard'))
        if post_type not in VALID_POST_TYPES:
            post_type = 'general'

        post = Post(author_id=current_user.id, body=body, post_type=post_type)

        # ── Image attachment ─────────────────────────────────────
        attachment = request.files.get('attachment')
        if attachment and attachment.filename:
            if attachment.mimetype not in ALLOWED_IMAGE_MIMES:
                flash('Only JPG and PNG images are supported.', 'error')
                return redirect(url_for('dashboard'))
            data = attachment.read()
            if len(data) > MAX_POST_IMAGE_BYTES:
                flash('Image must be under 10 MB.', 'error')
                return redirect(url_for('dashboard'))
            ext = 'jpg' if attachment.mimetype == 'image/jpeg' else 'png'
            filename = f"{uuid.uuid4().hex}_{secure_filename(attachment.filename)}"
            upload_dir = os.path.join(app.static_folder, 'uploads', 'posts')
            os.makedirs(upload_dir, exist_ok=True)
            with open(os.path.join(upload_dir, filename), 'wb') as f:
                f.write(data)
            post.image_path = f"uploads/posts/{filename}"
            post.image_name = attachment.filename

        # ── Link preview (only if no image) ──────────────────────
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
                    pass  # Network/parse errors are non-fatal

        db.session.add(post)
        current_user.xp += 5
        db.session.commit()
        flash('Post shared!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/feed/<int:post_id>/like', methods=['POST'])
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

    @app.route('/feed/<int:post_id>/comment', methods=['POST'])
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

    @app.route('/feed/<int:post_id>/delete', methods=['POST'])
    @login_required
    def feed_delete(post_id):
        post = Post.query.get_or_404(post_id)
        if post.author_id != current_user.id:
            return jsonify({'error': 'forbidden'}), 403
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted.', 'success')
        return redirect(url_for('dashboard'))

    # ── Listing comments ─────────────────────────────────────────

    @app.route('/listings/<int:listing_id>/comment', methods=['POST'])
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

    @app.route('/listing-comments/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_listing_comment(comment_id):
        comment = ListingComment.query.get_or_404(comment_id)
        if comment.author_id != current_user.id:
            return jsonify({'error': 'forbidden'}), 403
        comment.listing.comments_count = max(0, comment.listing.comments_count - 1)
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'ok': True})

    # ── Bounty comments ──────────────────────────────────────────

    @app.route('/bounties/<int:bounty_id>/comment', methods=['POST'])
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

    @app.route('/bounty-comments/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_bounty_comment(comment_id):
        comment = BountyComment.query.get_or_404(comment_id)
        if comment.author_id != current_user.id:
            return jsonify({'error': 'forbidden'}), 403
        comment.bounty.comments_count = max(0, comment.bounty.comments_count - 1)
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'ok': True})

    # ── Session comments ─────────────────────────────────────────

    @app.route('/sessions/<int:session_id>/comment', methods=['POST'])
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

    @app.route('/session-comments/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_session_comment(comment_id):
        comment = SessionComment.query.get_or_404(comment_id)
        if comment.author_id != current_user.id:
            return jsonify({'error': 'forbidden'}), 403
        comment.session.comments_count = max(0, comment.session.comments_count - 1)
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'ok': True})

    # ── Activity ─────────────────────────────────────────────────

    @app.route('/activity')
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
                'link': url_for('dashboard'),
                'badge': p.post_type,
            })

        for c in PostComment.query.filter_by(author_id=uid).order_by(PostComment.created_at.desc()).limit(30):
            post = Post.query.get(c.post_id)
            author_name = f'{post.author.first_name} {post.author.last_name}' if post else 'someone'
            events.append({
                'type': 'comment', 'time': c.created_at,
                'label': f'You commented on {author_name}\'s post',
                'excerpt': c.body[:120] + ('…' if len(c.body) > 120 else ''),
                'link': url_for('dashboard'),
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
                    'link': url_for('dashboard'),
                    'badge': None,
                })

        for rsvp in SessionRSVP.query.filter_by(user_id=uid).all():
            sess = StudySession.query.get(rsvp.session_id)
            if sess:
                events.append({
                    'type': 'rsvp', 'time': sess.created_at,
                    'label': f'You joined "{sess.title}"',
                    'excerpt': f'{sess.unit_code} · {sess.location}',
                    'link': url_for('study_sessions'),
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

    # ── Library ──────────────────────────────────────────────────

    @app.route('/library')
    @login_required
    def library():
        saved = (SavedNote.query
                 .filter_by(user_id=current_user.id)
                 .order_by(SavedNote.saved_at.desc())
                 .all())
        saved_notes = [sn.note for sn in saved]
        saved_ids   = {sn.note_id for sn in saved}
        my_notes    = Note.query.filter_by(author_id=current_user.id).order_by(Note.created_at.desc()).all()
        return render_template('library.html', saved_notes=saved_notes,
                               my_notes=my_notes, saved_ids=saved_ids)

    @app.route('/save_note/<int:note_id>', methods=['POST'])
    @login_required
    def save_note(note_id):
        note = Note.query.get_or_404(note_id)
        existing = SavedNote.query.filter_by(user_id=current_user.id, note_id=note_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'saved': False})
        sn = SavedNote(user_id=current_user.id, note_id=note_id)
        db.session.add(sn)
        db.session.commit()
        return jsonify({'saved': True})

    # ── My Listings ───────────────────────────────────────────────

    @app.route('/my-listings')
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

    # ── Stub pages ──────────────────────────────────────────────

    @app.route('/about')
    def about():
        return redirect(url_for('index'))

    @app.route('/privacy')
    def privacy():
        return redirect(url_for('index'))

    @app.route('/contact')
    def contact():
        return redirect(url_for('index'))

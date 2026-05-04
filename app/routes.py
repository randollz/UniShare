from flask import (render_template, request, redirect,
                   url_for, session, flash, jsonify, Response)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (User, Listing, Note, StudySession, SessionRSVP,
                        Bounty, SavedListing, Rating, Message, Post, PostLike)
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
                controllers.create_listing(current_user.id, request.form)
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
                controllers.create_note(current_user.id, request.form)
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
        return render_template('note_detail.html', note=note)

    @app.route('/notes/<int:note_id>/download')
    def download_note(note_id):
        note = Note.query.get_or_404(note_id)
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
                controllers.create_study_session(current_user.id, request.form)
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
                controllers.create_bounty(current_user.id, request.form)
                flash('Bounty posted!', 'success')
                return redirect(url_for('bounties'))
            except ValueError as e:
                flash(str(e), 'error')
        return render_template('create_bounty.html', errors={}, form=request.form)

    @app.route('/claim_bounty/<int:bounty_id>', methods=['POST'])
    @login_required
    def claim_bounty(bounty_id):
        bounty = Bounty.query.get_or_404(bounty_id)
        if bounty.poster_id == current_user.id:
            flash("You can't claim your own bounty.", 'error')
        else:
            db.session.delete(bounty)
            db.session.commit()
            flash('Bounty claimed!', 'success')
        return redirect(url_for('bounties'))

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

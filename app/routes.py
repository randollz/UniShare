import functools
from flask import (render_template, request, redirect,
                   url_for, session, flash, jsonify, Response)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from validators import (validate_required_text, validate_optional_text,
                        validate_unit_code, validate_price, validate_positive_int,
                        validate_session_date, validate_choice, LISTING_CONDITIONS)


# ─────────────────────────────────────────────────────────────
# Helpers (module-level so routes can reference them)
# ─────────────────────────────────────────────────────────────

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    return user


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please sign in to continue.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# Route registration
# ─────────────────────────────────────────────────────────────

def register_routes(app):

    # ── Context processors ──────────────────────────────────────

    @app.context_processor
    def inject_unread_count():
        user_id = session.get('user_id')
        if not user_id:
            return {'unread_count': 0}
        db = get_db()
        count = db.execute(
            'SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND read = 0',
            (user_id,)
        ).fetchone()[0]
        db.close()
        return {'unread_count': count}

    # ── Error handlers ──────────────────────────────────────────

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', current_user=get_current_user()), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html', current_user=get_current_user()), 500

    # ── Auth ────────────────────────────────────────────────────

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if session.get('user_id'):
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            action = request.form.get('action')
            db = get_db()

            if action == 'login':
                email = request.form.get('email', '').strip().lower()
                password = request.form.get('password', '')
                user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
                if user and check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    db.close()
                    return redirect(url_for('dashboard'))
                flash('Invalid email or password.', 'error')

            elif action == 'register':
                first_name = request.form.get('first_name', '').strip()
                last_name  = request.form.get('last_name', '').strip()
                email      = request.form.get('email', '').strip().lower()
                password   = request.form.get('password', '')
                existing   = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
                if existing:
                    flash('An account with that email already exists.', 'error')
                else:
                    cur = db.execute(
                        'INSERT INTO users (first_name, last_name, email, password_hash) VALUES (?,?,?,?)',
                        (first_name, last_name, email, generate_password_hash(password))
                    )
                    db.commit()
                    session['user_id'] = cur.lastrowid
                    db.close()
                    return redirect(url_for('dashboard'))

            db.close()

        return render_template('login.html', current_user=get_current_user())

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    # ── Index ───────────────────────────────────────────────────

    @app.route('/')
    def index():
        db = get_db()

        stats = {
            'users':    db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'listings': db.execute('SELECT COUNT(*) FROM listings').fetchone()[0],
            'notes':    db.execute('SELECT COUNT(*) FROM notes').fetchone()[0],
        }

        recent_listings = db.execute(
            'SELECT * FROM listings ORDER BY created_at DESC LIMIT 3'
        ).fetchall()

        notes_by_unit = db.execute(
            'SELECT unit_code, COUNT(*) as count FROM notes GROUP BY unit_code ORDER BY count DESC LIMIT 6'
        ).fetchall()

        top_users = db.execute(
            'SELECT * FROM users ORDER BY xp DESC LIMIT 5'
        ).fetchall()

        db.close()
        return render_template('index.html',
                               current_user=get_current_user(),
                               stats=stats,
                               recent_listings=recent_listings,
                               notes_by_unit=notes_by_unit,
                               top_users=top_users)

    # ── Dashboard ───────────────────────────────────────────────

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user = get_current_user()
        db   = get_db()

        my_listings = db.execute(
            'SELECT * FROM listings WHERE seller_id = ? ORDER BY created_at DESC',
            (user['id'],)
        ).fetchall()

        saved = db.execute(
            '''SELECT l.*, u.first_name, u.last_name
               FROM saved_listings sl
               JOIN listings l ON l.id = sl.listing_id
               JOIN users    u ON u.id = l.seller_id
               WHERE sl.user_id = ?''',
            (user['id'],)
        ).fetchall()

        my_sessions = db.execute(
            '''SELECT s.* FROM sessions s
               JOIN session_rsvps r ON r.session_id = s.id
               WHERE r.user_id = ?
               ORDER BY s.session_date ASC''',
            (user['id'],)
        ).fetchall()

        top_users = db.execute(
            'SELECT * FROM users ORDER BY xp DESC LIMIT 5'
        ).fetchall()

        db.close()
        return render_template('dashboard.html',
                               current_user=user,
                               user=user,
                               my_listings=my_listings,
                               saved=saved,
                               my_sessions=my_sessions,
                               top_users=top_users)

    # ── Marketplace ─────────────────────────────────────────────

    @app.route('/marketplace')
    def marketplace():
        q         = request.args.get('q', '').strip()
        unit      = request.args.get('unit', '').strip().upper()
        condition = request.args.get('condition', '').strip()
        sort      = request.args.get('sort', '').strip()

        query  = '''SELECT l.*, u.first_name, u.last_name,
                           u.rating_sum, u.rating_count,
                           CASE WHEN u.rating_count > 0
                                THEN ROUND(CAST(u.rating_sum AS REAL) / u.rating_count, 1)
                                ELSE NULL END AS avg_rating
                    FROM listings l JOIN users u ON u.id = l.seller_id
                    WHERE 1=1'''
        params = []

        if q:
            query += ' AND (l.title LIKE ? OR l.description LIKE ?)'
            params += [f'%{q}%', f'%{q}%']
        if unit:
            query += ' AND l.unit_code = ?'
            params.append(unit)
        if condition:
            query += ' AND l.condition = ?'
            params.append(condition)

        if sort == 'price_asc':
            query += ' ORDER BY l.price ASC'
        elif sort == 'price_desc':
            query += ' ORDER BY l.price DESC'
        else:
            query += ' ORDER BY l.created_at DESC'

        db       = get_db()
        listings = db.execute(query, params).fetchall()

        saved_ids = set()
        user = get_current_user()
        if user:
            rows = db.execute(
                'SELECT listing_id FROM saved_listings WHERE user_id = ?',
                (user['id'],)
            ).fetchall()
            saved_ids = {r['listing_id'] for r in rows}

        recent_listings = db.execute(
            '''SELECT l.id, l.title, l.unit_code, l.price, l.condition
               FROM listings l
               ORDER BY l.created_at DESC
               LIMIT 3'''
        ).fetchall()

        price_stats_rows = db.execute(
            '''SELECT
                  SUBSTR(unit_code, 1, 4) AS unit_prefix,
                  ROUND(AVG(price), 0)    AS avg_price,
                  COUNT(*)                AS n
               FROM listings
               GROUP BY unit_prefix
               HAVING n >= 1
               ORDER BY n DESC
               LIMIT 5'''
        ).fetchall()

        active_count = db.execute('SELECT COUNT(*) AS c FROM listings').fetchone()['c']

        db.close()

        return render_template('marketplace.html',
                               current_user=user,
                               listings=listings,
                               saved_ids=saved_ids,
                               recent_listings=recent_listings,
                               price_stats=price_stats_rows,
                               active_count=active_count,
                               q=q, unit=unit, condition=condition, sort=sort)

    @app.route('/create_listing', methods=['GET', 'POST'])
    @login_required
    def create_listing():
        errors = {}
        form = {}
        if request.method == 'POST':
            form['title'],       errors['title']       = validate_required_text(request.form.get('title'), 'Title', max_len=100)
            form['unit_code'],   errors['unit_code']   = validate_unit_code(request.form.get('unit_code'))
            form['price'],       errors['price']       = validate_price(request.form.get('price'))
            form['condition'],   errors['condition']   = validate_choice(request.form.get('condition'), 'Condition', LISTING_CONDITIONS)
            form['description'], errors['description'] = validate_optional_text(request.form.get('description'), 'Description', max_len=2000)

            errors = {k: v for k, v in errors.items() if v}

            if not errors:
                user = get_current_user()
                db   = get_db()
                db.execute(
                    'INSERT INTO listings (seller_id, title, unit_code, price, condition, description) VALUES (?,?,?,?,?,?)',
                    (user['id'], form['title'], form['unit_code'], form['price'],
                     form['condition'], form['description'])
                )
                db.commit()
                db.close()
                flash('Listing posted!', 'success')
                return redirect(url_for('marketplace'))

            for msg in errors.values():
                flash(msg, 'error')

        return render_template('create_listing.html',
                               current_user=get_current_user(),
                               errors=errors, form=form,
                               conditions=LISTING_CONDITIONS)

    @app.route('/delete_listing/<int:listing_id>', methods=['POST'])
    @login_required
    def delete_listing(listing_id):
        user = get_current_user()
        db   = get_db()
        db.execute('DELETE FROM listings WHERE id = ? AND seller_id = ?', (listing_id, user['id']))
        db.commit()
        db.close()
        return redirect(url_for('dashboard'))

    @app.route('/save_listing/<int:listing_id>', methods=['POST'])
    @login_required
    def save_listing(listing_id):
        user = get_current_user()
        db   = get_db()
        try:
            db.execute('INSERT INTO saved_listings (user_id, listing_id) VALUES (?,?)',
                       (user['id'], listing_id))
            db.commit()
        except Exception:
            pass
        db.close()
        return redirect(url_for('marketplace'))

    @app.route('/unsave_listing/<int:listing_id>', methods=['POST'])
    @login_required
    def unsave_listing(listing_id):
        user = get_current_user()
        db   = get_db()
        db.execute(
            'DELETE FROM saved_listings WHERE user_id = ? AND listing_id = ?',
            (user['id'], listing_id)
        )
        db.commit()
        db.close()
        return redirect(url_for('marketplace'))

    @app.route('/listings/<int:listing_id>')
    def view_listing(listing_id):
        db = get_db()
        listing = db.execute(
            '''SELECT l.*, u.first_name, u.last_name
               FROM listings l JOIN users u ON u.id = l.seller_id
               WHERE l.id = ?''',
            (listing_id,)
        ).fetchone()
        db.close()

        if listing is None:
            flash('Listing not found.', 'error')
            return redirect(url_for('marketplace'))

        return render_template('listing_detail.html',
                               listing=listing,
                               current_user=get_current_user())

    @app.route('/listings/<int:listing_id>/download')
    def download_listing(listing_id):
        db = get_db()
        listing = db.execute('SELECT * FROM listings WHERE id = ?', (listing_id,)).fetchone()
        db.close()

        if listing is None:
            flash('Listing not found.', 'error')
            return redirect(url_for('marketplace'))

        content = (
            f"{listing['title']}\n\n"
            f"Unit: {listing['unit_code']}\n"
            f"Price: ${listing['price']:.2f}\n"
            f"Condition: {listing['condition']}\n\n"
            f"{listing['description']}"
        )

        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename=listing-{listing_id}.txt'}
        )

    # ── Notes ───────────────────────────────────────────────────

    @app.route('/notes')
    def notes():
        q    = request.args.get('q', '').strip()
        unit = request.args.get('unit', '').strip().upper()

        query  = '''SELECT n.*, u.first_name, u.last_name
                    FROM notes n JOIN users u ON u.id = n.author_id
                    WHERE 1=1'''
        params = []

        if q:
            query += ' AND (n.title LIKE ? OR n.description LIKE ?)'
            params += [f'%{q}%', f'%{q}%']
        if unit:
            query += ' AND n.unit_code = ?'
            params.append(unit)

        query += ' ORDER BY n.upvotes DESC, n.created_at DESC'

        db    = get_db()
        notes_list = db.execute(query, params).fetchall()
        db.close()

        return render_template('notes.html',
                               current_user=get_current_user(),
                               notes=notes_list, q=q, unit=unit)

    @app.route('/create_note', methods=['GET', 'POST'])
    @login_required
    def create_note():
        errors = {}
        form = {}

        if request.method == 'POST':
            form['title'],       errors['title']       = validate_required_text(request.form.get('title'), 'Title', max_len=150)
            form['unit_code'],   errors['unit_code']   = validate_unit_code(request.form.get('unit_code'))
            form['semester'],    errors['semester']    = validate_optional_text(request.form.get('semester'), 'Semester', max_len=50)
            form['description'], errors['description'] = validate_optional_text(request.form.get('description'), 'Description', max_len=2000)

            errors = {k: v for k, v in errors.items() if v}

            if not errors:
                user = get_current_user()
                db   = get_db()
                db.execute(
                    'INSERT INTO notes (author_id, title, unit_code, semester, description) VALUES (?,?,?,?,?)',
                    (user['id'], form['title'], form['unit_code'],
                     form['semester'], form['description'])
                )
                db.commit()
                db.close()
                flash('Notes shared!', 'success')
                return redirect(url_for('notes'))

            for msg in errors.values():
                flash(msg, 'error')

        return render_template('create_note.html',
                               current_user=get_current_user(),
                               errors=errors, form=form)

    @app.route('/upvote_note/<int:note_id>', methods=['POST'])
    @login_required
    def upvote_note(note_id):
        db = get_db()
        db.execute('UPDATE notes SET upvotes = upvotes + 1 WHERE id = ?', (note_id,))
        db.commit()
        db.close()
        return redirect(url_for('notes'))

    @app.route('/notes/<int:note_id>')
    def view_note(note_id):
        db = get_db()
        note = db.execute(
            '''SELECT n.*, u.first_name, u.last_name
               FROM notes n JOIN users u ON u.id = n.author_id
               WHERE n.id = ?''',
            (note_id,)
        ).fetchone()
        db.close()

        if note is None:
            flash('Note not found.', 'error')
            return redirect(url_for('notes'))

        return render_template('note_detail.html', note=note, current_user=get_current_user())

    @app.route('/notes/<int:note_id>/download')
    def download_note(note_id):
        db = get_db()
        note = db.execute('SELECT * FROM notes WHERE id = ?', (note_id,)).fetchone()
        db.close()

        if note is None:
            flash('Note not found.', 'error')
            return redirect(url_for('notes'))

        content = (
            f"{note['title']}\n\n"
            f"Unit: {note['unit_code']}\n"
            f"Semester: {note['semester']}\n\n"
            f"{note['description']}"
        )

        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename=note-{note_id}.txt'}
        )

    # ── Study Sessions ──────────────────────────────────────────

    @app.route('/sessions')
    def study_sessions():
        unit = request.args.get('unit', '').strip().upper()

        query = '''
        SELECT s.*, u.first_name, u.last_name,
           (SELECT COUNT(*) FROM session_rsvps r WHERE r.session_id = s.id) as rsvp_count,
           EXISTS (
               SELECT 1 FROM session_rsvps r2
               WHERE r2.session_id = s.id AND r2.user_id = ?
           ) as current_user_joined
        FROM sessions s
        JOIN users u ON u.id = s.host_id
        WHERE 1=1
        '''
        current_user = get_current_user()
        params = [current_user['id'] if current_user else 0]

        if unit:
            query += ' AND s.unit_code = ?'
            params.append(unit)

        query += ' ORDER BY s.session_date ASC'

        db           = get_db()
        sessions_list = db.execute(query, params).fetchall()
        db.close()

        return render_template('sessions.html',
                               current_user=current_user,
                               sessions=sessions_list, unit=unit)

    @app.route('/create_session', methods=['GET', 'POST'])
    @login_required
    def create_session():
        errors = {}
        form = {}

        if request.method == 'POST':
            form['title'],         errors['title']         = validate_required_text(request.form.get('title'), 'Title', max_len=150)
            form['unit_code'],     errors['unit_code']     = validate_unit_code(request.form.get('unit_code'))
            form['location'],      errors['location']      = validate_optional_text(request.form.get('location'), 'Location', max_len=200)
            form['session_date'],  errors['session_date']  = validate_session_date(request.form.get('session_date'))
            form['max_attendees'], errors['max_attendees'] = validate_positive_int(request.form.get('max_attendees', '10'), 'Max attendees', min_value=2, max_value=200)
            form['description'],   errors['description']   = validate_optional_text(request.form.get('description'), 'Description', max_len=2000)

            errors = {k: v for k, v in errors.items() if v}

            if not errors:
                user = get_current_user()
                db   = get_db()
                db.execute(
                    'INSERT INTO sessions (host_id, title, unit_code, location, session_date, max_attendees, description) VALUES (?,?,?,?,?,?,?)',
                    (user['id'], form['title'], form['unit_code'], form['location'],
                     form['session_date'], form['max_attendees'], form['description'])
                )
                db.commit()
                db.close()
                flash('Study session posted!', 'success')
                return redirect(url_for('study_sessions'))

            for msg in errors.values():
                flash(msg, 'error')

        return render_template('create_session.html',
                               current_user=get_current_user(),
                               errors=errors, form=form)

    @app.route('/rsvp_session/<int:session_id>', methods=['POST'])
    @login_required
    def rsvp_session(session_id):
        user = get_current_user()
        db   = get_db()
        try:
            db.execute('INSERT INTO session_rsvps (session_id, user_id) VALUES (?,?)',
                       (session_id, user['id']))
            db.commit()
            flash("You're in!", 'success')
        except Exception:
            flash("You're already signed up for that session.", 'info')
        db.close()
        return redirect(url_for('study_sessions'))

    @app.route('/delete_session/<int:session_id>', methods=['POST'])
    @login_required
    def delete_session(session_id):
        user = get_current_user()
        db   = get_db()
        db.execute('DELETE FROM sessions WHERE id = ? AND host_id = ?', (session_id, user['id']))
        db.commit()
        db.close()
        flash('Session deleted.', 'success')
        return redirect(url_for('study_sessions'))

    @app.route('/cancel_rsvp/<int:session_id>', methods=['POST'])
    @login_required
    def cancel_rsvp(session_id):
        user = get_current_user()
        db   = get_db()
        db.execute(
            'DELETE FROM session_rsvps WHERE session_id = ? AND user_id = ?',
            (session_id, user['id'])
        )
        db.commit()
        db.close()
        flash('RSVP cancelled.', 'info')
        return redirect(url_for('study_sessions'))

    # ── Ratings ─────────────────────────────────────────────────

    @app.route('/rate_user/<int:listing_id>', methods=['POST'])
    @login_required
    def rate_user(listing_id):
        rater = get_current_user()
        db    = get_db()

        listing = db.execute('SELECT * FROM listings WHERE id = ?', (listing_id,)).fetchone()
        if not listing:
            db.close()
            flash('Listing not found.', 'error')
            return redirect(url_for('marketplace'))

        rated_id = listing['seller_id']
        if rated_id == rater['id']:
            db.close()
            flash('You cannot rate yourself.', 'error')
            return redirect(url_for('marketplace'))

        already = db.execute(
            'SELECT id FROM ratings WHERE rater_id = ? AND listing_id = ?',
            (rater['id'], listing_id)
        ).fetchone()
        if already:
            db.close()
            flash('You have already rated this transaction.', 'info')
            return redirect(url_for('marketplace'))

        score   = int(request.form.get('score', 5))
        comment = request.form.get('comment', '').strip()

        db.execute(
            'INSERT INTO ratings (rater_id, rated_id, listing_id, score, comment) VALUES (?,?,?,?,?)',
            (rater['id'], rated_id, listing_id, score, comment)
        )
        db.execute(
            'UPDATE users SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE id = ?',
            (score, rated_id)
        )
        db.commit()
        db.close()
        flash('Rating submitted!', 'success')
        return redirect(url_for('marketplace'))

    # ── Leaderboard ─────────────────────────────────────────────

    @app.route('/leaderboard')
    def leaderboard():
        db = get_db()
        users = db.execute('SELECT * FROM users ORDER BY xp DESC').fetchall()
        db.close()
        return render_template('new_leaderboard.html',
                               current_user=get_current_user(),
                               users=users)

    # ── Messages ────────────────────────────────────────────────

    @app.route('/messages')
    @login_required
    def messages():
        user = get_current_user()
        db   = get_db()

        contacts = db.execute(
            '''SELECT DISTINCT u.id, u.first_name, u.last_name
               FROM messages m
               JOIN users u ON u.id = CASE
                   WHEN m.sender_id   = ? THEN m.receiver_id
                   ELSE m.sender_id
               END
               WHERE m.sender_id = ? OR m.receiver_id = ?
               ORDER BY u.first_name''',
            (user['id'], user['id'], user['id'])
        ).fetchall()

        db.close()
        return render_template('messages.html',
                               current_user=user,
                               contacts=contacts,
                               active_user_id=None)

    @app.route('/messages/<int:other_id>')
    @login_required
    def messages_thread(other_id):
        user = get_current_user()
        db   = get_db()

        db.execute(
            'UPDATE messages SET read = 1 WHERE sender_id = ? AND receiver_id = ?',
            (other_id, user['id'])
        )
        db.commit()

        thread = db.execute(
            '''SELECT m.*, u.first_name, u.last_name
               FROM messages m JOIN users u ON u.id = m.sender_id
               WHERE (m.sender_id = ? AND m.receiver_id = ?)
                  OR (m.sender_id = ? AND m.receiver_id = ?)
               ORDER BY m.created_at ASC''',
            (user['id'], other_id, other_id, user['id'])
        ).fetchall()

        other_user = db.execute('SELECT * FROM users WHERE id = ?', (other_id,)).fetchone()

        contacts = db.execute(
            '''SELECT DISTINCT u.id, u.first_name, u.last_name
               FROM messages m
               JOIN users u ON u.id = CASE
                   WHEN m.sender_id   = ? THEN m.receiver_id
                   ELSE m.sender_id
               END
               WHERE m.sender_id = ? OR m.receiver_id = ?
               ORDER BY u.first_name''',
            (user['id'], user['id'], user['id'])
        ).fetchall()

        db.close()
        return render_template('messages.html',
                               current_user=user,
                               contacts=contacts,
                               thread=thread,
                               other_user=other_user,
                               active_user_id=other_id)

    @app.route('/messages/<int:other_id>/send', methods=['POST'])
    @login_required
    def messages_send(other_id):
        user = get_current_user()
        body = request.json.get('body', '').strip() if request.is_json else request.form.get('body', '').strip()
        if not body:
            return jsonify({'error': 'empty'}), 400

        db = get_db()
        db.execute(
            'INSERT INTO messages (sender_id, receiver_id, body) VALUES (?,?,?)',
            (user['id'], other_id, body)
        )
        db.commit()
        db.close()
        return jsonify({'ok': True})

    @app.route('/messages/<int:other_id>/poll')
    @login_required
    def messages_poll(other_id):
        user     = get_current_user()
        after_id = int(request.args.get('after', 0))
        db       = get_db()

        rows = db.execute(
            '''SELECT m.id, m.sender_id, m.body, m.created_at
               FROM messages m
               WHERE ((m.sender_id = ? AND m.receiver_id = ?)
                   OR (m.sender_id = ? AND m.receiver_id = ?))
                 AND m.id > ?
               ORDER BY m.created_at ASC''',
            (user['id'], other_id, other_id, user['id'], after_id)
        ).fetchall()

        db.execute(
            'UPDATE messages SET read = 1 WHERE sender_id = ? AND receiver_id = ? AND id > ?',
            (other_id, user['id'], after_id)
        )
        db.commit()
        db.close()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/messages/<int:other_id>/send', methods=['POST'])
    @login_required
    def api_messages_send(other_id):
        user = get_current_user()
        body = request.json.get('body', '').strip() if request.is_json else request.form.get('body', '').strip()
        if not body:
            return jsonify({'error': 'empty'}), 400

        db  = get_db()
        cur = db.execute(
            'INSERT INTO messages (sender_id, receiver_id, body) VALUES (?,?,?)',
            (user['id'], other_id, body)
        )
        db.commit()
        row = db.execute('SELECT id, body, created_at FROM messages WHERE id = ?', (cur.lastrowid,)).fetchone()
        db.close()

        return jsonify({
            'id':          row['id'],
            'body':        row['body'],
            'created_at':  row['created_at'],
            'sender_id':   user['id'],
            'sender_name': f"{user['first_name']} {user['last_name']}",
        })

    @app.route('/api/messages/<int:other_id>/poll')
    @login_required
    def api_messages_poll(other_id):
        user  = get_current_user()
        since = request.args.get('since', '1970-01-01 00:00:00')
        db    = get_db()

        rows = db.execute(
            '''SELECT m.id, m.sender_id, m.body, m.created_at
               FROM messages m
               WHERE ((m.sender_id = ? AND m.receiver_id = ?)
                   OR (m.sender_id = ? AND m.receiver_id = ?))
                 AND m.created_at > ?
               ORDER BY m.created_at ASC''',
            (user['id'], other_id, other_id, user['id'], since)
        ).fetchall()

        db.execute(
            'UPDATE messages SET read = 1 WHERE sender_id = ? AND receiver_id = ? AND created_at > ?',
            (other_id, user['id'], since)
        )
        db.commit()
        db.close()
        return jsonify([dict(r) for r in rows])

    # ── Bounties ────────────────────────────────────────────────

    @app.route('/bounties')
    def bounties():
        db           = get_db()
        bounties_list = db.execute(
            '''SELECT b.*, u.first_name, u.last_name
               FROM bounties b JOIN users u ON u.id = b.poster_id
               ORDER BY b.created_at DESC'''
        ).fetchall()
        db.close()
        return render_template('bounties.html',
                               current_user=get_current_user(),
                               bounties=bounties_list)

    @app.route('/create_bounty', methods=['GET', 'POST'])
    @login_required
    def create_bounty():
        errors = {}
        form = {}

        if request.method == 'POST':
            form['title'],       errors['title']       = validate_required_text(request.form.get('title'), 'Title', max_len=150)
            form['description'], errors['description'] = validate_optional_text(request.form.get('description'), 'Description', max_len=2000)
            form['reward'],      errors['reward']      = validate_price(request.form.get('reward'), field_label='Reward', allow_zero=True)

            raw_unit = (request.form.get('unit_code') or '').strip()
            if raw_unit:
                form['unit_code'], errors['unit_code'] = validate_unit_code(raw_unit)
            else:
                form['unit_code'] = ''
                errors['unit_code'] = None

            errors = {k: v for k, v in errors.items() if v}

            if not errors:
                user = get_current_user()
                db   = get_db()
                db.execute(
                    'INSERT INTO bounties (poster_id, title, unit_code, reward, description) VALUES (?,?,?,?,?)',
                    (user['id'], form['title'], form['unit_code'],
                     form['reward'], form['description'])
                )
                db.commit()
                db.close()
                flash('Bounty posted!', 'success')
                return redirect(url_for('bounties'))

            for msg in errors.values():
                flash(msg, 'error')

        return render_template('create_bounty.html',
                               current_user=get_current_user(),
                               errors=errors, form=form)

    @app.route('/claim_bounty/<int:bounty_id>', methods=['POST'])
    @login_required
    def claim_bounty(bounty_id):
        user = get_current_user()
        db   = get_db()

        bounty = db.execute('SELECT poster_id FROM bounties WHERE id = ?', (bounty_id,)).fetchone()

        if bounty is None:
            db.close()
            flash('Bounty not found.', 'error')
            return redirect(url_for('bounties'))

        if bounty['poster_id'] == user['id']:
            db.close()
            flash("You can't claim your own bounty.", 'error')
            return redirect(url_for('bounties'))

        db.execute('DELETE FROM bounties WHERE id = ?', (bounty_id,))
        db.commit()
        db.close()
        flash('Bounty claimed!', 'success')
        return redirect(url_for('bounties'))

    @app.route('/bounties/<int:bounty_id>')
    def view_bounty(bounty_id):
        db = get_db()
        bounty = db.execute(
            '''SELECT b.*, u.first_name, u.last_name
               FROM bounties b JOIN users u ON u.id = b.poster_id
               WHERE b.id = ?''',
            (bounty_id,)
        ).fetchone()
        db.close()

        if bounty is None:
            flash('Bounty not found.', 'error')
            return redirect(url_for('bounties'))

        return render_template('bounty_detail.html', bounty=bounty, current_user=get_current_user())

    @app.route('/bounties/<int:bounty_id>/download')
    def download_bounty(bounty_id):
        db = get_db()
        bounty = db.execute('SELECT * FROM bounties WHERE id = ?', (bounty_id,)).fetchone()
        db.close()

        if bounty is None:
            flash('Bounty not found.', 'error')
            return redirect(url_for('bounties'))

        unit_line = bounty['unit_code'] if bounty['unit_code'] else 'General'

        content = (
            f"{bounty['title']}\n\n"
            f"Unit: {unit_line}\n"
            f"Reward: ${bounty['reward']:.2f}\n\n"
            f"{bounty['description']}"
        )

        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename=bounty-{bounty_id}.txt'}
        )

    # ── Profile ─────────────────────────────────────────────────

    @app.route('/profile/<int:user_id>')
    def profile(user_id):
        db           = get_db()
        profile_user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not profile_user:
            db.close()
            return redirect(url_for('index'))

        listings = db.execute(
            'SELECT * FROM listings WHERE seller_id = ? ORDER BY created_at DESC',
            (user_id,)
        ).fetchall()

        notes_list = db.execute(
            'SELECT * FROM notes WHERE author_id = ? ORDER BY upvotes DESC',
            (user_id,)
        ).fetchall()

        avg_rating = None
        if profile_user['rating_count'] > 0:
            avg_rating = round(profile_user['rating_sum'] / profile_user['rating_count'], 1)

        db.close()
        return render_template('profiles.html',
                               current_user=get_current_user(),
                               profile_user=profile_user,
                               listings=listings,
                               notes=notes_list,
                               avg_rating=avg_rating)

    # ── Settings ─────────────────────────────────────────────────

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        user = get_current_user()
        if request.method == 'POST':
            db = get_db()
            db.execute(
                'UPDATE users SET first_name=?, last_name=?, bio=? WHERE id=?',
                (request.form.get('first_name', user['first_name']),
                 request.form.get('last_name',  user['last_name']),
                 request.form.get('bio',        user['bio'] or ''),
                 user['id'])
            )
            db.commit()
            db.close()
            flash('Settings saved.', 'success')
            return redirect(url_for('settings'))
        return render_template('settings.html', current_user=user, user=user)

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

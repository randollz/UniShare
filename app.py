import os
import functools
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from validators import (validate_required_text, validate_optional_text,
                        validate_unit_code, validate_price, validate_positive_int,
                        validate_email, validate_password, validate_session_date,
                        validate_choice, LISTING_CONDITIONS)

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = 'unishare-demo-secret-key'


# ─────────────────────────────────────────────────────────────
# Helpers
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
# Auth
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Index
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Marketplace
# ─────────────────────────────────────────────────────────────

@app.route('/marketplace')
def marketplace():
    q         = request.args.get('q', '').strip()
    unit      = request.args.get('unit', '').strip().upper()
    condition = request.args.get('condition', '').strip()
    sort      = request.args.get('sort', '').strip()

    query  = '''SELECT l.*, u.first_name, u.last_name,
                       u.rating_sum, u.rating_count
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
    db.close()

    return render_template('marketplace.html',
                           current_user=get_current_user(),
                           listings=listings,
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

        # Strip keys where error is None so template can do {% if errors.title %}
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


# ─────────────────────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────────────────────

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
    notes = db.execute(query, params).fetchall()
    db.close()

    return render_template('notes.html',
                           current_user=get_current_user(),
                           notes=notes, q=q, unit=unit)


@app.route('/create_note', methods=['GET', 'POST'])
@login_required
def create_note():
    if request.method == 'POST':
        user = get_current_user()
        db   = get_db()
        db.execute(
            'INSERT INTO notes (author_id, title, unit_code, semester, description) VALUES (?,?,?,?,?)',
            (user['id'],
             request.form['title'],
             request.form['unit_code'].strip().upper(),
             request.form.get('semester', ''),
             request.form.get('description', ''))
        )
        db.commit()
        db.close()
        flash('Notes shared!', 'success')
        return redirect(url_for('notes'))
    return render_template('create_note.html', current_user=get_current_user())


@app.route('/upvote_note/<int:note_id>', methods=['POST'])
@login_required
def upvote_note(note_id):
    db = get_db()
    db.execute('UPDATE notes SET upvotes = upvotes + 1 WHERE id = ?', (note_id,))
    db.commit()
    db.close()
    return redirect(url_for('notes'))


# ─────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────

@app.route('/sessions')
def study_sessions():
    unit = request.args.get('unit', '').strip().upper()

    query  = '''SELECT s.*, u.first_name, u.last_name,
                       (SELECT COUNT(*) FROM session_rsvps r WHERE r.session_id = s.id) as rsvp_count
                FROM sessions s JOIN users u ON u.id = s.host_id
                WHERE 1=1'''
    params = []

    if unit:
        query += ' AND s.unit_code = ?'
        params.append(unit)

    query += ' ORDER BY s.session_date ASC'

    db       = get_db()
    sessions = db.execute(query, params).fetchall()
    db.close()

    return render_template('session.html',
                           current_user=get_current_user(),
                           sessions=sessions, unit=unit)


@app.route('/create_session', methods=['GET', 'POST'])
@login_required
def create_session():
    if request.method == 'POST':
        user = get_current_user()
        db   = get_db()
        db.execute(
            'INSERT INTO sessions (host_id, title, unit_code, location, session_date, max_attendees, description) VALUES (?,?,?,?,?,?,?)',
            (user['id'],
             request.form['title'],
             request.form['unit_code'].strip().upper(),
             request.form.get('location', ''),
             request.form.get('session_date', ''),
             int(request.form.get('max_attendees', 10)),
             request.form.get('description', ''))
        )
        db.commit()
        db.close()
        flash('Study session posted!', 'success')
        return redirect(url_for('study_sessions'))
    return render_template('create_session.html', current_user=get_current_user())


@app.route('/rsvp_session/<int:session_id>', methods=['POST'])
@login_required
def rsvp_session(session_id):
    user = get_current_user()
    db   = get_db()
    try:
        db.execute('INSERT INTO session_rsvps (session_id, user_id) VALUES (?,?)',
                   (session_id, user['id']))
        db.commit()
        flash('You\'re in!', 'success')
    except Exception:
        flash('You\'re already signed up for that session.', 'info')
    db.close()
    return redirect(url_for('study_sessions'))


# ─────────────────────────────────────────────────────────────
# Bounties
# ─────────────────────────────────────────────────────────────

@app.route('/bounties')
def bounties():
    db       = get_db()
    bounties = db.execute(
        '''SELECT b.*, u.first_name, u.last_name
           FROM bounties b JOIN users u ON u.id = b.poster_id
           ORDER BY b.created_at DESC'''
    ).fetchall()
    db.close()
    return render_template('bounties.html',
                           current_user=get_current_user(),
                           bounties=bounties)


@app.route('/create_bounty', methods=['GET', 'POST'])
@login_required
def create_bounty():
    if request.method == 'POST':
        user = get_current_user()
        db   = get_db()
        db.execute(
            'INSERT INTO bounties (poster_id, title, unit_code, reward, description) VALUES (?,?,?,?,?)',
            (user['id'],
             request.form['title'],
             request.form.get('unit_code', '').strip().upper(),
             float(request.form.get('reward', 0)),
             request.form.get('description', ''))
        )
        db.commit()
        db.close()
        flash('Bounty posted!', 'success')
        return redirect(url_for('bounties'))
    return render_template('create_bounty.html', current_user=get_current_user())


@app.route('/claim_bounty/<int:bounty_id>', methods=['POST'])
@login_required
def claim_bounty(bounty_id):
    db = get_db()
    db.execute('DELETE FROM bounties WHERE id = ?', (bounty_id,))
    db.commit()
    db.close()
    flash('Bounty claimed!', 'success')
    return redirect(url_for('bounties'))


# ─────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────

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

    notes = db.execute(
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
                           notes=notes,
                           avg_rating=avg_rating)


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Stub pages (footer links)
# ─────────────────────────────────────────────────────────────

@app.route('/about')
def about():
    return redirect(url_for('index'))


@app.route('/privacy')
def privacy():
    return redirect(url_for('index'))


@app.route('/contact')
def contact():
    return redirect(url_for('index'))


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

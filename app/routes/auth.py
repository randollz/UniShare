from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('feed.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('feed.dashboard'))
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
                return redirect(url_for('feed.dashboard'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

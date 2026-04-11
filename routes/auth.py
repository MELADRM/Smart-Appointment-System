"""Register, login, logout, password reset."""

from datetime import datetime, timedelta
import uuid
from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from db import load_db, save_db, new_id
from helpers import add_notification, is_valid_email
from app_utils import send_email, login_is_blocked, login_record_fail, login_clear

def register(app):
    @app.route('/register', methods=['GET', 'POST'], endpoint='register')
    def signup_view():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            name = request.form.get('name', '').strip()[:120]
            email = request.form.get('email', '').strip().lower()[:190]
            pw = request.form.get('password', '').strip()
            confirm = request.form.get('confirm', '').strip()
            if not all([name, email, pw, confirm]):
                flash('All fields are required.', 'danger')
                return render_template('auth/register.html')
            if len(name) < 2:
                flash('Please enter your full name.', 'danger')
                return render_template('auth/register.html')
            if not is_valid_email(email):
                flash('Please enter a valid email address.', 'danger')
                return render_template('auth/register.html')
            if pw != confirm:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/register.html')
            if len(pw) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('auth/register.html')
            db = load_db()
            if any(u['email'] == email for u in db['users']):
                flash('Email already registered.', 'danger')
                return render_template('auth/register.html')
            uid = new_id('u')
            db['users'].append(
                {
                    'id': uid,
                    'name': name,
                    'email': email,
                    'password': generate_password_hash(pw),
                    'role': 'user',
                    'is_active': True,
                    'created_at': datetime.now().isoformat(),
                }
            )
            add_notification(db, uid, f'Welcome to SmartBook, {name}! 🎉', 'success')
            save_db(db)
            send_email(
                email,
                'Welcome to SmartBook Pro',
                f'Hi {name},\n\n'
                'Thanks for creating an account on SmartBook Pro.\n'
                'You can now browse businesses and book appointments.\n\n'
                '— The SmartBook team',
            )
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('auth/register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        ip = request.remote_addr or '?'
        if request.method == 'POST':
            if login_is_blocked(ip):
                flash('Too many failed attempts. Try again in 10 minutes.', 'danger')
                return render_template('auth/login.html')
            email = request.form.get('email', '').strip().lower()
            pw = request.form.get('password', '').strip()
            if not email or not pw:
                flash('Please enter both email and password.', 'danger')
                return render_template('auth/login.html')
            db = load_db()
            user = next((u for u in db['users'] if u['email'] == email), None)
            if not user or not check_password_hash(user['password'], pw):
                login_record_fail(ip)
                flash('Invalid email or password.', 'danger')
                return render_template('auth/login.html')
            if not user.get('is_active', True):
                flash('Your account has been suspended. Contact support.', 'danger')
                return render_template('auth/login.html')
            login_clear(ip)
            session.update(
                {
                    'user_id': user['id'],
                    'user_name': user['name'],
                    'role': user['role'],
                }
            )
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        return render_template('auth/login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Logged out successfully.', 'info')
        return redirect(url_for('home'))

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()[:190]
            if not is_valid_email(email):
                flash('Please enter a valid email address.', 'danger')
                return render_template('auth/forgot.html')
            db = load_db()
            user = next((u for u in db['users'] if u['email'] == email), None)

            if user:
                token = uuid.uuid4().hex
                db.setdefault('password_resets', []).append(
                    {
                        'id': new_id('pr'),
                        'user_id': user['id'],
                        'token': token,
                        'used': False,
                        'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                        'created_at': datetime.now().isoformat(),
                    }
                )
                save_db(db)
                reset_link = url_for('reset_with_token', token=token, _external=True)
                print(f"[PASSWORD RESET] {email} -> {reset_link}")
                send_email(
                    email,
                    'Reset your SmartBook password',
                    f'Click the link to reset your password: {reset_link}',
                )
                flash(
                    f'If that email is registered, a reset link has been sent. '
                    f'(Dev link: <a href="{reset_link}">{reset_link}</a>)',
                    'info',
                )
            else:
                flash('If that email is registered, a reset link has been sent.', 'info')
            return redirect(url_for('login'))
        return render_template('auth/forgot.html')

    @app.route('/reset/<token>', methods=['GET', 'POST'])
    def reset_with_token(token):
        db = load_db()
        rec = next(
            (r for r in db.get('password_resets', []) if r['token'] == token and not r.get('used')),
            None,
        )
        if not rec:
            flash('That reset link is invalid or has already been used.', 'danger')
            return redirect(url_for('login'))

        try:
            expires_at = datetime.fromisoformat(rec['expires_at'])
        except (TypeError, ValueError):
            flash('That reset link is invalid. Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))
        if expires_at < datetime.now():
            flash('That reset link has expired. Request a new one.', 'danger')
            return redirect(url_for('forgot_password'))
        if request.method == 'POST':
            pw = request.form.get('new_password', '').strip()
            conf = request.form.get('confirm', '').strip()
            if len(pw) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('auth/reset_token.html', token=token)
            if pw != conf:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/reset_token.html', token=token)
            user = next((u for u in db['users'] if u['id'] == rec['user_id']), None)
            if user:
                user['password'] = generate_password_hash(pw)
            rec['used'] = True
            save_db(db)
            flash('Password updated! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('auth/reset_token.html', token=token)

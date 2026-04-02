"""Route-protection decorators."""

from functools import wraps
from flask import flash, redirect, session, url_for

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return dec

def role_required(*roles):
    # Wrong role gets redirected to home; missing login goes to /login.
    def decorator(f):
        @wraps(f)
        def dec(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)

        return dec

    return decorator

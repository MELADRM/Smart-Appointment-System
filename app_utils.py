"""Shared helpers used by routes (uploads, email, login throttling)."""

from datetime import datetime
import os
import sys
import uuid
from werkzeug.utils import secure_filename

ALLOWED_IMG_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _ext_ok(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG_EXTS

def _is_real_image(file_storage):
    # Catches a renamed .exe etc. Uses Pillow if available, otherwise trusts the extension.
    try:
        from PIL import Image
    except ImportError:
        return True
    try:
        file_storage.stream.seek(0)
        Image.open(file_storage.stream).verify()
        file_storage.stream.seek(0)
        return True
    except Exception:
        return False

def save_logo(app, file_storage, biz_id):
    # Returns the DB-relative path, or None if the upload is missing/invalid.
    if not file_storage or not file_storage.filename:
        return None
    if not _ext_ok(file_storage.filename):
        return None
    if not _is_real_image(file_storage):
        return None
    folder = os.path.join(app.root_path, 'static', 'uploads', 'logos')
    os.makedirs(folder, exist_ok=True)
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    fname = secure_filename(f"{biz_id}-{uuid.uuid4().hex[:6]}.{ext}")
    file_storage.save(os.path.join(folder, fname))
    return f"uploads/logos/{fname}"

def save_gallery_image(app, file_storage, biz_id):
    # Same rules as save_logo, different folder.
    if not file_storage or not file_storage.filename:
        return None
    if not _ext_ok(file_storage.filename):
        return None
    if not _is_real_image(file_storage):
        return None
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    folder = os.path.join(app.root_path, 'static', 'uploads', 'gallery')
    os.makedirs(folder, exist_ok=True)
    fname = secure_filename(f"{biz_id}-{uuid.uuid4().hex[:8]}.{ext}")
    file_storage.save(os.path.join(folder, fname))
    return f"uploads/gallery/{fname}"

def send_email(to_addr, subject, body):
    # Falls back to console printing if SMTP isn't configured.
    host = os.environ.get('SB_SMTP_HOST', '')
    if not host or not to_addr:

        msg = f"[EMAIL -> {to_addr}] {subject}\n{body}\n"
        try:
            print(msg)
        except UnicodeEncodeError:
            enc = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
            print(msg.encode(enc, errors='replace').decode(enc, errors='replace'))
        return
    try:
        import smtplib
        from email.mime.text import MIMEText

        port = int(os.environ.get('SB_SMTP_PORT', 587))
        user = os.environ.get('SB_SMTP_USER', '')
        pw = os.environ.get('SB_SMTP_PASSWORD', '')
        sender = os.environ.get('SB_SMTP_FROM', user or 'no-reply@smartbook.local')
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to_addr
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            if user:
                s.login(user, pw)
            s.send_message(msg)
    except Exception as e:
        print(f"[EMAIL FAILED -> {to_addr}] {subject}: {e}")

_LOGIN_FAILS = {}
_LOGIN_MAX_FAILS = 5
_LOGIN_WINDOW_SEC = 600

def login_is_blocked(ip):
    now = datetime.now().timestamp()
    fails = [t for t in _LOGIN_FAILS.get(ip, []) if now - t < _LOGIN_WINDOW_SEC]
    _LOGIN_FAILS[ip] = fails
    return len(fails) >= _LOGIN_MAX_FAILS

def login_record_fail(ip):
    _LOGIN_FAILS.setdefault(ip, []).append(datetime.now().timestamp())

def login_clear(ip):
    _LOGIN_FAILS.pop(ip, None)

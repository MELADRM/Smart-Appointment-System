"""SmartBook Pro entry point."""
from datetime import datetime
from flask import Flask, session
from db import load_db
from helpers import CATEGORIES, fmt_slot
from seed import seed_db
from routes import register_all

app = Flask(__name__)
app.secret_key = 'smartbook-v5-secret-2025-xyz'
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024


@app.context_processor
def inject_globals():
    # Makes these variables available in every template.
    notif_count = 0
    pending_apps = 0
    if session.get('user_id'):
        db = load_db()
        notif_count = sum(
            1
            for n in db.get('notifications', [])
            if n['user_id'] == session['user_id'] and not n['read']
        )
        if session.get('role') == 'admin':
            pending_apps = sum(
                1 for a in db.get('business_applications', []) if a['status'] == 'pending'
            )
    return dict(
        now=datetime.now(),
        fmt_slot=fmt_slot,
        notif_count=notif_count,
        pending_apps=pending_apps,
        CATEGORIES=CATEGORIES,
        theme=session.get('theme', 'light'),
    )


register_all(app)


if __name__ == '__main__':
    seed_db()
    app.run(debug=True, port=5000)

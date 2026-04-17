"""Seed default users on first run."""

from datetime import datetime
from werkzeug.security import generate_password_hash
from db import load_db, save_db

def seed_db():
    # Make sure the default users exist and patch any old placeholder IDs.
    db = load_db()
    changed = False

    def ensure_user(uid, name, email, password, role):
        nonlocal changed
        user = next((x for x in db['users'] if x['id'] == uid), None)
        if not user:
            db['users'].append(
                {
                    'id': uid,
                    'name': name,
                    'email': email,
                    'password': generate_password_hash(password),
                    'role': role,
                    'created_at': datetime.now().isoformat(),
                    'is_active': True,
                }
            )
            changed = True
            return

        if user['password'] in ('__SEED__', '__SEED_STAFF__', '__SEED_STAFF2__'):
            user['password'] = generate_password_hash(password)
            changed = True

    ensure_user('u-admin-001', 'Platform Admin', 'admin@smartbook.com', 'admin123', 'admin')
    ensure_user(
        'u-staff-001', 'Dr. Sarah Ahmed', 'sarah@smartbook.com', 'staff123', 'business_owner'
    )
    ensure_user(
        'u-staff-002', 'Dr. James Park', 'james@smartbook.com', 'staff123', 'business_owner'
    )

    for biz in db.get('businesses', []):
        if biz['owner_id'] == '__SEED_STAFF__':
            biz['owner_id'] = 'u-staff-001'
            changed = True
        if biz['owner_id'] == '__SEED_STAFF2__':
            biz['owner_id'] = 'u-staff-002'
            changed = True

    for key in ('business_applications', 'services', 'reviews', 'notifications', 'availability'):
        if key not in db:
            db[key] = []
            changed = True

    approved_owner_ids = {
        b['owner_id'] for b in db.get('businesses', []) if b.get('status') == 'approved'
    }
    for u in db.get('users', []):
        if u.get('role') == 'business_owner' and u['id'] not in approved_owner_ids:
            u['role'] = 'user'
            changed = True
    if changed:
        save_db(db)

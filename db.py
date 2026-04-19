"""MySQL-backed persistence layer."""

import re
import uuid
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import mysql.connector
from mysql.connector import pooling
from config import DB_CONFIG

_POOL = pooling.MySQLConnectionPool(pool_name='smartbook_pool', pool_size=5, **DB_CONFIG)

def _conn():
    return _POOL.get_connection()

def new_id(prefix='id'):
    # Short unique ID like 'u-ab12cd34ef'.
    return f"{prefix}-{uuid.uuid4().hex[:10]}"

def slugify(text):
    # 'Dr. Ahmed Clinic!' -> 'dr-ahmed-clinic'.
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:60]

def unique_slug(base, existing_slugs):
    # Append -2, -3 ... if the slug is already taken.
    slug = slugify(base)
    if slug not in existing_slugs:
        return slug
    for i in range(2, 100):
        candidate = f"{slug}-{i}"
        if candidate not in existing_slugs:
            return candidate
    return f"{slug}-{uuid.uuid4().hex[:6]}"

def _dt_to_str(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)

def _date_to_str(v):
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v.isoformat()
    return str(v)

def _time_to_str(v):
    if v is None:
        return None
    if isinstance(v, timedelta):
        total = int(v.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    if isinstance(v, time):
        return v.strftime('%H:%M')
    return str(v)[:5]

def _money(v):
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)

def _bool(v):
    return bool(v) if v is not None else False

def _slots(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, (bytes, bytearray)):
        v = v.decode('utf-8')
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return []

def load_db():
    # Read every table into the dict-of-lists shape the app expects.
    cnx = _conn()
    try:
        cur = cnx.cursor(dictionary=True)

        cur.execute("SELECT * FROM users")
        users = []
        for r in cur.fetchall():
            users.append(
                {
                    'id': r['id'],
                    'name': r['name'],
                    'email': r['email'],
                    'password': r['password'],
                    'role': r['role'],
                    'is_active': _bool(r['is_active']),
                    'created_at': _dt_to_str(r['created_at']),
                }
            )

        cur.execute("SELECT * FROM businesses")
        businesses = []
        for r in cur.fetchall():
            businesses.append(
                {
                    'id': r['id'],
                    'owner_id': r['owner_id'],
                    'name': r['name'],
                    'slug': r['slug'],
                    'category': r['category'],
                    'description': r['description'] or '',
                    'phone': r['phone'] or '',
                    'email': r['email'] or '',
                    'address': r['address'] or '',
                    'website': r['website'] or '',
                    'logo_initial': r['logo_initial'] or '',
                    'logo_color': r['logo_color'] or '',
                    'logo_url': r['logo_url'] or '',
                    'owner_bio': r['owner_bio'] or '',
                    'status': r['status'],
                    'featured': _bool(r['featured']),
                    'created_at': _dt_to_str(r['created_at']),
                    'approved_at': _dt_to_str(r['approved_at']),
                }
            )

        cur.execute("SELECT * FROM business_applications")
        apps = []
        for r in cur.fetchall():
            apps.append(
                {
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'user_name': r['user_name'] or '',
                    'name': r['name'],
                    'category': r['category'],
                    'description': r['description'] or '',
                    'phone': r['phone'] or '',
                    'email': r['email'] or '',
                    'address': r['address'] or '',
                    'status': r['status'],
                    'reject_reason': r['reject_reason'] or '',
                    'created_at': _dt_to_str(r['created_at']),
                    'approved_at': _dt_to_str(r['approved_at']),
                    'rejected_at': _dt_to_str(r['rejected_at']),
                }
            )

        cur.execute("SELECT * FROM services")
        services = []
        for r in cur.fetchall():
            services.append(
                {
                    'id': r['id'],
                    'business_id': r['business_id'],
                    'name': r['name'],
                    'duration_min': r['duration_min'],
                    'price': _money(r['price']),
                    'description': r['description'] or '',
                }
            )

        cur.execute("SELECT * FROM availability")
        avail = []
        for r in cur.fetchall():
            avail.append(
                {
                    'id': r['id'],
                    'biz_id': r['biz_id'],
                    'date': _date_to_str(r['date']),
                    'slots': _slots(r['slots']),
                    'created_at': _dt_to_str(r['created_at']),
                    'updated_at': _dt_to_str(r['updated_at']),
                }
            )

        cur.execute("SELECT * FROM appointments")
        appts = []
        for r in cur.fetchall():
            appts.append(
                {
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'biz_id': r['biz_id'],
                    'service_id': r['service_id'],
                    'date': _date_to_str(r['date']),
                    'time': _time_to_str(r['time']),
                    'duration_min': int(r['duration_min'] or 30),
                    'notes': r['notes'] or '',
                    'reason': r['reason'] or '',
                    'status': r['status'],
                    'admin_override': _bool(r['admin_override']),
                    'created_at': _dt_to_str(r['created_at']),
                    'updated_at': _dt_to_str(r['updated_at']),
                    'cancelled_at': _dt_to_str(r['cancelled_at']),
                    'rescheduled_at': _dt_to_str(r['rescheduled_at']),
                }
            )

        cur.execute("SELECT * FROM reviews")
        reviews = []
        for r in cur.fetchall():
            reviews.append(
                {
                    'id': r['id'],
                    'appt_id': r['appt_id'],
                    'biz_id': r['biz_id'],
                    'user_id': r['user_id'],
                    'rating': int(r['rating']),
                    'comment': r['comment'] or '',
                    'owner_reply': r.get('owner_reply') or '',
                    'owner_reply_at': _dt_to_str(r.get('owner_reply_at')),
                    'created_at': _dt_to_str(r['created_at']),
                }
            )

        cur.execute("SELECT * FROM notifications")
        notifs = []
        for r in cur.fetchall():
            notifs.append(
                {
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'message': r['message'],
                    'kind': r['kind'],
                    'read': _bool(r['is_read']),
                    'created_at': _dt_to_str(r['created_at']),
                }
            )

        cur.execute("SELECT * FROM password_resets")
        resets = []
        for r in cur.fetchall():
            resets.append(
                {
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'token': r['token'],
                    'expires_at': _dt_to_str(r['expires_at']),
                    'used': _bool(r['used']),
                    'created_at': _dt_to_str(r['created_at']),
                }
            )

        cur.execute("SELECT * FROM admin_actions")
        actions = []
        for r in cur.fetchall():
            actions.append(
                {
                    'id': r['id'],
                    'actor_id': r['actor_id'] or '',
                    'actor_name': r['actor_name'] or '',
                    'action': r['action'],
                    'target_type': r['target_type'] or '',
                    'target_id': r['target_id'] or '',
                    'detail': r['detail'] or '',
                    'created_at': _dt_to_str(r['created_at']),
                }
            )

        cur.execute("SELECT * FROM business_images")
        images = []
        for r in cur.fetchall():
            images.append(
                {
                    'id': r['id'],
                    'business_id': r['business_id'],
                    'url': r['url'],
                    'caption': r['caption'] or '',
                    'sort_order': int(r['sort_order'] or 0),
                    'created_at': _dt_to_str(r['created_at']),
                }
            )

        cur.execute("SELECT * FROM business_hours")
        hours = []
        for r in cur.fetchall():
            hours.append(
                {
                    'id': r['id'],
                    'business_id': r['business_id'],
                    'weekday': int(r['weekday']),
                    'open_time': _time_to_str(r['open_time']),
                    'close_time': _time_to_str(r['close_time']),
                    'is_closed': _bool(r['is_closed']),
                }
            )
        cur.close()
        return {
            'users': users,
            'businesses': businesses,
            'business_applications': apps,
            'services': services,
            'availability': avail,
            'appointments': appts,
            'reviews': reviews,
            'notifications': notifs,
            'password_resets': resets,
            'admin_actions': actions,
            'business_images': images,
            'business_hours': hours,
        }
    finally:
        cnx.close()

def _s(v):
    return v if v not in ('', None) else None

def save_db(db):
    # Wipe every table and re-insert every row from the given dict.
    cnx = _conn()
    try:
        cur = cnx.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")

        for t in (
            'business_hours',
            'business_images',
            'admin_actions',
            'password_resets',
            'notifications',
            'reviews',
            'appointments',
            'availability',
            'services',
            'business_applications',
            'businesses',
            'users',
        ):
            cur.execute(f"DELETE FROM {t}")

        cur.executemany(
            """INSERT INTO users
               (id, name, email, password, role, is_active, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    u['id'],
                    u['name'],
                    u['email'],
                    u['password'],
                    u.get('role', 'user'),
                    bool(u.get('is_active', True)),
                    u.get('created_at'),
                )
                for u in db.get('users', [])
            ],
        )

        cur.executemany(
            """INSERT INTO businesses
               (id, owner_id, name, slug, category, description,
                phone, email, address, website,
                logo_initial, logo_color, logo_url, owner_bio,
                status, featured,
                created_at, approved_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    b['id'],
                    b['owner_id'],
                    b['name'],
                    b['slug'],
                    b['category'],
                    _s(b.get('description')),
                    _s(b.get('phone')),
                    _s(b.get('email')),
                    _s(b.get('address')),
                    _s(b.get('website')),
                    _s(b.get('logo_initial')),
                    _s(b.get('logo_color')),
                    _s(b.get('logo_url')),
                    _s(b.get('owner_bio')),
                    b.get('status', 'pending'),
                    bool(b.get('featured', False)),
                    b.get('created_at'),
                    b.get('approved_at'),
                )
                for b in db.get('businesses', [])
            ],
        )

        cur.executemany(
            """INSERT INTO business_applications
               (id, user_id, user_name, name, category, description,
                phone, email, address, status, reject_reason,
                created_at, approved_at, rejected_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    a['id'],
                    a['user_id'],
                    _s(a.get('user_name')),
                    a['name'],
                    a['category'],
                    _s(a.get('description')),
                    _s(a.get('phone')),
                    _s(a.get('email')),
                    _s(a.get('address')),
                    a.get('status', 'pending'),
                    _s(a.get('reject_reason')),
                    a.get('created_at'),
                    a.get('approved_at'),
                    a.get('rejected_at'),
                )
                for a in db.get('business_applications', [])
            ],
        )

        cur.executemany(
            """INSERT INTO services
               (id, business_id, name, duration_min, price, description)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    s['id'],
                    s['business_id'],
                    s['name'],
                    int(s.get('duration_min', 30)),
                    float(s.get('price', 0) or 0),
                    _s(s.get('description')),
                )
                for s in db.get('services', [])
            ],
        )

        cur.executemany(
            """INSERT INTO availability
               (id, biz_id, date, slots, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    a['id'],
                    a['biz_id'],
                    a['date'],
                    json.dumps(a.get('slots', []) or []),
                    a.get('created_at'),
                    a.get('updated_at'),
                )
                for a in db.get('availability', [])
            ],
        )

        cur.executemany(
            """INSERT INTO appointments
               (id, user_id, biz_id, service_id, date, time, duration_min,
                notes, reason, status, admin_override,
                created_at, updated_at, cancelled_at, rescheduled_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    ap['id'],
                    ap['user_id'],
                    ap['biz_id'],
                    _s(ap.get('service_id')),
                    ap['date'],
                    ap['time'],
                    int(ap.get('duration_min', 30) or 30),
                    _s(ap.get('notes')),
                    _s(ap.get('reason')),
                    ap.get('status', 'booked'),
                    bool(ap.get('admin_override', False)),
                    ap.get('created_at'),
                    ap.get('updated_at'),
                    ap.get('cancelled_at'),
                    ap.get('rescheduled_at'),
                )
                for ap in db.get('appointments', [])
            ],
        )

        cur.executemany(
            """INSERT INTO reviews
               (id, appt_id, biz_id, user_id, rating, comment,
                owner_reply, owner_reply_at, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    r['id'],
                    r['appt_id'],
                    r['biz_id'],
                    r['user_id'],
                    int(r.get('rating', 5)),
                    _s(r.get('comment')),
                    _s(r.get('owner_reply')),
                    r.get('owner_reply_at'),
                    r.get('created_at'),
                )
                for r in db.get('reviews', [])
            ],
        )

        cur.executemany(
            """INSERT INTO notifications
               (id, user_id, message, kind, is_read, created_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    n['id'],
                    n['user_id'],
                    n['message'],
                    n.get('kind', 'info'),
                    bool(n.get('read', False)),
                    n.get('created_at'),
                )
                for n in db.get('notifications', [])
            ],
        )

        cur.executemany(
            """INSERT INTO password_resets
               (id, user_id, token, expires_at, used, created_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    p['id'],
                    p['user_id'],
                    p['token'],
                    p.get('expires_at'),
                    bool(p.get('used', False)),
                    p.get('created_at'),
                )
                for p in db.get('password_resets', [])
            ],
        )

        cur.executemany(
            """INSERT INTO admin_actions
               (id, actor_id, actor_name, action, target_type,
                target_id, detail, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            [
                (
                    a['id'],
                    _s(a.get('actor_id')),
                    _s(a.get('actor_name')),
                    a['action'],
                    _s(a.get('target_type')),
                    _s(a.get('target_id')),
                    _s(a.get('detail')),
                    a.get('created_at'),
                )
                for a in db.get('admin_actions', [])
            ],
        )

        cur.executemany(
            """INSERT INTO business_images
               (id, business_id, url, caption, sort_order, created_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    i['id'],
                    i['business_id'],
                    i['url'],
                    _s(i.get('caption')),
                    int(i.get('sort_order', 0) or 0),
                    i.get('created_at'),
                )
                for i in db.get('business_images', [])
            ],
        )

        cur.executemany(
            """INSERT INTO business_hours
               (id, business_id, weekday, open_time, close_time, is_closed)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    h['id'],
                    h['business_id'],
                    int(h.get('weekday', 0)),
                    _s(h.get('open_time')),
                    _s(h.get('close_time')),
                    bool(h.get('is_closed', False)),
                )
                for h in db.get('business_hours', [])
            ],
        )
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        cnx.commit()
        cur.close()
    except Exception:
        cnx.rollback()
        raise
    finally:
        cnx.close()

"""Helpers and constants used across the app."""

import re
from datetime import datetime
from db import new_id

PHONE_RE = re.compile(r'^\+?[\d\s\-().]{7,25}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')
TIME_RE = re.compile(r'^\d{2}:\d{2}$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def clean_phone(raw):
    # Returns cleaned phone, '' for empty input, or None if invalid.
    if not raw:
        return ''
    raw = raw.strip()
    if not raw:
        return ''

    cleaned = re.sub(r'\s+', ' ', raw)
    if not PHONE_RE.match(cleaned):
        return None

    digits = re.sub(r'[^\d+]', '', cleaned)
    if len(re.sub(r'\D', '', digits)) < 7:
        return None
    return cleaned


def is_valid_email(s):
    return bool(s) and bool(EMAIL_RE.match(s.strip()))


def is_valid_url(s):
    # Empty input counts as valid (website is optional).
    if not s:
        return True
    s = s.strip().lower()
    return s.startswith('http://') or s.startswith('https://')


def is_valid_hex_color(s):
    return bool(s) and bool(HEX_COLOR_RE.match(s.strip()))


def is_valid_date(s):
    if not s or not DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def is_valid_time(s):
    if not s or not TIME_RE.match(s):
        return False
    try:
        h, m = map(int, s.split(':'))
        return 0 <= h < 24 and 0 <= m < 60
    except ValueError:
        return False


def safe_int(v, default=0, lo=None, hi=None):
    # int() that never raises; clamps to [lo, hi] if given.
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return default
    if lo is not None and n < lo:
        n = lo
    if hi is not None and n > hi:
        n = hi
    return n


def safe_float(v, default=0.0, lo=None, hi=None):
    # float() that never raises; clamps to [lo, hi] if given.
    try:
        n = float(str(v).strip())
    except (TypeError, ValueError):
        return default
    if lo is not None and n < lo:
        n = lo
    if hi is not None and n > hi:
        n = hi
    return n


ALL_SLOTS = [
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
    "13:00",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
    "15:30",
    "16:00",
    "16:30",
    "17:00",
    "17:30",
]


def slots_between(open_time, close_time):
    # Return the slots inside [open_time, close_time); '[]' if either side is blank.
    if not open_time or not close_time:
        return []
    return [s for s in ALL_SLOTS if open_time <= s < close_time]


CATEGORIES = [
    "Healthcare",
    "Dentistry",
    "Cardiology",
    "Dermatology",
    "Physiotherapy",
    "Mental Health",
    "Nutrition",
    "Veterinary",
    "Beauty & Wellness",
    "Legal",
    "Financial",
    "Education",
    "Fitness",
]


def fmt_slot(s):
    # '14:30' -> '02:30 PM' for templates.
    h, m = map(int, s.split(':'))
    p = 'AM' if h < 12 else 'PM'
    hd = h if 1 <= h <= 12 else (12 if h == 0 else h - 12)
    return f"{hd:02d}:{m:02d} {p}"


def get_user(uid, db):
    return next((u for u in db['users'] if u['id'] == uid), None)


def get_biz_for_owner(owner_id, db):
    # Approved business belonging to this owner, if any.
    return next(
        (b for b in db['businesses'] if b['owner_id'] == owner_id and b['status'] == 'approved'),
        None,
    )


def enrich_appointments(appts, db):
    # Add user_name / business_name / service_name fields for templates.
    umap = {u['id']: u for u in db['users']}
    bmap = {b['id']: b for b in db['businesses']}
    svmap = {s['id']: s for s in db.get('services', [])}
    for a in appts:
        a['user_name'] = umap.get(a.get('user_id'), {}).get('name', '—')
        a['business_name'] = bmap.get(a.get('biz_id'), {}).get('name', '—')
        a['service_name'] = svmap.get(a.get('service_id'), {}).get('name', a.get('reason', '—'))
    return appts


def slots_needed(duration_min):
    # How many 30-minute slots fit `duration_min` (always at least 1).
    try:
        d = int(duration_min or 30)
    except (TypeError, ValueError):
        d = 30
    return max(1, (d + 29) // 30)


def slot_range(start_time, duration_min):
    # Slots a booking starting at `start_time` would occupy.
    if start_time not in ALL_SLOTS:
        return [start_time]
    idx = ALL_SLOTS.index(start_time)
    n = slots_needed(duration_min)
    return ALL_SLOTS[idx : idx + n]


def slots_for_day(biz_id, date, db, duration_min=30):
    # Every slot for a date, each marked taken/free.
    # Format: [{'time': '09:00', 'display': '09:00 AM', 'taken': False}, ...]
    avail = next(
        (av for av in db['availability'] if av['biz_id'] == biz_id and av['date'] == date),
        None,
    )
    open_slots = avail['slots'] if avail else ALL_SLOTS

    svmap = {s['id']: s for s in db.get('services', [])}
    booked = set()
    for ap in db['appointments']:
        if ap['biz_id'] != biz_id or ap['date'] != date or ap['status'] != 'booked':
            continue
        dur = (
            ap.get('duration_min') or svmap.get(ap.get('service_id'), {}).get('duration_min') or 30
        )
        for t in slot_range(ap['time'], dur):
            booked.add(t)
    need = slots_needed(duration_min)
    out = []
    for s in open_slots:

        rng = slot_range(s, duration_min * 1)
        too_long = False
        overlap = any(t in booked for t in rng) or any(t not in open_slots for t in rng)
        out.append(
            {
                'time': s,
                'display': fmt_slot(s),
                'taken': (s in booked) or too_long or overlap,
            }
        )
    return out


def suggest_slot(biz_id, date, requested, db):
    # Next free slot the same day, or None if the day is full.
    slots = slots_for_day(biz_id, date, db)
    free = [s['time'] for s in slots if not s['taken']]
    if not free:
        return None
    try:
        idx = ALL_SLOTS.index(requested)
        for s in ALL_SLOTS[idx + 1 :]:
            if s in free:
                return s
    except ValueError:
        pass
    return free[0]


def add_notification(db, user_id, msg, kind='info'):
    # Caller must run save_db() afterwards.
    db['notifications'].append(
        {
            'id': new_id('n'),
            'user_id': user_id,
            'message': msg,
            'kind': kind,
            'read': False,
            'created_at': datetime.now().isoformat(),
        }
    )


def log_admin_action(db, actor_id, actor_name, action, target_type, target_id, detail=''):
    # Add a row to the admin audit log. Caller must run save_db() afterwards.
    db.setdefault('admin_actions', []).append(
        {
            'id': new_id('log'),
            'actor_id': actor_id,
            'actor_name': actor_name,
            'action': action,
            'target_type': target_type,
            'target_id': target_id,
            'detail': detail,
            'created_at': datetime.now().isoformat(),
        }
    )

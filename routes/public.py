"""Routes anyone can visit."""

from datetime import datetime
import calendar as _calendar
from flask import abort, flash, redirect, render_template, request, session, url_for
from db import load_db, save_db, new_id
from decorators import login_required
from helpers import (
    ALL_SLOTS,
    CATEGORIES,
    fmt_slot,
    get_user,
    is_valid_date,
    is_valid_time,
    safe_int,
    slot_range,
    slots_for_day,
    slots_needed,
    suggest_slot,
    add_notification,
)
from app_utils import send_email

def register(app):
    @app.route('/toggle-theme', methods=['POST'])
    def toggle_theme():
        session['theme'] = 'dark' if session.get('theme') != 'dark' else 'light'
        return redirect(request.form.get('next') or request.referrer or url_for('home'))

    @app.route('/')
    def home():
        # Landing page: hero + featured businesses + quick stats.
        db = load_db()
        approved = [b for b in db['businesses'] if b['status'] == 'approved']
        featured = [b for b in approved if b.get('featured')]
        stats = {
            'businesses': len(approved),
            'appointments': len(db['appointments']),
            'users': len([u for u in db['users'] if u['role'] == 'user']),
        }

        today = datetime.today().date()
        cal = _calendar.Calendar(firstweekday=6)
        hero_weeks = cal.monthdatescalendar(today.year, today.month)
        hero_month = today.strftime('%B %Y')
        return render_template(
            'public/home.html',
            featured=featured,
            all_businesses=approved,
            stats=stats,
            CATEGORIES=CATEGORIES,
            hero_weeks=hero_weeks,
            hero_month=hero_month,
            hero_today=today,
        )

    @app.route('/explore')
    def explore():
        # Browse + search approved businesses by category / keyword.
        db = load_db()
        cat = request.args.get('cat', '')
        q = request.args.get('q', '').strip().lower()
        bizs = [b for b in db['businesses'] if b['status'] == 'approved']
        if cat:
            bizs = [b for b in bizs if b.get('category') == cat]
        if q:
            bizs = [
                b
                for b in bizs
                if q in b['name'].lower()
                or q in b.get('description', '').lower()
                or q in b.get('address', '').lower()
                or q in b.get('category', '').lower()
            ]
        return render_template(
            'public/explore.html', businesses=bizs, cat=cat, q=q, CATEGORIES=CATEGORIES
        )

    @app.route('/b/<slug>')
    def business_page(slug):
        # Public-facing page for a single business (services, reviews, gallery).
        db = load_db()
        biz = next(
            (b for b in db['businesses'] if b['slug'] == slug and b['status'] == 'approved'), None
        )
        if not biz:
            abort(404)
        services = [s for s in db.get('services', []) if s['business_id'] == biz['id']]
        reviews = [r for r in db.get('reviews', []) if r['biz_id'] == biz['id']]
        gallery = [i for i in db.get('business_images', []) if i['business_id'] == biz['id']]
        gallery.sort(key=lambda i: i.get('sort_order', 0))
        umap = {u['id']: u for u in db['users']}
        for r in reviews:
            r['reviewer_name'] = umap.get(r['user_id'], {}).get('name', 'Anonymous')
        owner = umap.get(biz.get('owner_id'))
        avg_rating = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else None
        return render_template(
            'public/business.html',
            biz=biz,
            services=services,
            reviews=reviews,
            avg_rating=avg_rating,
            gallery=gallery,
            owner=owner,
        )

    @app.route('/b/<slug>/book', methods=['GET', 'POST'])
    @login_required
    def public_book(slug):
        # Server-rendered calendar + slot picker. POST confirms the booking.
        db = load_db()
        biz = next(
            (b for b in db['businesses'] if b['slug'] == slug and b['status'] == 'approved'), None
        )
        if not biz:
            abort(404)
        services = [s for s in db.get('services', []) if s['business_id'] == biz['id']]

        if request.method == 'POST':
            date = request.form.get('date', '').strip()
            time = request.form.get('time', '').strip()
            service_id = request.form.get('service_id', '').strip()
            notes = request.form.get('notes', '').strip()[:500]
            if not is_valid_date(date):
                flash('Please select a valid date.', 'danger')
                return redirect(url_for('public_book', slug=slug))
            if datetime.strptime(date, '%Y-%m-%d').date() < datetime.today().date():
                flash('Please select a future date.', 'danger')
                return redirect(url_for('public_book', slug=slug))
            if not is_valid_time(time) or time not in ALL_SLOTS:
                flash('Please pick a valid time slot.', 'danger')
                return redirect(url_for('public_book', slug=slug, date=date))
            svc = next((s for s in services if s['id'] == service_id), None) if service_id else None
            if service_id and not svc:
                flash('That service is not available at this business.', 'danger')
                return redirect(url_for('public_book', slug=slug, date=date))
            duration = safe_int((svc or {}).get('duration_min'), default=30, lo=5, hi=480)
            needed_slots = slot_range(time, duration)
            avail = next(
                (
                    av
                    for av in db['availability']
                    if av['biz_id'] == biz['id'] and av['date'] == date
                ),
                None,
            )
            open_slots = avail['slots'] if avail else ALL_SLOTS
            if any(t not in open_slots for t in needed_slots) or len(needed_slots) < slots_needed(
                duration
            ):
                sug = suggest_slot(biz['id'], date, time, db)
                msg = 'That slot is outside the business hours for a ' f'{duration}-minute booking.'
                if sug:
                    msg += f' 💡 Try <strong>{fmt_slot(sug)}</strong> instead.'
                flash(msg, 'warning')
                return redirect(url_for('public_book', slug=slug, date=date))
            day_slots = slots_for_day(biz['id'], date, db, duration_min=duration)
            day_taken = {s['time']: s['taken'] for s in day_slots}
            if day_taken.get(time, True):
                sug = suggest_slot(biz['id'], date, time, db)
                msg = 'That slot overlaps with an existing booking.'
                if sug:
                    msg += f' 💡 <strong>{fmt_slot(sug)}</strong> is free!'
                flash(msg, 'warning')
                return redirect(url_for('public_book', slug=slug, date=date))
            appt = {
                'id': new_id('ap'),
                'user_id': session['user_id'],
                'biz_id': biz['id'],
                'service_id': service_id,
                'date': date,
                'time': time,
                'duration_min': duration,
                'notes': notes or '',
                'reason': svc['name'] if svc else 'Appointment',
                'status': 'booked',
                'created_at': datetime.now().isoformat(),
            }
            db['appointments'].append(appt)
            add_notification(
                db,
                biz['owner_id'],
                f"New booking: {session['user_name']} on {date} at {fmt_slot(time)}",
                'success',
            )
            save_db(db)

            customer = get_user(session['user_id'], db)
            owner = get_user(biz['owner_id'], db)
            svc_name = svc['name'] if svc else 'Appointment'
            if customer and customer.get('email'):
                send_email(
                    customer['email'],
                    f'Booking confirmed — {biz["name"]}',
                    f'Hi {customer["name"]},\n\n'
                    f'Your appointment at {biz["name"]} is confirmed:\n'
                    f'  • Date:    {date}\n'
                    f'  • Time:    {fmt_slot(time)}\n'
                    f'  • Service: {svc_name} ({duration} min)\n\n'
                    'You can view or cancel it from "My Appointments".\n\n'
                    '— The SmartBook team',
                )
            if owner and owner.get('email'):
                send_email(
                    owner['email'],
                    f'New booking at {biz["name"]}',
                    f'Hi {owner["name"]},\n\n'
                    f'{customer["name"] if customer else "A customer"} just booked '
                    f'{svc_name} on {date} at {fmt_slot(time)}.\n\n'
                    'Open your dashboard to see details.\n\n'
                    '— SmartBook',
                )
            flash(
                f'✅ Booked at <strong>{biz["name"]}</strong> for {date} at {fmt_slot(time)}!',
                'success',
            )
            return redirect(url_for('user_my_appointments', just_booked=1))

        today = datetime.today().date()
        year = safe_int(request.args.get('year'), default=today.year, lo=1970, hi=2100)
        month = safe_int(request.args.get('month'), default=today.month, lo=1, hi=12)
        selected_date = request.args.get('date', '').strip() or None
        selected_time = request.args.get('time', '').strip() or None
        cal = _calendar.Calendar(firstweekday=6)
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            row = []
            for d in week:
                in_month = d.month == month
                ds = d.strftime('%Y-%m-%d')
                cell = {
                    'day': d.day,
                    'date_str': ds,
                    'in_month': in_month,
                    'past': d < today,
                    'today': d == today,
                    'selected': ds == selected_date,
                    'weekend': d.weekday() >= 5,
                }
                if in_month and d >= today:
                    slots = slots_for_day(biz['id'], ds, db)
                    free_count = sum(1 for s in slots if not s['taken'])
                    if free_count == 0 and slots:
                        cell['all_booked'] = True
                    elif free_count > 0:
                        cell['has_free'] = True
                row.append(cell)
            weeks.append(row)
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        is_current_month = year == today.year and month == today.month
        slots_am, slots_pm, selected_date_obj = [], [], None
        if selected_date:
            try:
                selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                day_slots = slots_for_day(biz['id'], selected_date, db)
                slots_am = [s for s in day_slots if 'AM' in s['display']]
                slots_pm = [s for s in day_slots if 'PM' in s['display']]
            except ValueError:
                selected_date = None
        return render_template(
            'public/book.html',
            biz=biz,
            services=services,
            year=year,
            month=month,
            month_name=_calendar.month_name[month],
            weeks=weeks,
            prev_year=prev_year,
            prev_month=prev_month,
            next_year=next_year,
            next_month=next_month,
            is_current_month=is_current_month,
            selected_date=selected_date,
            selected_date_obj=selected_date_obj,
            selected_time=selected_time,
            slots_am=slots_am,
            slots_pm=slots_pm,
        )

    @app.errorhandler(404)
    def not_found(e):
        return render_template('public/404.html'), 404

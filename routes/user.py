"""Customer-facing routes."""

from datetime import datetime
from flask import flash, redirect, render_template, request, session, url_for
from db import load_db, save_db, new_id
from decorators import login_required
from helpers import (
    CATEGORIES,
    add_notification,
    clean_phone,
    enrich_appointments,
    fmt_slot,
    is_valid_email,
    safe_int,
    suggest_slot,
)

def register(app):
    @app.route('/dashboard')
    @login_required
    def dashboard():
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        if role == 'business_owner':
            return redirect(url_for('biz_dashboard'))
        return redirect(url_for('user_dashboard'))

    @app.route('/user/dashboard')
    @login_required
    def user_dashboard():
        db = load_db()
        uid = session['user_id']
        appts = [ap for ap in db['appointments'] if ap['user_id'] == uid]
        appts = sorted(appts, key=lambda x: (x['date'], x['time']), reverse=True)
        enrich_appointments(appts, db)
        pending_app = next(
            (
                a
                for a in db['business_applications']
                if a['user_id'] == uid and a['status'] == 'pending'
            ),
            None,
        )
        notifs = [n for n in db.get('notifications', []) if n['user_id'] == uid][-5:][::-1]
        for n in db.get('notifications', []):
            if n['user_id'] == uid:
                n['read'] = True
        save_db(db)
        stats = {
            'total': len(appts),
            'booked': sum(1 for a in appts if a['status'] == 'booked'),
            'completed': sum(1 for a in appts if a['status'] == 'completed'),
            'cancelled': sum(1 for a in appts if a['status'] == 'cancelled'),
            'no_show': sum(1 for a in appts if a['status'] == 'no_show'),
        }
        return render_template(
            'user/dashboard.html',
            appointments=appts[:5],
            stats=stats,
            pending_app=pending_app,
            notifs=notifs,
        )

    @app.route('/user/appointments')
    @login_required
    def user_my_appointments():
        db = load_db()
        appts = [ap for ap in db['appointments'] if ap['user_id'] == session['user_id']]
        appts = sorted(appts, key=lambda x: (x['date'], x['time']), reverse=True)
        enrich_appointments(appts, db)
        return render_template('user/my_appointments.html', appointments=appts)

    @app.route('/user/cancel/<appt_id>', methods=['POST'])
    @login_required
    def user_cancel(appt_id):
        db = load_db()
        appt = next(
            (
                a
                for a in db['appointments']
                if a['id'] == appt_id and a['user_id'] == session['user_id']
            ),
            None,
        )
        if not appt:
            flash('Appointment not found.', 'danger')
        elif appt['status'] != 'booked':
            flash('Only active bookings can be cancelled.', 'warning')
        else:
            biz = next((b for b in db['businesses'] if b['id'] == appt['biz_id']), None)
            appt['status'] = 'cancelled'
            appt['cancelled_at'] = datetime.now().isoformat()
            if biz:
                add_notification(
                    db,
                    biz['owner_id'],
                    f"{session['user_name']} cancelled their booking on {appt['date']}",
                    'warning',
                )
            save_db(db)
            flash('Appointment cancelled.', 'success')
        return redirect(url_for('user_my_appointments'))

    @app.route('/user/reschedule/<appt_id>', methods=['GET', 'POST'])
    @login_required
    def user_reschedule(appt_id):
        db = load_db()
        appt = next(
            (
                a
                for a in db['appointments']
                if a['id'] == appt_id and a['user_id'] == session['user_id']
            ),
            None,
        )
        if not appt or appt['status'] != 'booked':
            flash('Cannot reschedule this appointment.', 'danger')
            return redirect(url_for('user_my_appointments'))
        biz = next((b for b in db['businesses'] if b['id'] == appt['biz_id']), None)
        if request.method == 'POST':
            new_date = request.form.get('date', '').strip()
            new_time = request.form.get('time', '').strip()
            try:
                if datetime.strptime(new_date, '%Y-%m-%d').date() < datetime.today().date():
                    flash('Select a future date.', 'danger')
                    return render_template('user/reschedule.html', appt=appt, biz=biz)
            except ValueError:
                flash('Invalid date.', 'danger')
                return render_template('user/reschedule.html', appt=appt, biz=biz)
            clash = any(
                a
                for a in db['appointments']
                if a['biz_id'] == appt['biz_id']
                and a['date'] == new_date
                and a['time'] == new_time
                and a['status'] == 'booked'
                and a['id'] != appt_id
            )
            if clash:
                sug = suggest_slot(appt['biz_id'], new_date, new_time, db)
                msg = 'Slot already taken.'
                if sug:
                    msg += f' Try <strong>{fmt_slot(sug)}</strong>.'
                flash(msg, 'warning')
                return render_template('user/reschedule.html', appt=appt, biz=biz)
            appt['date'] = new_date
            appt['time'] = new_time
            appt['rescheduled_at'] = datetime.now().isoformat()
            save_db(db)
            flash(f'Rescheduled to {new_date} at {fmt_slot(new_time)}.', 'success')
            return redirect(url_for('user_my_appointments'))
        return render_template('user/reschedule.html', appt=appt, biz=biz)

    @app.route('/user/review/<appt_id>', methods=['GET', 'POST'])
    @login_required
    def leave_review(appt_id):
        db = load_db()
        appt = next(
            (
                a
                for a in db['appointments']
                if a['id'] == appt_id
                and a['user_id'] == session['user_id']
            ),
            None,
        )
        if not appt:
            flash('You can only review completed appointments.', 'warning')
            return redirect(url_for('user_my_appointments'))
        already = any(r for r in db.get('reviews', []) if r['appt_id'] == appt_id)
        if already:
            flash('You already left a review for this appointment.', 'info')
            return redirect(url_for('user_my_appointments'))
        biz = next((b for b in db['businesses'] if b['id'] == appt['biz_id']), None)
        if request.method == 'POST':
            rating = safe_int(request.form.get('rating'), default=5, lo=1, hi=5)
            comment = request.form.get('comment', '').strip()[:1000]
            db['reviews'].append(
                {
                    'id': new_id('rv'),
                    'appt_id': appt_id,
                    'biz_id': appt['biz_id'],
                    'user_id': session['user_id'],
                    'rating': rating,
                    'comment': comment,
                    'created_at': datetime.now().isoformat(),
                }
            )
            save_db(db)
            flash('Review submitted! Thank you.', 'success')
            return redirect(url_for('user_my_appointments'))
        return render_template('user/review.html', appt=appt, biz=biz)

    @app.route('/apply', methods=['GET', 'POST'])
    @login_required
    def apply_business():
        # Lets a regular user apply to list their own business.
        db = load_db()
        uid = session['user_id']
        if session.get('role') == 'business_owner':
            flash('You already own a business.', 'info')
            return redirect(url_for('biz_dashboard'))
        existing = next(
            (
                a
                for a in db['business_applications']
                if a['user_id'] == uid and a['status'] == 'pending'
            ),
            None,
        )
        if existing:
            flash('You already have a pending application.', 'info')
            return redirect(url_for('user_dashboard'))
        if request.method == 'POST':
            name = request.form.get('name', '').strip()[:150]
            category = request.form.get('category', '').strip()
            desc = request.form.get('description', '').strip()[:2000]
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()[:255]
            email = request.form.get('email', '').strip().lower()
            if not all([name, category, desc]) or len(name) < 2 or len(desc) < 10:
                flash(
                    'Business name, category and description are required '
                    '(description must be at least 10 characters).',
                    'danger',
                )
                return render_template('user/apply.html', CATEGORIES=CATEGORIES)
            if category not in CATEGORIES:
                flash('Please pick a valid category.', 'danger')
                return render_template('user/apply.html', CATEGORIES=CATEGORIES)
            if email and not is_valid_email(email):
                flash('Please enter a valid business email address.', 'danger')
                return render_template('user/apply.html', CATEGORIES=CATEGORIES)
            cleaned_phone = clean_phone(phone)
            if cleaned_phone is None:
                flash(
                    'Phone number looks invalid. Digits, spaces, and + - ( ) '
                    'only (7–25 characters).',
                    'danger',
                )
                return render_template('user/apply.html', CATEGORIES=CATEGORIES)
            db['business_applications'].append(
                {
                    'id': new_id('app'),
                    'user_id': uid,
                    'user_name': session['user_name'],
                    'name': name,
                    'category': category,
                    'description': desc,
                    'phone': cleaned_phone,
                    'address': address,
                    'email': email,
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                }
            )

            for u in db['users']:
                if u['role'] == 'admin':
                    add_notification(
                        db,
                        u['id'],
                        f"New business application: <strong>{name}</strong> by {session['user_name']}",
                        'info',
                    )
            save_db(db)
            flash('✅ Application submitted! The admin will review it shortly.', 'success')
            return redirect(url_for('user_dashboard'))
        return render_template('user/apply.html', CATEGORIES=CATEGORIES)

    @app.route('/notifications')
    @login_required
    def notifications():
        db = load_db()
        uid = session['user_id']
        notifs = [n for n in db.get('notifications', []) if n['user_id'] == uid][::-1]
        return render_template('user/notifications.html', notifs=notifs)

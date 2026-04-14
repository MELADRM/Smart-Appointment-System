"""Business-owner routes."""

from datetime import datetime, timedelta
import os
from flask import flash, redirect, render_template, request, session, url_for
from db import load_db, save_db, new_id
from decorators import role_required
from helpers import (
    ALL_SLOTS,
    CATEGORIES,
    add_notification,
    clean_phone,
    enrich_appointments,
    get_biz_for_owner,
    is_valid_email,
    is_valid_hex_color,
    is_valid_url,
    safe_float,
    safe_int,
    slots_between,
)
from services import AnalyticsService, ReviewReplyService
from app_utils import save_logo, save_gallery_image

WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def register(app):
    @app.route('/business/dashboard')
    @role_required('business_owner')
    def biz_dashboard():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            flash('No approved business found for your account.', 'warning')
            return redirect(url_for('user_dashboard'))
        appts = [a for a in db['appointments'] if a['biz_id'] == biz['id']]
        enrich_appointments(appts, db)
        today_str = datetime.today().strftime('%Y-%m-%d')
        today_appts = sorted(
            [a for a in appts if a['date'] == today_str and a['status'] == 'booked'],
            key=lambda x: x['time'],
        )
        week_start = datetime.today().date() - timedelta(days=datetime.today().weekday())
        week_end = week_start + timedelta(days=6)
        week_appts = [
            a
            for a in appts
            if a['status'] == 'booked'
            and week_start <= datetime.strptime(a['date'], '%Y-%m-%d').date() <= week_end
        ]
        services = [s for s in db.get('services', []) if s['business_id'] == biz['id']]
        reviews = [r for r in db.get('reviews', []) if r['biz_id'] == biz['id']]
        avg_rating = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else None
        stats = {
            'total': len(appts),
            'booked': sum(1 for a in appts if a['status'] == 'booked'),
            'completed': sum(1 for a in appts if a['status'] == 'completed'),
            'cancelled': sum(1 for a in appts if a['status'] == 'cancelled'),
            'no_show': sum(1 for a in appts if a['status'] == 'no_show'),
            'reviews': len(reviews),
            'rating': avg_rating,
        }

        analytics = AnalyticsService(db, biz).build()
        notifs = [n for n in db.get('notifications', []) if n['user_id'] == session['user_id']][
            -5:
        ][::-1]
        for n in db.get('notifications', []):
            if n['user_id'] == session['user_id']:
                n['read'] = True
        save_db(db)
        return render_template(
            'business/dashboard.html',
            biz=biz,
            stats=stats,
            analytics=analytics,
            today_appts=today_appts,
            week_appts=week_appts,
            services=services,
            notifs=notifs,
            public_url=url_for('business_page', slug=biz['slug'], _external=True),
        )

    @app.route('/business/appointments')
    @role_required('business_owner')
    def biz_appointments():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        appts = sorted(
            [a for a in db['appointments'] if a['biz_id'] == biz['id']],
            key=lambda x: (x['date'], x['time']),
            reverse=True,
        )
        enrich_appointments(appts, db)
        status_f = request.args.get('status', '')
        if status_f:
            appts = [a for a in appts if a['status'] == status_f]
        return render_template(
            'business/appointments.html', biz=biz, appointments=appts, status_f=status_f
        )

    @app.route('/business/update-status/<appt_id>', methods=['POST'])
    @role_required('business_owner')
    def biz_update_status(appt_id):
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        new_st = request.form.get('status')
        appt = (
            next(
                (
                    a
                    for a in db['appointments']
                    if a['id'] == appt_id and a.get('biz_id') == biz['id']
                ),
                None,
            )
            if biz
            else None
        )
        if appt and new_st in ('booked', 'completed', 'cancelled', 'no_show'):
            old_st = appt['status']
            appt['status'] = new_st
            appt['updated_at'] = datetime.now().isoformat()

            if new_st == 'completed' and old_st != 'completed':
                add_notification(
                    db,
                    appt['user_id'],
                    f'Your appointment at {biz["name"]} on {appt["date"]} is marked completed. Leave a review!',
                    'success',
                )
            save_db(db)
            flash(f'Status updated to <strong>{new_st}</strong>.', 'success')
        return redirect(url_for('biz_appointments'))

    @app.route('/business/availability', methods=['GET', 'POST'])
    @role_required('business_owner')
    def biz_availability():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        if request.method == 'POST':
            date = request.form.get('date', '').strip()
            slots = request.form.getlist('slots')
            if date:
                rec = next(
                    (
                        av
                        for av in db['availability']
                        if av['biz_id'] == biz['id'] and av['date'] == date
                    ),
                    None,
                )
                if rec:
                    rec['slots'] = sorted(slots)
                    rec['updated_at'] = datetime.now().isoformat()
                else:
                    db['availability'].append(
                        {
                            'id': new_id('av'),
                            'biz_id': biz['id'],
                            'date': date,
                            'slots': sorted(slots),
                            'created_at': datetime.now().isoformat(),
                        }
                    )
                save_db(db)
                flash(f'Availability saved for {date}.', 'success')
            return redirect(url_for('biz_availability'))
        avail = sorted(
            [av for av in db['availability'] if av['biz_id'] == biz['id']], key=lambda x: x['date']
        )
        return render_template(
            'business/availability.html', biz=biz, availability=avail, all_slots=ALL_SLOTS
        )

    @app.route('/business/availability/delete/<av_id>', methods=['POST'])
    @role_required('business_owner')
    def biz_del_availability(av_id):
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if biz:
            db['availability'] = [
                av
                for av in db['availability']
                if not (av['id'] == av_id and av['biz_id'] == biz['id'])
            ]
            save_db(db)
            flash('Availability removed.', 'success')
        return redirect(url_for('biz_availability'))

    @app.route('/business/hours', methods=['GET', 'POST'])
    @role_required('business_owner')
    def biz_hours():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        hours_all = db.setdefault('business_hours', [])
        if request.method == 'POST':
            hours_all[:] = [h for h in hours_all if h['business_id'] != biz['id']]
            for wd in range(7):
                closed = request.form.get(f'closed_{wd}') == '1'
                open_t = request.form.get(f'open_{wd}', '').strip()
                close_t = request.form.get(f'close_{wd}', '').strip()
                if closed:
                    open_t, close_t = '', ''
                hours_all.append(
                    {
                        'id': new_id('bh'),
                        'business_id': biz['id'],
                        'weekday': wd,
                        'open_time': open_t,
                        'close_time': close_t,
                        'is_closed': closed,
                    }
                )
            save_db(db)
            flash('Weekly hours saved.', 'success')
            return redirect(url_for('biz_hours'))
        by_day = {wd: {'open_time': '', 'close_time': '', 'is_closed': False} for wd in range(7)}
        for h in hours_all:
            if h['business_id'] == biz['id']:
                by_day[int(h['weekday'])] = h
        return render_template(
            'business/hours.html',
            biz=biz,
            by_day=by_day,
            weekday_names=WEEKDAY_NAMES,
            all_slots=ALL_SLOTS,
        )

    @app.route('/business/hours/apply', methods=['POST'])
    @role_required('business_owner')
    def biz_hours_apply():
        # Apply the weekly template to the next N days (skips dates already customised).
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        try:
            days = int(request.form.get('days', 30) or 30)
        except ValueError:
            days = 30
        days = max(1, min(days, 180))
        by_day = {
            int(h['weekday']): h
            for h in db.get('business_hours', [])
            if h['business_id'] == biz['id']
        }
        if not by_day:
            flash('Set your weekly hours first, then apply them.', 'warning')
            return redirect(url_for('biz_hours'))
        existing_dates = {av['date'] for av in db['availability'] if av['biz_id'] == biz['id']}
        added = skipped = 0
        today = datetime.today().date()
        for offset in range(days):
            d = today + timedelta(days=offset)
            iso = d.isoformat()
            if iso in existing_dates:
                skipped += 1
                continue
            h = by_day.get(d.weekday())
            if not h or h.get('is_closed'):
                slots = []
            else:
                slots = slots_between(h.get('open_time'), h.get('close_time'))
            db['availability'].append(
                {
                    'id': new_id('av'),
                    'biz_id': biz['id'],
                    'date': iso,
                    'slots': slots,
                    'created_at': datetime.now().isoformat(),
                }
            )
            added += 1
        save_db(db)
        flash(
            f'Applied weekly template: {added} day(s) added, '
            f'{skipped} already customised (kept).',
            'success',
        )
        return redirect(url_for('biz_availability'))

    @app.route('/business/services', methods=['GET', 'POST'])
    @role_required('business_owner')
    def biz_services():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                svc_name = request.form.get('name', '').strip()[:120]
                if not svc_name:
                    flash('Service name is required.', 'danger')
                    return redirect(url_for('biz_services'))
                db['services'].append(
                    {
                        'id': new_id('svc'),
                        'business_id': biz['id'],
                        'name': svc_name,
                        'duration_min': safe_int(
                            request.form.get('duration'), default=30, lo=5, hi=480
                        ),
                        'price': safe_float(
                            request.form.get('price'), default=0.0, lo=0.0, hi=100000.0
                        ),
                        'description': request.form.get('description', '').strip()[:1000],
                    }
                )
                flash('Service added.', 'success')
            elif action == 'delete':
                sid = request.form.get('service_id')
                db['services'] = [
                    s
                    for s in db['services']
                    if not (s['id'] == sid and s['business_id'] == biz['id'])
                ]
                flash('Service removed.', 'success')
            save_db(db)
            return redirect(url_for('biz_services'))
        svcs = [s for s in db.get('services', []) if s['business_id'] == biz['id']]
        return render_template('business/services.html', biz=biz, services=svcs)

    @app.route('/business/profile', methods=['GET', 'POST'])
    @role_required('business_owner')
    def biz_profile():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        if request.method == 'POST':
            name = request.form.get('name', biz['name']).strip()[:150]
            desc = request.form.get('description', '').strip()[:2000]
            phone = request.form.get('phone', '').strip()
            addr = request.form.get('address', '').strip()[:255]
            bmail = request.form.get('email', '').strip().lower()[:190]
            web = request.form.get('website', '').strip()[:255]
            cat = request.form.get('category', biz.get('category', ''))
            col = request.form.get('logo_color', biz.get('logo_color', '#2563eb')).strip()
            bio = request.form.get('owner_bio', '').strip()[:2000]
            if len(name) < 2:
                flash('Business name is required.', 'danger')
                return redirect(url_for('biz_profile'))
            if cat and cat not in CATEGORIES:
                flash('Please pick a valid category.', 'danger')
                return redirect(url_for('biz_profile'))
            cleaned_phone = clean_phone(phone)
            if cleaned_phone is None:
                flash(
                    'Phone number looks invalid. Digits, spaces, and + - ( ) '
                    'only (7–25 characters).',
                    'danger',
                )
                return redirect(url_for('biz_profile'))
            if bmail and not is_valid_email(bmail):
                flash('Please enter a valid business email address.', 'danger')
                return redirect(url_for('biz_profile'))
            if web and not is_valid_url(web):
                flash('Website must start with http:// or https://', 'danger')
                return redirect(url_for('biz_profile'))
            if col and not is_valid_hex_color(col):
                col = biz.get('logo_color', '#2563eb')
            biz['name'] = name
            biz['description'] = desc
            biz['phone'] = cleaned_phone
            biz['address'] = addr
            biz['email'] = bmail
            biz['website'] = web
            biz['category'] = cat
            biz['logo_color'] = col
            biz['logo_initial'] = biz['name'][0].upper()
            biz['owner_bio'] = bio

            if request.form.get('remove_logo'):
                old = biz.get('logo_url')
                if old:
                    try:
                        os.remove(os.path.join(app.root_path, 'static', old))
                    except OSError:
                        pass
                biz['logo_url'] = ''
            else:
                new_path = save_logo(app, request.files.get('logo_file'), biz['id'])
                if new_path:
                    old = biz.get('logo_url')
                    if old:
                        try:
                            os.remove(os.path.join(app.root_path, 'static', old))
                        except OSError:
                            pass
                    biz['logo_url'] = new_path

            gallery_files = request.files.getlist('gallery_files')
            images = db.setdefault('business_images', [])
            next_sort = (
                max(
                    (i.get('sort_order', 0) for i in images if i['business_id'] == biz['id']),
                    default=0,
                )
                + 1
            )
            for f in gallery_files:
                path = save_gallery_image(app, f, biz['id'])
                if path:
                    images.append(
                        {
                            'id': new_id('img'),
                            'business_id': biz['id'],
                            'url': path,
                            'caption': '',
                            'sort_order': next_sort,
                            'created_at': datetime.now().isoformat(timespec='seconds'),
                        }
                    )
                    next_sort += 1
            save_db(db)
            flash('Business profile updated.', 'success')
            return redirect(url_for('biz_profile'))
        gallery = [i for i in db.get('business_images', []) if i['business_id'] == biz['id']]
        gallery.sort(key=lambda i: i.get('sort_order', 0))
        return render_template(
            'business/profile.html', biz=biz, gallery=gallery, CATEGORIES=CATEGORIES
        )

    @app.route('/business/gallery/<img_id>/delete', methods=['POST'])
    @role_required('business_owner')
    def biz_gallery_delete(img_id):
        # Remove one gallery image (file + DB row).
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        images = db.get('business_images', [])
        img = next((i for i in images if i['id'] == img_id and i['business_id'] == biz['id']), None)
        if img:
            try:
                os.remove(os.path.join(app.root_path, 'static', img['url']))
            except OSError:
                pass
            images.remove(img)
            save_db(db)
            flash('Gallery image removed.', 'success')
        return redirect(url_for('biz_profile'))

    @app.route('/business/reviews')
    @role_required('business_owner')
    def biz_reviews():
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        reviews = [r for r in db.get('reviews', []) if r['biz_id'] == biz['id']]
        reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        umap = {u['id']: u for u in db['users']}
        for r in reviews:
            r['reviewer_name'] = umap.get(r['user_id'], {}).get('name', 'Anonymous')
        avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else None
        return render_template('business/reviews.html', biz=biz, reviews=reviews, avg=avg)

    @app.route('/business/reviews/<rid>/reply', methods=['POST'])
    @role_required('business_owner')
    def biz_review_reply(rid):
        # Thin glue: ReviewReplyService does the real work.
        db = load_db()
        biz = get_biz_for_owner(session['user_id'], db)
        if not biz:
            return redirect(url_for('user_dashboard'))
        svc = ReviewReplyService(db)
        review = svc.find_for_business(rid, biz['id'])
        if not review:
            flash('Review not found.', 'danger')
            return redirect(url_for('biz_reviews'))
        outcome = svc.set_reply(
            review_row=review,
            business_name=biz['name'],
            customer_id=review['user_id'],
            text=request.form.get('reply', ''),
        )
        save_db(db)
        flash(
            {
                'posted': 'Reply posted.',
                'updated': 'Reply updated.',
                'removed': 'Reply removed.',
            }.get(outcome, 'Reply updated.'),
            'success' if outcome != 'removed' else 'info',
        )
        return redirect(url_for('biz_reviews'))

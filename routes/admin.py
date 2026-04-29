"""Admin-only routes."""

from datetime import datetime
import os
import random
from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash
from db import load_db, save_db, new_id, unique_slug
from decorators import role_required
from helpers import (
    add_notification,
    enrich_appointments,
    get_user,
    is_valid_email,
    log_admin_action,
)
from services import ReliabilityService
from app_utils import send_email

def register(app):
    @app.route('/admin')
    @role_required('admin')
    def admin_dashboard():
        db = load_db()
        users = db['users']
        appts = db['appointments']
        bizs = db['businesses']
        apps = db['business_applications']
        stats = {
            'users': len([u for u in users if u['role'] == 'user']),
            'owners': len([u for u in users if u['role'] == 'business_owner']),
            'businesses': len([b for b in bizs if b['status'] == 'approved']),
            'pending_apps': len([a for a in apps if a['status'] == 'pending']),
            'total_appts': len(appts),
            'booked': sum(1 for a in appts if a['status'] == 'booked'),
            'completed': sum(1 for a in appts if a['status'] == 'completed'),
            'revenue_est': sum(
                s.get('price', 0)
                for s in db.get('services', [])
                for a in appts
                if a.get('service_id') == s['id'] and a['status'] == 'completed'
            ),
        }
        recent_appts = sorted(appts, key=lambda x: x.get('created_at', ''), reverse=True)[:8]
        enrich_appointments(recent_appts, db)
        recent_apps = [a for a in apps if a['status'] == 'pending'][:5]
        return render_template(
            'admin/dashboard.html', stats=stats, recent_appts=recent_appts, recent_apps=recent_apps
        )

    @app.route('/admin/applications')
    @role_required('admin')
    def admin_applications():
        db = load_db()
        apps = sorted(
            db['business_applications'], key=lambda x: x.get('created_at', ''), reverse=True
        )
        status_f = request.args.get('status', '')
        if status_f:
            apps = [a for a in apps if a['status'] == status_f]
        return render_template('admin/applications.html', applications=apps, status_f=status_f)

    @app.route('/admin/applications/<app_id>/approve', methods=['POST'])
    @role_required('admin')
    def admin_approve_app(app_id):
        db = load_db()
        app_rec = next((a for a in db['business_applications'] if a['id'] == app_id), None)
        if not app_rec:
            flash('Application not found.', 'danger')
            return redirect(url_for('admin_applications'))
        existing_slugs = {b['slug'] for b in db['businesses']}
        slug = unique_slug(app_rec['name'], existing_slugs)
        colors = ['#2563eb', '#059669', '#dc2626', '#d97706', '#7c3aed', '#0891b2', '#be185d']
        color = random.choice(colors)
        biz_id = new_id('biz')
        db['businesses'].append(
            {
                'id': biz_id,
                'owner_id': app_rec['user_id'],
                'name': app_rec['name'],
                'slug': slug,
                'category': app_rec.get('category', ''),
                'description': app_rec.get('description', ''),
                'phone': app_rec.get('phone', ''),
                'email': app_rec.get('email', ''),
                'address': app_rec.get('address', ''),
                'website': '',
                'logo_initial': app_rec['name'][0].upper(),
                'logo_color': color,
                'status': 'approved',
                'featured': False,
                'created_at': datetime.now().isoformat(),
                'approved_at': datetime.now().isoformat(),
            }
        )

        user = get_user(app_rec['user_id'], db)
        if user:
            user['role'] = 'business_owner'
        app_rec['status'] = 'approved'
        app_rec['approved_at'] = datetime.now().isoformat()
        add_notification(
            db,
            app_rec['user_id'],
            f'🎉 Congratulations! Your business <strong>{app_rec["name"]}</strong> has been approved! '
            f'Your public page: /b/{slug}',
            'success',
        )
        log_admin_action(
            db,
            session['user_id'],
            session['user_name'],
            'approve_application',
            'business_application',
            app_id,
            f'Created business "{app_rec["name"]}" (slug: {slug})',
        )
        save_db(db)
        if user and user.get('email'):
            public_url = url_for('business_page', slug=slug, _external=True)
            send_email(
                user['email'],
                f'Your business "{app_rec["name"]}" is live 🎉',
                f'Hi {user["name"]},\n\n'
                f'Great news — your business "{app_rec["name"]}" has been approved '
                'on SmartBook Pro.\n\n'
                f'Public page: {public_url}\n\n'
                'You can now log in and set up services, availability, and your logo.\n\n'
                '— The SmartBook team',
            )
        flash(
            f'✅ Business <strong>{app_rec["name"]}</strong> approved! Slug: /b/{slug}', 'success'
        )
        return redirect(url_for('admin_applications'))

    @app.route('/admin/applications/<app_id>/reject', methods=['POST'])
    @role_required('admin')
    def admin_reject_app(app_id):
        db = load_db()
        reason = request.form.get('reason', '').strip()
        app_rec = next((a for a in db['business_applications'] if a['id'] == app_id), None)
        if app_rec:
            app_rec['status'] = 'rejected'
            app_rec['rejected_at'] = datetime.now().isoformat()
            app_rec['reject_reason'] = reason
            add_notification(
                db,
                app_rec['user_id'],
                f'Your business application for <strong>{app_rec["name"]}</strong> was not approved. '
                + (f'Reason: {reason}' if reason else 'Please contact support.'),
                'danger',
            )
            log_admin_action(
                db,
                session['user_id'],
                session['user_name'],
                'reject_application',
                'business_application',
                app_id,
                reason or '(no reason given)',
            )
            save_db(db)
            applicant = get_user(app_rec['user_id'], db)
            if applicant and applicant.get('email'):
                send_email(
                    applicant['email'],
                    f'Update on your "{app_rec["name"]}" application',
                    f'Hi {applicant["name"]},\n\n'
                    f'After review, we were unable to approve your business '
                    f'application for "{app_rec["name"]}" at this time.\n\n'
                    + (f'Reason: {reason}\n\n' if reason else '')
                    + 'If you believe this was in error, feel free to reach out.\n\n'
                    '— The SmartBook team',
                )
            flash('Application rejected.', 'success')
        return redirect(url_for('admin_applications'))

    @app.route('/admin/businesses')
    @role_required('admin')
    def admin_businesses():
        db = load_db()
        bizs = sorted(db['businesses'], key=lambda x: x.get('created_at', ''), reverse=True)
        umap = {u['id']: u for u in db['users']}
        for b in bizs:
            b['owner_name'] = umap.get(b['owner_id'], {}).get('name', '—')
            b['appt_count'] = sum(1 for a in db['appointments'] if a.get('biz_id') == b['id'])
        return render_template('admin/businesses.html', businesses=bizs)

    @app.route('/admin/businesses/<biz_id>/toggle-featured', methods=['POST'])
    @role_required('admin')
    def admin_toggle_featured(biz_id):
        db = load_db()
        biz = next((b for b in db['businesses'] if b['id'] == biz_id), None)
        if biz:
            biz['featured'] = not biz.get('featured', False)
            log_admin_action(
                db,
                session['user_id'],
                session['user_name'],
                'toggle_featured',
                'business',
                biz_id,
                f'featured={biz["featured"]}',
            )
            save_db(db)
            flash(f'{"Featured" if biz["featured"] else "Unfeatured"}: {biz["name"]}', 'success')
        return redirect(url_for('admin_businesses'))

    @app.route('/admin/businesses/<biz_id>/toggle-status', methods=['POST'])
    @role_required('admin')
    def admin_toggle_biz_status(biz_id):
        db = load_db()
        biz = next((b for b in db['businesses'] if b['id'] == biz_id), None)
        if biz:
            biz['status'] = 'suspended' if biz['status'] == 'approved' else 'approved'
            add_notification(
                db,
                biz['owner_id'],
                f'Your business has been {"suspended" if biz["status"] == "suspended" else "reinstated"}.',
                'warning' if biz['status'] == 'suspended' else 'success',
            )
            log_admin_action(
                db,
                session['user_id'],
                session['user_name'],
                'toggle_biz_status',
                'business',
                biz_id,
                f'status={biz["status"]}',
            )
            save_db(db)
            flash(f'Business {biz["status"]}: {biz["name"]}', 'success')
        return redirect(url_for('admin_businesses'))

    @app.route('/admin/businesses/<biz_id>/delete', methods=['POST'])
    @role_required('admin')
    def admin_delete_biz(biz_id):
        # Removes the business + every related row + the uploaded image files.
        db = load_db()
        biz = next((b for b in db['businesses'] if b['id'] == biz_id), None)
        biz_name = (biz or {}).get('name', '(unknown)')
        owner_id = (biz or {}).get('owner_id')

        orphan_paths = []
        if biz and biz.get('logo_url'):
            orphan_paths.append(biz['logo_url'])
        for img in db.get('business_images', []):
            if img.get('business_id') == biz_id and img.get('url'):
                orphan_paths.append(img['url'])

        db['businesses'] = [b for b in db['businesses'] if b['id'] != biz_id]
        db['appointments'] = [a for a in db['appointments'] if a.get('biz_id') != biz_id]
        db['availability'] = [av for av in db['availability'] if av.get('biz_id') != biz_id]
        db['services'] = [s for s in db.get('services', []) if s.get('business_id') != biz_id]
        db['reviews'] = [r for r in db.get('reviews', []) if r.get('biz_id') != biz_id]
        db['business_images'] = [
            i for i in db.get('business_images', []) if i.get('business_id') != biz_id
        ]
        db['business_hours'] = [
            h for h in db.get('business_hours', []) if h.get('business_id') != biz_id
        ]

        if owner_id:
            still_owns = any(
                b['owner_id'] == owner_id and b.get('status') == 'approved'
                for b in db['businesses']
            )
            if not still_owns:
                owner = next((u for u in db['users'] if u['id'] == owner_id), None)
                if owner and owner.get('role') == 'business_owner':
                    owner['role'] = 'user'
        log_admin_action(
            db,
            session['user_id'],
            session['user_name'],
            'delete_business',
            'business',
            biz_id,
            biz_name,
        )
        save_db(db)

        for rel in orphan_paths:
            try:
                os.remove(os.path.join(app.root_path, 'static', rel))
            except OSError:
                pass
        flash('Business and all related data deleted.', 'success')
        return redirect(url_for('admin_businesses'))

    @app.route('/admin/users')
    @role_required('admin')
    def admin_users():
        db = load_db()
        users = [u for u in db['users'] if u['id'] != session['user_id']]
        users = sorted(users, key=lambda x: x.get('created_at', ''), reverse=True)
        role_f = request.args.get('role', '')
        if role_f:
            users = [u for u in users if u['role'] == role_f]
        appt_map = {}
        for a in db['appointments']:
            appt_map[a['user_id']] = appt_map.get(a['user_id'], 0) + 1

        reliability = ReliabilityService(db)
        no_show_map = reliability.no_show_map()
        flag = request.args.get('flag', '')
        if flag == 'noshow':
            flagged = reliability.flagged_user_ids()
            users = [u for u in users if u['id'] in flagged]
        return render_template(
            'admin/users.html',
            users=users,
            appt_map=appt_map,
            no_show_map=no_show_map,
            role_f=role_f,
            flag=flag,
        )

    @app.route('/admin/users/<uid>/edit', methods=['GET', 'POST'])
    @role_required('admin')
    def admin_edit_user(uid):
        db = load_db()
        user = next((u for u in db['users'] if u['id'] == uid), None)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_users'))
        if request.method == 'POST':
            new_name = request.form.get('name', user['name']).strip()[:120]
            new_email = request.form.get('email', user['email']).strip().lower()[:190]
            if len(new_name) < 2:
                flash('Name must be at least 2 characters.', 'danger')
                return render_template('admin/edit_user.html', user=user)
            if not is_valid_email(new_email):
                flash('Please enter a valid email address.', 'danger')
                return render_template('admin/edit_user.html', user=user)
            if new_email != user['email'] and any(u['email'] == new_email for u in db['users']):
                flash('Another account already uses that email.', 'danger')
                return render_template('admin/edit_user.html', user=user)
            user['name'] = new_name
            user['email'] = new_email
            new_role = request.form.get('role', '')
            if new_role in ('user', 'business_owner', 'admin'):
                user['role'] = new_role
            user['is_active'] = request.form.get('is_active') == '1'
            pw = request.form.get('password', '').strip()
            if pw:
                if len(pw) < 6:
                    flash('Password min 6 chars.', 'danger')
                    return render_template('admin/edit_user.html', user=user)
                user['password'] = generate_password_hash(pw)
            save_db(db)
            flash('User updated.', 'success')
            return redirect(url_for('admin_users'))
        return render_template('admin/edit_user.html', user=user)

    @app.route('/admin/users/<uid>/delete', methods=['POST'])
    @role_required('admin')
    def admin_delete_user(uid):
        if uid == session['user_id']:
            flash('Cannot delete your own account.', 'danger')
            return redirect(url_for('admin_users'))
        db = load_db()
        u = next((x for x in db['users'] if x['id'] == uid), None)
        uname = (u or {}).get('name', '(unknown)')
        db['users'] = [u for u in db['users'] if u['id'] != uid]
        log_admin_action(
            db, session['user_id'], session['user_name'], 'delete_user', 'user', uid, uname
        )
        save_db(db)
        flash('User deleted.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<uid>/toggle-active', methods=['POST'])
    @role_required('admin')
    def admin_toggle_user(uid):
        db = load_db()
        user = next((u for u in db['users'] if u['id'] == uid), None)
        if user:
            user['is_active'] = not user.get('is_active', True)
            log_admin_action(
                db,
                session['user_id'],
                session['user_name'],
                'toggle_user',
                'user',
                uid,
                f'active={user["is_active"]}',
            )
            save_db(db)
            flash(f'User {"activated" if user["is_active"] else "suspended"}.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/appointments')
    @role_required('admin')
    def admin_appointments():
        db = load_db()
        appts = sorted(db['appointments'], key=lambda x: (x['date'], x['time']), reverse=True)
        enrich_appointments(appts, db)
        status_f = request.args.get('status', '')
        if status_f:
            appts = [a for a in appts if a['status'] == status_f]
        return render_template('admin/appointments.html', appointments=appts, status_f=status_f)

    @app.route('/admin/appointments/<appt_id>/override', methods=['POST'])
    @role_required('admin')
    def admin_override_appt(appt_id):
        db = load_db()
        new_status = request.form.get('status')
        appt = next((a for a in db['appointments'] if a['id'] == appt_id), None)
        if appt and new_status in ('booked', 'completed', 'cancelled', 'no_show'):
            appt['status'] = new_status
            appt['admin_override'] = True
            log_admin_action(
                db,
                session['user_id'],
                session['user_name'],
                'override_appointment',
                'appointment',
                appt_id,
                f'new_status={new_status}',
            )
            save_db(db)
            flash(f'Appointment status overridden to {new_status}.', 'success')
        return redirect(url_for('admin_appointments'))

    @app.route('/admin/reviews')
    @role_required('admin')
    def admin_reviews():
        db = load_db()
        reviews = sorted(db.get('reviews', []), key=lambda x: x.get('created_at', ''), reverse=True)
        bmap = {b['id']: b for b in db['businesses']}
        umap = {u['id']: u for u in db['users']}
        for r in reviews:
            r['biz_name'] = bmap.get(r['biz_id'], {}).get('name', '—')
            r['reviewer_name'] = umap.get(r['user_id'], {}).get('name', '—')
        return render_template('admin/reviews.html', reviews=reviews)

    @app.route('/admin/reviews/<rv_id>/delete', methods=['POST'])
    @role_required('admin')
    def admin_delete_review(rv_id):
        db = load_db()
        db['reviews'] = [r for r in db.get('reviews', []) if r['id'] != rv_id]
        log_admin_action(
            db, session['user_id'], session['user_name'], 'delete_review', 'review', rv_id, ''
        )
        save_db(db)
        flash('Review deleted.', 'success')
        return redirect(url_for('admin_reviews'))

    @app.route('/admin/audit')
    @role_required('admin')
    def admin_audit():
        db = load_db()
        log = sorted(
            db.get('admin_actions', []), key=lambda x: x.get('created_at', ''), reverse=True
        )
        return render_template('admin/audit.html', log=log)

    @app.route('/admin/settings', methods=['GET', 'POST'])
    @role_required('admin')
    def admin_settings():
        db = load_db()
        if request.method == 'POST':
            new_pw = request.form.get('new_password', '').strip()
            if new_pw and len(new_pw) >= 6:
                admin = next((u for u in db['users'] if u['id'] == session['user_id']), None)
                if admin:
                    admin['password'] = generate_password_hash(new_pw)
                    save_db(db)
                    flash('Password updated.', 'success')
            return redirect(url_for('admin_settings'))
        admin_user = next((u for u in db['users'] if u['id'] == session['user_id']), None)
        total_reviews = len(db.get('reviews', []))
        avg_rating = (
            round(sum(r['rating'] for r in db.get('reviews', [])) / total_reviews, 1)
            if total_reviews
            else None
        )
        return render_template(
            'admin/settings.html',
            admin_user=admin_user,
            db_stats={
                'reviews': total_reviews,
                'avg_rating': avg_rating,
                'services': len(db.get('services', [])),
                'availability': len(db.get('availability', [])),
            },
        )

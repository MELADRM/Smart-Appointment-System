"""
SmartBook Pro — automated tests.

Two suites in one file:
  - Fast suite:  layout / compile / import checks (no DB needed). Runs in CI.
  - Full suite:  end-to-end flow against the real MySQL DB.
                 Skipped unless RUN_DB_TESTS=1 so CI stays green without MySQL.

Run locally:
  py test.py                                  # fast suite only
  RUN_DB_TESTS=1 py test.py                   # both suites (Git Bash)
  set RUN_DB_TESTS=1 && py test.py            # both suites (cmd.exe)
  $env:RUN_DB_TESTS=1; py test.py             # both suites (PowerShell)
"""

import os
import sys
import time
import unittest
import compileall

ROOT = os.path.dirname(os.path.abspath(__file__))
RUN_DB_TESTS = os.environ.get('RUN_DB_TESTS') == '1'


# ============================================================
# Fast suite — no database, safe to run anywhere.
# ============================================================

class CompileTests(unittest.TestCase):
    def test_all_python_files_compile(self):
        ok = compileall.compile_dir(ROOT, quiet=1, force=True)
        self.assertTrue(ok, 'One or more .py files failed to compile.')


class ProjectLayoutTests(unittest.TestCase):
    def test_core_files_exist(self):
        for name in (
            'app.py', 'config.py', 'db.py', 'helpers.py',
            'seed.py', 'requirements.txt',
        ):
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT, name)),
                f'Missing file: {name}',
            )

    def test_core_folders_exist(self):
        for name in ('routes', 'templates', 'static', 'models', 'services'):
            self.assertTrue(
                os.path.isdir(os.path.join(ROOT, name)),
                f'Missing folder: {name}',
            )

    def test_key_templates_exist(self):
        for name in (
            'templates/public/home.html',
            'templates/public/explore.html',
            'templates/auth/login.html',
            'templates/auth/register.html',
        ):
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT, name)),
                f'Missing template: {name}',
            )


class RequirementsTests(unittest.TestCase):
    def test_requirements_lists_core_packages(self):
        with open(os.path.join(ROOT, 'requirements.txt'), encoding='utf-8') as f:
            text = f.read().lower()
        for pkg in ('flask', 'werkzeug', 'mysql-connector-python', 'pillow'):
            self.assertIn(pkg, text, f'requirements.txt is missing {pkg}')


class PureModuleImportTests(unittest.TestCase):
    def test_decorators_imports(self):
        sys.path.insert(0, ROOT)
        import decorators  # noqa: F401

    def test_app_utils_imports(self):
        sys.path.insert(0, ROOT)
        import app_utils  # noqa: F401


# ============================================================
# Full suite — exercises real routes against the live DB.
# Each test cleans up after itself in tearDownClass.
# ============================================================

@unittest.skipUnless(RUN_DB_TESTS, 'Set RUN_DB_TESTS=1 to run DB-backed tests.')
class FullFlowTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT)
        from app import app
        app.testing = True
        cls.client = app.test_client()

        from db import load_db
        from datetime import date, timedelta
        from helpers import slots_for_day

        db = load_db()
        approved = [b for b in db['businesses'] if b['status'] == 'approved']
        if not approved:
            raise AssertionError('No approved business — run seed_demo.py first.')
        cls.biz = approved[0]

        svcs = [s for s in db['services'] if s['business_id'] == cls.biz['id']]
        if not svcs:
            raise AssertionError('Target business has no services.')
        cls.svc = svcs[0]

        owner = next(u for u in db['users'] if u['id'] == cls.biz['owner_id'])
        cls.owner_email = owner['email']

        # Two distinct future slots so flow tests don't trip over each other.
        cls.slot_a = cls._find_free_slot(db, cls.biz['id'])
        cls.slot_b = cls._find_free_slot(db, cls.biz['id'], skip=cls.slot_a)

        cls._user_ids = []
        cls._appt_ids = []
        cls._review_ids = []

    @staticmethod
    def _find_free_slot(db, biz_id, skip=None):
        from datetime import date, timedelta
        from helpers import slots_for_day
        for i in range(1, 45):
            d = (date.today() + timedelta(days=i)).isoformat()
            day = slots_for_day(biz_id, d, db)
            free = [s['time'] for s in day if not s['taken']]
            for t in free:
                if skip and (d, t) == skip:
                    continue
                return (d, t)
        raise AssertionError('Could not find a free slot in the next 45 days.')

    def setUp(self):
        # Clear cookies between tests so each starts unauthenticated.
        self.client.get('/logout')

    @classmethod
    def tearDownClass(cls):
        from db import _conn
        cnx = _conn()
        try:
            cur = cnx.cursor()
            if cls._review_ids:
                ph = ','.join(['%s'] * len(cls._review_ids))
                cur.execute(f'DELETE FROM reviews WHERE id IN ({ph})', cls._review_ids)
            if cls._appt_ids:
                ph = ','.join(['%s'] * len(cls._appt_ids))
                cur.execute(f'DELETE FROM appointments WHERE id IN ({ph})', cls._appt_ids)
            if cls._user_ids:
                ph = ','.join(['%s'] * len(cls._user_ids))
                cur.execute(
                    f'DELETE FROM notifications WHERE user_id IN ({ph})',
                    cls._user_ids,
                )
                cur.execute(
                    f'DELETE FROM users WHERE id IN ({ph})',
                    cls._user_ids,
                )
            cnx.commit()
            cur.close()
        finally:
            cnx.close()

    # ---- helpers ----

    def _register(self, name, email, password='pass1234'):
        return self.client.post(
            '/register',
            data={'name': name, 'email': email, 'password': password, 'confirm': password},
            follow_redirects=False,
        )

    def _login(self, email, password):
        return self.client.post(
            '/login',
            data={'email': email, 'password': password},
            follow_redirects=False,
        )

    def _track_user(self, email):
        from db import load_db
        u = next((x for x in load_db()['users'] if x['email'] == email), None)
        if u:
            self._user_ids.append(u['id'])
        return u

    def _book(self, slug, date, time, service_id):
        return self.client.post(
            f'/b/{slug}/book',
            data={'date': date, 'time': time, 'service_id': service_id},
            follow_redirects=False,
        )

    # ---- tests (run in alphabetical order: 01, 02, 03, 04) ----

    def test_01_register_redirects_to_login(self):
        email = f'layla.yousef.{int(time.time())}@example.com'
        r = self._register('Layla Yousef', email)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r.headers['Location'])
        self.assertIsNotNone(self._track_user(email), 'User row should exist after register.')

    def test_02_login_lands_on_dashboard(self):
        email = f'daniel.roberts.{int(time.time())}@example.com'
        self._register('Daniel Roberts', email)
        self._track_user(email)
        r = self._login(email, 'pass1234')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/dashboard', r.headers['Location'])

    def test_03_book_complete_review_flow(self):
        # Customer signs up, books, owner completes, customer reviews.
        from db import load_db

        email = f'sara.malik.{int(time.time())}@example.com'
        self._register('Sara Malik', email)
        self._track_user(email)
        self._login(email, 'pass1234')

        d, t = self.slot_a
        r = self._book(self.biz['slug'], d, t, self.svc['id'])
        self.assertEqual(r.status_code, 302, f'Booking failed: {r.data[:200]}')

        u = next(x for x in load_db()['users'] if x['email'] == email)
        appt = next(
            a for a in load_db()['appointments']
            if a['user_id'] == u['id'] and a['date'] == d
        )
        self._appt_ids.append(appt['id'])

        # Owner marks the appointment completed.
        self.client.get('/logout')
        self._login(self.owner_email, 'staff123')
        r = self.client.post(
            f'/business/update-status/{appt["id"]}',
            data={'status': 'completed'},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)

        # Customer leaves a 5-star review.
        self.client.get('/logout')
        self._login(email, 'pass1234')
        r = self.client.post(
            f'/user/review/{appt["id"]}',
            data={'rating': '5', 'comment': 'Excellent — would book again.'},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)

        rv = next(
            (x for x in load_db()['reviews'] if x['appt_id'] == appt['id']),
            None,
        )
        self.assertIsNotNone(rv, 'Review row should be in DB.')
        self.assertEqual(rv['rating'], 5)
        self._review_ids.append(rv['id'])

    def test_04_double_booking_is_rejected(self):
        from db import load_db

        d, t = self.slot_b

        # First customer takes the slot.
        email_a = f'omar.nazir.{int(time.time())}@example.com'
        self._register('Omar Nazir', email_a)
        self._track_user(email_a)
        self._login(email_a, 'pass1234')
        r = self._book(self.biz['slug'], d, t, self.svc['id'])
        self.assertEqual(r.status_code, 302)

        u_a = next(x for x in load_db()['users'] if x['email'] == email_a)
        appt_a = next(
            a for a in load_db()['appointments']
            if a['user_id'] == u_a['id'] and a['date'] == d
        )
        self._appt_ids.append(appt_a['id'])
        self.client.get('/logout')

        # Second customer tries the same slot — should NOT create an appointment.
        email_b = f'maya.tawil.{int(time.time())}@example.com'
        self._register('Maya Tawil', email_b)
        self._track_user(email_b)
        self._login(email_b, 'pass1234')
        self._book(self.biz['slug'], d, t, self.svc['id'])

        u_b = next(x for x in load_db()['users'] if x['email'] == email_b)
        clash = next(
            (a for a in load_db()['appointments']
             if a['user_id'] == u_b['id'] and a['date'] == d and a['time'] == t),
            None,
        )
        self.assertIsNone(clash, 'Double booking should be rejected.')


if __name__ == '__main__':
    unittest.main(verbosity=2)

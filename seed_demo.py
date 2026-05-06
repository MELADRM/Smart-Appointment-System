"""Populate the DB with showcase data."""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from db import load_db, save_db, new_id, slugify

db = load_db()
for u in db['users']:
    if u['email'] in ('sarah@smartbook.com', 'james@smartbook.com'):
        u['role'] = 'business_owner'
if not any(u['email'] == 'maya@smartbook.com' for u in db['users']):
    db['users'].append(
        {
            'id': 'u-maya-001',
            'name': 'Maya Chen',
            'email': 'maya@smartbook.com',
            'password': generate_password_hash('maya123'),
            'role': 'user',
            'is_active': True,
            'created_at': datetime.now().isoformat(),
        }
    )
if not any(u['email'] == 'omar@smartbook.com' for u in db['users']):
    db['users'].append(
        {
            'id': 'u-omar-001',
            'name': 'Omar Haddad',
            'email': 'omar@smartbook.com',
            'password': generate_password_hash('omar123'),
            'role': 'user',
            'is_active': True,
            'created_at': datetime.now().isoformat(),
        }
    )
db['businesses'] = []
db['services'] = []
db['reviews'] = []
db['appointments'] = []
db['business_hours'] = []
NOW = datetime.now().isoformat()
BUSINESSES = [
    {
        'id': 'biz-sarah-clinic',
        'owner_id': 'u-staff-001',
        'name': 'Aurora Dental Clinic',
        'category': 'Dentistry',
        'description': 'Modern dental care for the whole family. Cleanings, whitening, '
        'orthodontics and cosmetic dentistry in a calm, friendly setting.',
        'phone': '+1 555-120-4567',
        'email': 'hello@auroradental.com',
        'address': '221 Main Street, Boston, MA',
        'website': 'https://auroradental.example.com',
        'logo_initial': 'A',
        'logo_color': '#2E74B6',
        'owner_bio': 'Dr. Sarah Ahmed · DDS, board-certified, 12 years of experience.',
    },
    {
        'id': 'biz-james-fitness',
        'owner_id': 'u-staff-002',
        'name': 'Peak Performance Gym',
        'category': 'Fitness',
        'description': 'Personal training, group HIIT classes, yoga and recovery sessions. '
        'Certified trainers, flexible scheduling.',
        'phone': '+1 555-220-9900',
        'email': 'train@peakperformance.com',
        'address': '58 Harbor Avenue, Boston, MA',
        'website': 'https://peakperformance.example.com',
        'logo_initial': 'P',
        'logo_color': '#DB7A1F',
        'owner_bio': 'Coach James Park · NASM-CPT, 10 years coaching athletes.',
    },
    {
        'id': 'biz-sarah-derm',
        'owner_id': 'u-staff-001',
        'name': 'Glow Dermatology Studio',
        'category': 'Dermatology',
        'description': 'Medical and aesthetic dermatology. Acne, pigmentation, laser '
        'treatments, and advanced skincare consultations.',
        'phone': '+1 555-330-2211',
        'email': 'care@glowderm.com',
        'address': '12 Beacon Hill, Boston, MA',
        'website': '',
        'logo_initial': 'G',
        'logo_color': '#C04A7C',
        'owner_bio': 'Medical aesthetics team led by Dr. Sarah Ahmed.',
    },
    {
        'id': 'biz-james-legal',
        'owner_id': 'u-staff-002',
        'name': 'Park & Associates Legal',
        'category': 'Legal',
        'description': 'Family, contract, and small-business law. Free 15-minute '
        'consultation for new clients.',
        'phone': '+1 555-408-7777',
        'email': 'contact@parklegal.com',
        'address': '401 Commerce Street, Boston, MA',
        'website': 'https://parklegal.example.com',
        'logo_initial': 'P',
        'logo_color': '#1F3A5F',
        'owner_bio': 'James Park, Esq. · Massachusetts Bar, 8 years practice.',
    },
    {
        'id': 'biz-sarah-bayside',
        'owner_id': 'u-staff-001',
        'name': 'Bayside Family Dentistry',
        'category': 'Dentistry',
        'description': 'Family-friendly dental practice with sedation options for nervous '
        'patients. Cleanings, fillings, and emergency visits welcome.',
        'phone': '+1 555-105-2233',
        'email': 'hello@baysidedental.com',
        'address': '76 Harborfront Road, Boston, MA',
        'website': '',
        'logo_initial': 'B',
        'logo_color': '#0E7C7B',
        'owner_bio': 'A second clinic in the Aurora Dental network.',
    },
    {
        'id': 'biz-james-ironforge',
        'owner_id': 'u-staff-002',
        'name': 'Iron Forge Strength Studio',
        'category': 'Fitness',
        'description': 'Powerlifting and strength conditioning in a small-group setting. '
        'Coached squat, bench, and deadlift programs for all levels.',
        'phone': '+1 555-244-1188',
        'email': 'lift@ironforge.com',
        'address': '14 Industrial Lane, Boston, MA',
        'website': '',
        'logo_initial': 'I',
        'logo_color': '#3E2C2A',
        'owner_bio': 'Sister gym to Peak Performance — strength-focused programming.',
    },
    {
        'id': 'biz-sarah-renew',
        'owner_id': 'u-staff-001',
        'name': 'Renew Skin & Aesthetics',
        'category': 'Dermatology',
        'description': 'Modern aesthetic dermatology — chemical peels, microneedling, '
        'and personalised skincare regimens.',
        'phone': '+1 555-330-7788',
        'email': 'care@renewskin.com',
        'address': '203 Newbury Street, Boston, MA',
        'website': '',
        'logo_initial': 'R',
        'logo_color': '#9B5DE5',
        'owner_bio': 'Aesthetics-focused branch led by Dr. Sarah Ahmed.',
    },
    {
        'id': 'biz-james-trustlaw',
        'owner_id': 'u-staff-002',
        'name': 'Trust & Estate Law Office',
        'category': 'Legal',
        'description': 'Wills, trusts, and probate. Help families plan ahead and avoid '
        'court complications when it matters most.',
        'phone': '+1 555-411-9090',
        'email': 'plan@trustlaw.com',
        'address': '550 State Avenue, Boston, MA',
        'website': '',
        'logo_initial': 'T',
        'logo_color': '#264653',
        'owner_bio': 'Estate planning practice partnered with Park & Associates.',
    },
]
existing_slugs = set()
for b in BUSINESSES:
    slug = slugify(b['name'])
    b['slug'] = slug
    existing_slugs.add(slug)
    db['businesses'].append(
        {
            'id': b['id'],
            'owner_id': b['owner_id'],
            'name': b['name'],
            'slug': b['slug'],
            'category': b['category'],
            'description': b['description'],
            'phone': b['phone'],
            'email': b['email'],
            'address': b['address'],
            'website': b['website'],
            'logo_initial': b['logo_initial'],
            'logo_color': b['logo_color'],
            'logo_url': '',
            'owner_bio': b['owner_bio'],
            'status': 'approved',
            'featured': b['id'] in ('biz-sarah-clinic', 'biz-james-fitness'),
            'created_at': NOW,
            'approved_at': NOW,
        }
    )
SERVICES = {
    'biz-sarah-clinic': [
        ('Dental Cleaning', 30, 80, 'Professional scaling and polish.'),
        ('Teeth Whitening', 60, 150, 'In-office whitening session.'),
        ('Cavity Filling', 45, 120, 'Composite filling with local anesthesia.'),
        ('Orthodontic Consult', 30, 50, 'Braces / aligners evaluation.'),
    ],
    'biz-james-fitness': [
        ('Personal Training', 60, 70, '1-on-1 session tailored to your goals.'),
        ('HIIT Group Class', 45, 25, 'High-intensity group workout.'),
        ('Yoga Session', 60, 35, 'Flow, hatha, or restorative.'),
        ('Recovery Massage', 60, 85, 'Sports massage with certified therapist.'),
    ],
    'biz-sarah-derm': [
        ('Skin Consultation', 30, 90, 'Diagnosis and personalized skincare plan.'),
        ('Acne Treatment', 45, 130, 'Deep cleanse + extraction + mask.'),
        ('Laser Pigmentation', 60, 220, 'Laser therapy for sun spots / melasma.'),
    ],
    'biz-james-legal': [
        ('Free Consultation', 15, 0, '15-minute intake call.'),
        ('Contract Review', 60, 200, 'Review and annotate one contract.'),
        ('Family Law Session', 90, 300, 'Divorce, custody, pre-nup consultation.'),
    ],
    'biz-sarah-bayside': [
        ('Routine Cleaning', 30, 70, 'Standard 6-month dental cleaning.'),
        ('Emergency Visit', 30, 95, 'Same-day urgent care for tooth pain.'),
        ('Sedation Consult', 30, 60, 'Pre-procedure consultation for anxious patients.'),
    ],
    'biz-james-ironforge': [
        ('Strength Assessment', 45, 50, 'Form review on the big three lifts.'),
        ('Coached Lifting Session', 60, 65, 'Programmed strength session with a coach.'),
        ('Powerlifting Program Review', 30, 40, 'Custom 8-week program walkthrough.'),
    ],
    'biz-sarah-renew': [
        ('Chemical Peel', 45, 140, 'Light or medium-depth peel with aftercare advice.'),
        ('Microneedling', 60, 200, 'Collagen-induction treatment.'),
        ('Skincare Consultation', 30, 75, 'Personalised regimen and product plan.'),
    ],
    'biz-james-trustlaw': [
        ('Will Drafting', 60, 250, 'Draft and finalise a simple will.'),
        ('Trust Setup', 90, 450, 'Revocable living trust creation.'),
        ('Probate Consultation', 45, 150, 'Guidance for executors and beneficiaries.'),
    ],
}
for biz_id, services in SERVICES.items():
    for name, duration, price, desc in services:
        db['services'].append(
            {
                'id': new_id('sv'),
                'business_id': biz_id,
                'name': name,
                'duration_min': duration,
                'price': price,
                'description': desc,
            }
        )
for biz in db['businesses']:
    for wd in range(7):
        closed = wd >= 5
        db['business_hours'].append(
            {
                'id': new_id('bh'),
                'business_id': biz['id'],
                'weekday': wd,
                'open_time': '' if closed else '09:00',
                'close_time': '' if closed else '17:30',
                'is_closed': closed,
            }
        )
CUSTOMERS = [('u-maya-001', 'Maya Chen'), ('u-omar-001', 'Omar Haddad')]
past = (datetime.now() - timedelta(days=7)).date().isoformat()
past2 = (datetime.now() - timedelta(days=14)).date().isoformat()
svc_lookup = {s['id']: s for s in db['services']}
svc_by_biz = {}
for s in db['services']:
    svc_by_biz.setdefault(s['business_id'], []).append(s)
review_texts = [
    (5, 'Absolutely excellent. Staff were friendly and the service was fast.'),
    (5, 'Best experience I\'ve had in years. Already booked my next session.'),
    (4, 'Great value for the price. Would recommend to friends.'),
    (5, 'Professional, clean, and on time. Exactly what I was looking for.'),
]
rt_idx = 0
# Only seed bookings at the four original demo businesses so the recommender
# has fresh businesses to suggest.
ORIGINAL_BIZ_IDS = {
    'biz-sarah-clinic', 'biz-james-fitness',
    'biz-sarah-derm',   'biz-james-legal',
}
for biz in db['businesses']:
    if biz['id'] not in ORIGINAL_BIZ_IDS:
        continue
    svcs = svc_by_biz.get(biz['id'], [])
    if not svcs:
        continue
    for i, (uid, uname) in enumerate(CUSTOMERS):
        svc = svcs[i % len(svcs)]
        ap_id = new_id('ap')
        ap_date = past if i == 0 else past2
        ap = {
            'id': ap_id,
            'user_id': uid,
            'biz_id': biz['id'],
            'service_id': svc['id'],
            'date': ap_date,
            'time': '10:00' if i == 0 else '14:00',
            'duration_min': svc['duration_min'],
            'notes': '',
            'reason': svc['name'],
            'status': 'completed',
            'created_at': NOW,
        }
        db['appointments'].append(ap)
        rating, comment = review_texts[rt_idx % len(review_texts)]
        rt_idx += 1
        db['reviews'].append(
            {
                'id': new_id('r'),
                'appt_id': ap_id,
                'biz_id': biz['id'],
                'user_id': uid,
                'rating': rating,
                'comment': comment,
                'owner_reply': '',
                'owner_reply_at': None,
                'created_at': NOW,
            }
        )
tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
upcoming_svc = svc_by_biz['biz-sarah-clinic'][0]
db['appointments'].append(
    {
        'id': new_id('ap'),
        'user_id': 'u-maya-001',
        'biz_id': 'biz-sarah-clinic',
        'service_id': upcoming_svc['id'],
        'date': tomorrow,
        'time': '11:00',
        'duration_min': upcoming_svc['duration_min'],
        'notes': '',
        'reason': upcoming_svc['name'],
        'status': 'booked',
        'created_at': NOW,
    }
)
db.setdefault('business_applications', [])
db['business_applications'] = [
    a for a in db['business_applications'] if a.get('id') != 'app-demo-001'
]
db['business_applications'].append(
    {
        'id': 'app-demo-001',
        'user_id': 'u-maya-001',
        'user_name': 'Maya Chen',
        'name': 'Serenity Yoga & Wellness',
        'category': 'Fitness',
        'description': 'Boutique yoga studio offering Vinyasa, Hatha and meditation classes.',
        'phone': '+1 555-600-3030',
        'email': 'hello@serenityyoga.com',
        'address': '88 Park Avenue, Boston, MA',
        'status': 'pending',
        'reject_reason': '',
        'created_at': NOW,
        'approved_at': None,
        'rejected_at': None,
    }
)
save_db(db)
print(
    f'Seeded: {len(db["businesses"])} businesses, '
    f'{len(db["services"])} services, '
    f'{len(db["appointments"])} appointments, '
    f'{len(db["reviews"])} reviews, '
    f'{len(db["business_applications"])} pending apps'
)

"""MySQL-backed persistence layer."""

import re
import uuid
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
    # Append -2 if the slug is already taken.
    slug = slugify(base)
    if slug not in existing_slugs:
        return slug
    return f"{slug}-2"

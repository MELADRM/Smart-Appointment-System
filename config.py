"""MySQL connection settings."""

import os
from urllib.parse import urlparse


def _from_url(url):
    parsed = urlparse(url)
    return {
        'host':     parsed.hostname,
        'port':     parsed.port or 3306,
        'user':     parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/') or 'railway',
    }


_url = os.environ.get('MYSQL_URL') or os.environ.get('DATABASE_URL')

if _url:
    _base = _from_url(_url)
else:
    _base = {
        'host':     os.environ.get('MYSQLHOST') or os.environ.get('SB_DB_HOST', 'localhost'),
        'port':     int(os.environ.get('MYSQLPORT') or os.environ.get('SB_DB_PORT', 3306)),
        'user':     os.environ.get('MYSQLUSER') or os.environ.get('SB_DB_USER', 'root'),
        'password': os.environ.get('MYSQLPASSWORD') or os.environ.get('SB_DB_PASSWORD', '333666'),
        'database': os.environ.get('MYSQLDATABASE') or os.environ.get('SB_DB_NAME', 'smartbook'),
    }

DB_CONFIG = {
    **_base,
    'charset': 'utf8mb4',
    'use_unicode': True,
    'autocommit': False,
}

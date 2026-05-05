# Smart Appointment System

A multi-category appointment booking platform built with Flask, MySQL and
Bootstrap. Customers browse businesses, pick a time, and book online;
business owners manage their schedule from a dashboard; admins oversee the
whole platform.

## Setup

1. Install Python 3.11
2. Install MySQL 8 and create a database called `smartbook`
3. Run `pip install -r requirements.txt`
4. Set MySQL credentials in environment variables
   (`SB_DB_USER`, `SB_DB_PASSWORD`, `SB_DB_NAME`)
5. Run `python app.py`

## Team

- **Melad Mustafabadran** — Team Leader, Frontend
- **Beste Ozkan** — Designer, Frontend
- **Ahed Akrout** — Backend
- **Osamah Naji** — Tester

## Tech Stack

- Flask 3.x and Werkzeug
- MySQL 8 with mysql-connector-python
- Bootstrap 5
- Python 3.11

## Tests

Run `python test.py` for the fast suite (used by CI).
Run with `RUN_DB_TESTS=1` for the full functional suite (needs a local DB).

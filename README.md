# Secure Question Paper Management System

College microproject built with Flask, Supabase PostgreSQL, Supabase Auth/Storage,
Python cryptography, SHA-256 hashing, and role-based access control.

## Current stage

- Flask project structure
- Supabase connectivity test
- profiles table preparation
- Basic frontend placeholder

## Run

1. Create and activate the virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Copy `.env.example` to `.env`.
4. Add your Supabase URL, key, and Flask secret key.
5. Run:
   python app.py
6. Open:
   http://127.0.0.1:5000/
7. Test Supabase:
   http://127.0.0.1:5000/test-supabase

Do not put real `.env` credentials into source control.

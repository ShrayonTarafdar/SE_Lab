"""
utils.py — Utility helpers for CampusKart

Contains:
- Database initialization (tables creation)
- OTP and Order ID generation utilities
- login_required decorator for Flask routes
"""

import sqlite3
import os
import random
import string
import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash

# --------------------------------------------
# LOGIN GUARD DECORATOR
# --------------------------------------------
def login_required(f):
    """
    Decorator that redirects to /login if user not in session.
    Use above any route that requires login.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# --------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------
def init_db():
    """
    Creates the SQLite database and all required tables
    if they do not already exist.
    Includes users, items, and orders.
    """
    print("Initializing CampusKart database...")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        profile_img TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ITEMS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT,
        image_url TEXT,
        status TEXT DEFAULT 'available',
        quantity INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES users (user_id)
    );
    """)

    # ORDERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE,
        buyer_id INTEGER,
        item_name TEXT,
        price REAL,
        seller_name TEXT,
        seller_email TEXT,
        status TEXT DEFAULT 'pending',
        hashed_otp TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users (user_id)
    );
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

    # Add quantity column if missing (backward compatibility)
    ensure_quantity_column()


def ensure_quantity_column():
    """
    Ensures that the 'quantity' column exists in the items table.
    Useful for upgrading older databases.
    """
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantity FROM items LIMIT 1;")
    except sqlite3.OperationalError:
        print("Adding missing 'quantity' column to items table...")
        cursor.execute("ALTER TABLE items ADD COLUMN quantity INTEGER DEFAULT 1;")
        conn.commit()
    conn.close()


# --------------------------------------------
# OTP GENERATION
# --------------------------------------------
def generate_hashed_otp():
    """
    Generates a random 4-digit OTP and its SHA256 hash (shortened).
    Returns (otp, hashed_otp)
    """
    otp = random.randint(1000, 9999)
    hashed = hashlib.sha256(str(otp).encode()).hexdigest()[:8]
    return otp, hashed


# --------------------------------------------
# ORDER ID GENERATION
# --------------------------------------------
def generate_order_id():
    """
    Generates a unique 8-character order ID like 'ORD12345'.
    """
    return "ORD" + "".join(random.choices(string.digits, k=5))

"""
utils.py — Utility helpers for CampusKart

Contains:
- Database initialization (tables creation)
- OTP and Order ID generation utilities
- login_required decorator for Flask routes
"""

import sqlite3
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
    """
    print("Initializing CampusKart database...")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Enable foreign key support which is off by default in SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

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
        FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)

    # ORDERS TABLE (Corrected Schema)
    # Stores item_id and seller_id for proper relational integrity
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        buyer_id INTEGER,
        seller_id INTEGER,
        item_id INTEGER,
        price REAL, /* Price at the time of sale */
        quantity_ordered INTEGER DEFAULT 1,
        payment_mode TEXT,
        payment_status TEXT DEFAULT 'pending',
        order_status TEXT DEFAULT 'pending', /* e.g., pending, in_transit, completed */
        hashed_otp TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (item_id) REFERENCES items (item_id) ON DELETE SET NULL
    );
    """)

    # ---> DATABASE TRIGGER for Automatic Stock Management <---
    # This trigger automatically updates the item's stock after an order is placed.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS after_order_insert_update_item_stock
    AFTER INSERT ON orders
    FOR EACH ROW
    BEGIN
        -- Decrement the quantity of the item that was just ordered
        UPDATE items
        SET quantity = quantity - NEW.quantity_ordered
        WHERE item_id = NEW.item_id;

        -- If the quantity is now 0 or less, mark the item as 'sold'
        UPDATE items
        SET status = 'sold'
        WHERE item_id = NEW.item_id AND quantity <= 0;
    END;
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully with new schema and triggers.")

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
    Generates a unique 8-character order ID like 'ORD-ABC123'.
    """
    return "ORD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
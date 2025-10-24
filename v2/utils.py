"""
utils.py — Utility helpers for CampusKart

Contains:
- Database initialization (tables creation with triggers)
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
    print("Initializing CampusKart database...")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- TABLES ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, profile_img TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER, name TEXT NOT NULL, description TEXT,
        price REAL NOT NULL, category TEXT, image_url TEXT, status TEXT DEFAULT 'available',
        quantity INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY, buyer_id INTEGER, seller_id INTEGER, item_id INTEGER, price REAL,
        quantity_ordered INTEGER DEFAULT 1, payment_mode TEXT, payment_status TEXT DEFAULT 'pending',
        order_status TEXT DEFAULT 'pending', hashed_otp TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (item_id) REFERENCES items (item_id) ON DELETE SET NULL
    );
    """)

    # ---> DATABASE TRIGGERS <---

    # --- AUTOMATION TRIGGERS ---

    # 1. Update stock AFTER a new order is successfully inserted.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS after_order_insert_update_item_stock
    AFTER INSERT ON orders
    FOR EACH ROW
    BEGIN
        UPDATE items SET quantity = quantity - NEW.quantity_ordered WHERE item_id = NEW.item_id;
        UPDATE items SET status = 'sold' WHERE item_id = NEW.item_id AND quantity <= 0;
    END;
    """)

    # 2. Restock item AFTER an order record is DELETED (for admin/cleanup purposes).
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS after_order_delete_restock_item
    AFTER DELETE ON orders
    FOR EACH ROW
    WHEN OLD.order_status != 'cancelled'
    BEGIN
        UPDATE items SET quantity = quantity + OLD.quantity_ordered, status = 'available' WHERE item_id = OLD.item_id;
    END;
    """)

    # --- VALIDATION & INTEGRITY TRIGGERS ---

    # 3. Prevent a user from buying their own item BEFORE an order is inserted.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_self_purchase
    BEFORE INSERT ON orders
    FOR EACH ROW
    WHEN NEW.buyer_id = NEW.seller_id
    BEGIN
        SELECT RAISE(ABORT, 'A user cannot purchase their own item.');
    END;
    """)

    # 4. Double-check stock BEFORE an order is inserted as a final safeguard.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS check_stock_before_order
    BEFORE INSERT ON orders
    FOR EACH ROW
    BEGIN
        SELECT
            CASE
                WHEN (SELECT quantity FROM items WHERE item_id = NEW.item_id) < NEW.quantity_ordered
                THEN RAISE(ABORT, 'Insufficient stock to place this order.')
            END;
    END;
    """)

    # 5. Prevent an item from being deleted IF it has non-cancelled orders associated with it.
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_item_delete_if_ordered
    BEFORE DELETE ON items
    FOR EACH ROW
    BEGIN
        SELECT RAISE(ABORT, 'Cannot delete an item that has existing, non-cancelled orders.')
        WHERE EXISTS (
            SELECT 1 FROM orders WHERE item_id = OLD.item_id AND order_status != 'cancelled'
        );
    END;
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully with all triggers.")

# --------------------------------------------
# OTP GENERATION
# --------------------------------------------
def generate_hashed_otp():
    otp = random.randint(1000, 9999)
    hashed = hashlib.sha256(str(otp).encode()).hexdigest()[:8]
    return otp, hashed

# --------------------------------------------
# ORDER ID GENERATION
# --------------------------------------------
def generate_order_id():
    return "ORD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
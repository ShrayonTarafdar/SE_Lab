"""
utils.py — Utility and Database Initialization for CampusKart

This file contains all the core helper functions, decorators, and database
initialization logic required for the CampusKart application.
"""

import sqlite3
import random
import string
import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash

# ======================================================================
# DECORATORS (For Protecting Web Routes)
# ======================================================================

def login_required(f):
    """
    Decorator to protect routes that require user authentication.
    If a user is not logged in (no user_id in session), they are redirected
    to the login page with a warning flash message.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ======================================================================
# DATABASE INITIALIZATION
# ======================================================================

def init_db():
    """
    Initialize the CampusKart SQLite database with all tables and triggers.
    Includes:
        - users table
        - items table
        - orders table (with OTP support)
        - Triggers to maintain stock, prevent invalid actions, and enforce rules
    """
    print("Initializing CampusKart database...")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints

    # -----------------------------
    # CREATE TABLES
    # -----------------------------

    # Users table: stores registered users
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

    # Items table: stores products for sale
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,           -- Foreign key to users table
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT,
        image_url TEXT,
        status TEXT DEFAULT 'available',      -- Tracks availability: available/sold
        quantity INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)

    # Orders table: stores all purchase orders
    # Includes OTPs for delivery verification
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,            -- Unique order identifier
        buyer_id INTEGER NOT NULL,            -- Foreign key to users
        seller_id INTEGER NOT NULL,           -- Foreign key to users
        item_id INTEGER NOT NULL,             -- Foreign key to items
        price REAL NOT NULL,
        quantity_ordered INTEGER DEFAULT 1,
        payment_mode TEXT,
        payment_status TEXT DEFAULT 'pending',
        order_status TEXT DEFAULT 'pending',  -- pending, in_transit, completed, cancelled
        otp TEXT,                             -- Plaintext OTP for buyer
        hashed_otp TEXT,                      -- Hashed OTP for admin verification
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (seller_id) REFERENCES users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (item_id) REFERENCES items (item_id) ON DELETE SET NULL
    );
    """)

    # -----------------------------
    # DATABASE TRIGGERS
    # -----------------------------

    # Trigger: After inserting an order, reduce item quantity and update status
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS after_order_insert_update_item_stock
    AFTER INSERT ON orders
    FOR EACH ROW
    BEGIN
        UPDATE items
        SET quantity = quantity - NEW.quantity_ordered
        WHERE item_id = NEW.item_id;

        UPDATE items
        SET status = 'sold'
        WHERE item_id = NEW.item_id AND quantity <= 0;
    END;
    """)

    # Trigger: After deleting an order (not cancelled), restock item
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS after_order_delete_restock_item
    AFTER DELETE ON orders
    FOR EACH ROW
    WHEN OLD.order_status != 'cancelled'
    BEGIN
        UPDATE items
        SET quantity = quantity + OLD.quantity_ordered,
            status = 'available'
        WHERE item_id = OLD.item_id;
    END;
    """)

    # Trigger: Prevent users from purchasing their own items
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_self_purchase
    BEFORE INSERT ON orders
    FOR EACH ROW
    WHEN NEW.buyer_id = NEW.seller_id
    BEGIN
        SELECT RAISE(ABORT, 'A user cannot purchase their own item.');
    END;
    """)

    # Trigger: Prevent orders if requested quantity exceeds stock
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS check_stock_before_order
    BEFORE INSERT ON orders
    FOR EACH ROW
    BEGIN
        SELECT CASE
            WHEN (SELECT quantity FROM items WHERE item_id = NEW.item_id) < NEW.quantity_ordered
            THEN RAISE(ABORT, 'Insufficient stock to place this order.')
        END;
    END;
    """)

    # Trigger: Prevent deletion of items that have existing non-cancelled orders
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
    print("Database initialized successfully with all tables and triggers.")

# ======================================================================
# HELPER FUNCTIONS
# ======================================================================

def generate_hashed_otp():
    """
    Generates a 4-digit OTP and returns both:
        - plaintext OTP (for user/buyer)
        - hashed OTP (for admin verification)
    Hashing uses SHA-256 truncated to 8 characters.
    """
    otp = str(random.randint(1000, 9999))
    hashed = hashlib.sha256(otp.encode()).hexdigest()[:8]

    # Print OTP for testing/admin convenience
    print("\n" + "="*50)
    print(" OTP GENERATED FOR ADMIN/TESTING ".center(50, "="))
    print(f" Plaintext OTP: {otp}".center(50))
    print("="*50 + "\n")

    return otp, hashed

def check_otp(submitted_otp, stored_hash):
    """
    Checks if the submitted OTP matches the stored hashed OTP.
    Returns True if valid, False otherwise.
    """
    if not submitted_otp or not stored_hash:
        return False
    hashed_submission = hashlib.sha256(str(submitted_otp).encode()).hexdigest()[:8]
    return hashed_submission == stored_hash

def generate_order_id():
    """
    Generates a unique order ID string like "ORD-XXXXXXXX" where
    XXXXXXXX is a random combination of uppercase letters and digits.
    """
    return "ORD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

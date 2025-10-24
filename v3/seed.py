import sqlite3
import bcrypt        # For hashing passwords securely
import os
import random        # For generating OTPs
import hashlib       # For hashing OTPs
from datetime import datetime, timedelta

# ------------------------------
# CONFIGURATION
# ------------------------------
DB_FILE = "database.db"

# Remove existing DB to start fresh
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------

def get_db():
    """
    Returns a connection to the SQLite database.
    Uses sqlite3.Row so we can access columns by name.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_from_utils():
    """
    Imports and executes the init_db() function from utils.py
    to create tables, triggers, and any initial schema required.
    Exits with error if utils.py or init_db is not found.
    """
    try:
        from utils import init_db
        init_db()
        print("Database schema and triggers created successfully.")
    except ImportError:
        print("Error: Could not import init_db from utils.py. Make sure it exists.")
        exit(1)

def generate_test_otp():
    """
    Generate a 4-digit OTP and a hashed version for seeding orders.
    The hashed OTP uses SHA-256 (first 8 chars) to simulate real hashing.
    Returns: (otp, hashed_otp)
    """
    otp = str(random.randint(1000, 9999))   # Random 4-digit OTP
    hashed = hashlib.sha256(otp.encode()).hexdigest()[:8]  # Simulated hashed OTP
    return otp, hashed

# ------------------------------
# SEED DATA
# ------------------------------

def seed_data():
    """
    Seeds the database with:
    1. Users
    2. Items
    3. Orders (with OTPs)
    """
    conn = get_db()
    cur = conn.cursor()
    print("Seeding data...")

    # ------------------------------
    # 1. Seed Users
    # ------------------------------
    users_to_add = [
        ('Alice Wonder', 'alice@example.com', 'alice123'),
        ('Bob Builder', 'bob@example.com', 'bob123'),
        ('Charlie Chocolate', 'charlie@example.com', 'charlie123'),
        ('Diana Prince', 'diana@example.com', 'diana123')
    ]
    for name, email, password in users_to_add:
        # Hash passwords securely using bcrypt
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, hashed_pw)
        )
    print(f"-> Seeded {len(users_to_add)} users.")

    # ------------------------------
    # 2. Seed Items
    # ------------------------------
    # Each item has: seller_id, name, description, price, category, quantity
    items_to_add = [
        (1, 'Introduction to Python', 'A beginner-friendly textbook.', 250.00, 'Books', 3),
        (1, 'Scientific Calculator', 'Casio FX-991EX, gently used.', 800.00, 'Electronics', 1),
        (1, 'Study Lamp', 'Bright LED lamp with adjustable neck.', 450.00, 'Furniture', 2),
        (2, 'Acoustic Guitar', 'Yamaha F310, includes a bag.', 4000.00, 'Miscellaneous', 1),
        (2, 'Electric Kettle', '1.5L capacity, great for hostels.', 600.00, 'Electronics', 4),
        (3, 'Set of 12 Gel Pens', 'Unopened pack of assorted colors.', 120.00, 'Stationery', 10),
        (3, 'Data Structures & Algo', 'Classic textbook by Cormen.', 550.00, 'Books', 1),
    ]
    for seller_id, name, desc, price, cat, qty in items_to_add:
        cur.execute(
            "INSERT INTO items (seller_id, name, description, price, category, quantity) VALUES (?, ?, ?, ?, ?, ?)",
            (seller_id, name, desc, price, cat, qty)
        )
    print(f"-> Seeded {len(items_to_add)} items.")

    # ------------------------------
    # 3. Seed Orders with OTPs
    # ------------------------------
    # Note: Database triggers will automatically decrement item quantity if needed.

    # Order 1: Completed order
    otp1, hashed1 = generate_test_otp()
    cur.execute(
        "INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('ORD-TEST001', 2, 1, 1, 250.00, 1, 'completed', otp1, hashed1)
    )

    # Order 2: In Transit (to test admin panel)
    otp2, hashed2 = generate_test_otp()
    print(f"--> Admin Test: Order ORD-TEST002 (Kettle) has OTP: {otp2}")
    cur.execute(
        "INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('ORD-TEST002', 3, 2, 5, 600.00, 1, 'in_transit', otp2, hashed2)
    )

    # Order 3: Pending (admin panel test)
    otp3, hashed3 = generate_test_otp()
    cur.execute(
        "INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('ORD-TEST003', 1, 3, 6, 240.00, 2, 'pending', otp3, hashed3)
    )

    # Order 4: Cancelled
    otp4, hashed4 = generate_test_otp()
    cur.execute(
        "INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('ORD-TEST004', 4, 1, 1, 250.00, 1, 'cancelled', otp4, hashed4)
    )

    print("-> Seeded 4 historical orders with OTPs.")

    # Commit all changes and close DB
    conn.commit()
    conn.close()
    print("Seeding complete!")

# ------------------------------
# MAIN EXECUTION
# ------------------------------
if __name__ == "__main__":
    # Step 1: Initialize database tables and triggers
    init_db_from_utils()
    
    # Step 2: Seed users, items, and orders
    seed_data()

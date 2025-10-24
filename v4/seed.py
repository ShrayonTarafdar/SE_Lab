import sqlite3
import bcrypt
import os
import random
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DB_FILE = "database.db"
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# --- HELPER FUNCTIONS ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_from_utils():
    try:
        from utils import init_db
        init_db()
        print("Database schema and triggers created successfully.")
    except ImportError:
        print("Error: Could not import init_db from utils.py. Make sure it exists.")
        exit(1)

def generate_test_otp():
    """A helper to generate OTPs specifically for the seed script."""
    otp = str(random.randint(1000, 9999))
    hashed = hashlib.sha256(otp.encode()).hexdigest()[:8]
    return otp, hashed

# --- SEED DATA ---
def seed_data():
    conn = get_db()
    cur = conn.cursor()
    print("Seeding data...")

    # 1. Seed Users
    users_to_add = [
        ('Alice Wonder', 'alice@example.com', 'alice123'),
        ('Bob Builder', 'bob@example.com', 'bob123'),
        ('Charlie Chocolate', 'charlie@example.com', 'charlie123'),
        ('Diana Prince', 'diana@example.com', 'diana123')
    ]
    for name, email, password in users_to_add:
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, hashed_pw))
    print(f"-> Seeded {len(users_to_add)} users.")

    # 2. Seed Items
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
        cur.execute("INSERT INTO items (seller_id, name, description, price, category, quantity) VALUES (?, ?, ?, ?, ?, ?)",
                    (seller_id, name, desc, price, cat, qty))
    print(f"-> Seeded {len(items_to_add)} items.")
    
    # 3. Seed Orders with OTPs
    # NOTE: The triggers will automatically decrement the stock.

    # Order 1: Completed
    otp1, hashed1 = generate_test_otp()
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST001', 2, 1, 1, 250.00, 1, 'completed', otp1, hashed1))

    # Order 2: In Transit (This is the one you will test in the admin panel)
    otp2, hashed2 = generate_test_otp()
    print(f"--> Admin Test: Order ORD-TEST002 (Kettle) has OTP: {otp2}")
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST002', 3, 2, 5, 600.00, 1, 'in_transit', otp2, hashed2))

    # Order 3: Pending (This is the one you will test in the admin panel)
    otp3, hashed3 = generate_test_otp()
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST003', 1, 3, 6, 240.00, 2, 'pending', otp3, hashed3))

    # Order 4: Cancelled
    otp4, hashed4 = generate_test_otp()
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status, otp, hashed_otp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST004', 4, 1, 1, 250.00, 1, 'cancelled', otp4, hashed4))

    print("-> Seeded 4 historical orders with OTPs.")

    conn.commit()
    conn.close()
    print("Seeding complete!")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    init_db_from_utils()
    seed_data()
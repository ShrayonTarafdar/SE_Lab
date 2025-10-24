import sqlite3
import bcrypt
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DB_FILE = "database.db"
# This script will DELETE the old database file to ensure a clean start.
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# --- HELPER FUNCTIONS ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_from_utils():
    # We import your utils to use the exact same schema creation logic
    # This ensures the seed script is always in sync with your app
    try:
        from utils import init_db
        init_db()
        print("Database schema and triggers created successfully.")
    except ImportError:
        print("Error: Could not import init_db from utils.py. Make sure it exists.")
        exit(1)

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

    # 2. Seed Items from different sellers
    items_to_add = [
        # Seller: Alice (user_id=1)
        (1, 'Introduction to Python', 'A beginner-friendly textbook.', 250.00, 'Books', 3),
        (1, 'Scientific Calculator', 'Casio FX-991EX, gently used.', 800.00, 'Electronics', 1),
        (1, 'Study Lamp', 'Bright LED lamp with adjustable neck.', 450.00, 'Furniture', 2),
        # Seller: Bob (user_id=2)
        (2, 'Acoustic Guitar', 'Yamaha F310, includes a bag.', 4000.00, 'Miscellaneous', 1),
        (2, 'Electric Kettle', '1.5L capacity, great for hostels.', 600.00, 'Electronics', 4),
        # Seller: Charlie (user_id=3)
        (3, 'Set of 12 Gel Pens', 'Unopened pack of assorted colors.', 120.00, 'Stationery', 10),
        (3, 'Data Structures & Algo', 'Classic textbook by Cormen.', 550.00, 'Books', 1),
    ]
    for seller_id, name, desc, price, cat, qty in items_to_add:
        cur.execute("INSERT INTO items (seller_id, name, description, price, category, quantity) VALUES (?, ?, ?, ?, ?, ?)",
                    (seller_id, name, desc, price, cat, qty))
    print(f"-> Seeded {len(items_to_add)} items.")
    
    # 3. Seed Orders to create a history
    # NOTE: The triggers will automatically decrement the stock for these orders.
    # Order: Bob (2) buys Alice's (1) Python book (item 1)
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST001', 2, 1, 1, 250.00, 1, 'completed'))
    # Order: Charlie (3) buys Bob's (2) Kettle (item 5)
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST002', 3, 2, 5, 600.00, 1, 'in_transit'))
    # Order: Alice (1) buys Charlie's (3) Gel Pens (item 6)
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST003', 1, 3, 6, 120.00, 2, 'pending'))
    # Order: Diana (4) buys Alice's (1) other Python book (item 1)
    cur.execute("INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, order_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('ORD-TEST004', 4, 1, 1, 250.00, 1, 'cancelled'))

    print("-> Seeded 4 historical orders.")

    conn.commit()
    conn.close()
    print("Seeding complete!")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    init_db_from_utils()
    seed_data()
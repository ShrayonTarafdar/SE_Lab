import sqlite3

items = [
    ("Hostel Chair", "Slightly used wooden chair", 400, "Furniture"),
    ("Math Textbook", "Calculus reference guide", 200, "Books"),
    ("Cycle", "Hero Sprint mountain bike", 2500, "Transport")
]

conn = sqlite3.connect("database.db")
for name, desc, price, category in items:
    conn.execute(
        "INSERT INTO items (seller_id, name, description, price, category, status) VALUES (1, ?, ?, ?, ?, 'available')",
        (name, desc, price, category)
    )
conn.commit()
conn.close()

print("Sample items added!")

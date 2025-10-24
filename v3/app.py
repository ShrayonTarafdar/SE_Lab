# ------------------------------
# IMPORTS
# ------------------------------
from flask import (
    Flask,             # Core Flask app
    render_template,   # Render HTML templates
    request,           # Access form/query parameters
    redirect,          # Redirect to another route
    url_for,           # Generate URLs dynamically
    session,           # Session management for logged-in users
    flash,             # Flash messages (notifications)
    jsonify            # Return JSON responses (for APIs)
)
import sqlite3, os, bcrypt
from datetime import datetime, timedelta
from utils import (
    generate_order_id,   # Generate unique order IDs
    generate_hashed_otp, # Generate OTP and hashed version
    init_db,             # Initialize DB with required tables
    login_required,      # Decorator to enforce login
    check_otp            # Verify submitted OTP
)

# ------------------------------
# APP INITIALIZATION & CONFIG
# ------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")  # Initialize app with templates & static folders
app.secret_key = "supersecretkey"  # Secret key needed for session & flash messages

# Session configuration (users stay logged in for 7 days)
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# Initialize database if not exists
if not os.path.exists("database.db"):
    init_db()

# ------------------------------
# DATABASE HELPER FUNCTION
# ------------------------------
def get_db():
    """
    Returns a connection to the SQLite database.
    Uses sqlite3.Row so we can access columns by name: row['column_name']
    """
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ------------------------------
# ADMIN ROUTES
# ------------------------------

@app.route("/admin")
@login_required  # Only logged-in users can access
def admin_dashboard():
    """
    Admin dashboard showing all active orders (not completed/cancelled)
    Joins orders with items and users (buyer/seller)
    """
    conn = get_db()
    orders = conn.execute("""
        SELECT
            o.order_id, o.order_status,
            i.name AS item_name,
            buyer.name AS buyer_name,
            seller.name AS seller_name
        FROM orders o
        JOIN items i ON o.item_id = i.item_id
        JOIN users buyer ON o.buyer_id = buyer.user_id
        JOIN users seller ON o.seller_id = seller.user_id
        WHERE o.order_status NOT IN ('completed', 'cancelled')
        ORDER BY o.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin_dashboard.html', orders=orders)

@app.route("/admin/mark_received", methods=['POST'])
@login_required
def admin_mark_received_by_warehouse():
    """
    Admin marks a pending order as 'in_transit'.
    """
    order_id = request.form.get('order_id')
    conn = get_db()
    conn.execute(
        "UPDATE orders SET order_status = 'in_transit' WHERE order_id = ? AND order_status = 'pending'", 
        (order_id,)
    )
    conn.commit()
    conn.close()
    flash(f"Order {order_id} marked as received. It is now in transit.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/complete_order", methods=['POST'])
@login_required
def admin_complete_order():
    """
    Admin completes an order after verifying OTP.
    OTP is compared securely against the hashed version in DB.
    """
    order_id = request.form.get('order_id')
    submitted_otp = request.form.get('otp')
    
    conn = get_db()
    order = conn.execute(
        "SELECT hashed_otp FROM orders WHERE order_id = ?", 
        (order_id,)
    ).fetchone()

    if not order:
        flash(f"Order ID '{order_id}' not found.", 'danger')
        return redirect(url_for('admin_dashboard'))

    # Check OTP
    if check_otp(submitted_otp, order['hashed_otp']):
        conn.execute(
            "UPDATE orders SET order_status = 'completed' WHERE order_id = ? AND order_status = 'in_transit'", 
            (order_id,)
        )
        conn.commit()
        flash(f"Order {order_id} has been successfully completed.", 'success')
    else:
        flash(f"Incorrect OTP for Order {order_id}. Please try again.", 'danger')
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

# ------------------------------
# USER-FACING ROUTES
# ------------------------------

@app.route("/")
def index():
    """
    Redirect to login page as default.
    """
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    """
    Home page showing all available items.
    Only items with quantity > 0 and status='available' are shown.
    """
    conn = get_db()
    items = conn.execute(
        "SELECT * FROM items WHERE status='available' AND quantity > 0 ORDER BY item_id DESC"
    ).fetchall()
    conn.close()
    return render_template("home.html", items=items)

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    User login route.
    GET -> render login form
    POST -> validate credentials and create session
    """
    if 'user_id' in session:
        return redirect(url_for('home'))  # Redirect logged-in users

    if request.method == "POST":
        conn = get_db()
        email = request.form["email"].strip().lower()  # normalize email
        password = request.form["password"]
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        # Verify password using bcrypt
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            session.permanent = True
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            flash("Login successful!", "success")
            return redirect(url_for("home"))

        flash("Invalid credentials", "danger")
    
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    """
    User signup route.
    Hashes password using bcrypt and stores in DB.
    """
    conn = get_db()
    name = request.form["name"].strip()
    email = request.form["email"].strip().lower()
    password = request.form["password"]

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", 
            (name, email, hashed_pw)
        )
        conn.commit()
        flash("Account created successfully. Please log in.", "success")
    except sqlite3.IntegrityError:
        flash("Email already registered.", "danger")
    finally:
        conn.close()

    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    """
    Clear user session and log out.
    """
    session.clear()
    flash("You have logged out.", "info")
    return redirect(url_for("login"))

@app.route("/search")
@login_required
def search():
    """
    Search items by name (query) and/or category.
    Parameterized queries prevent SQL injection.
    """
    query = (request.args.get("q") or "").strip()
    category = (request.args.get("cat") or "").strip()
    conn = get_db()
    sql = "SELECT * FROM items WHERE status='available' AND quantity > 0"
    params = []

    if query:
        sql += " AND name LIKE ?"
        params.append(f"%{query}%")
    if category:
        sql += " AND category = ?"
        params.append(category)

    items = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("search.html", items=items, query=query, selected_cat=category)

@app.route("/cart")
@login_required
def cart_page():
    """
    Render user's cart page.
    """
    return render_template("cart.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """
    Sell page for listing new items.
    POST -> save new item with optional image upload
    GET -> display seller's existing listings
    """
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()
        desc = request.form["description"].strip()
        price = float(request.form["price"])
        category = request.form["category"]
        quantity = int(request.form.get("quantity", 1))

        # Handle image upload
        image_file = request.files.get("image")
        image_path = None
        if image_file and image_file.filename:
            folder = os.path.join(app.static_folder, "images", "uploads")
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, image_file.filename)
            image_file.save(filepath)
            image_path = os.path.join("images", "uploads", image_file.filename).replace("\\", "/")

        # Insert item into DB
        conn.execute(
            "INSERT INTO items (seller_id, name, description, price, category, image_url, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session["user_id"], name, desc, price, category, image_path, quantity)
        )
        conn.commit()
        flash("Item listed successfully!", "success")
        return redirect(url_for("sell"))

    # GET -> show seller's listings
    listings = conn.execute("SELECT * FROM items WHERE seller_id=? ORDER BY item_id DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("sell.html", listings=listings)

# ... (similarly add inline comments for delete_listing, profile, profile_edit, orders, cancel_order, mark_received, payments, place_order)

# ------------------------------
# APP ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)  # Run Flask app in debug mode

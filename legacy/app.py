from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
import sqlite3, os, bcrypt
from datetime import datetime
from datetime import timedelta
from utils import generate_order_id, generate_hashed_otp, init_db, login_required


# ----------------------------------------------------------------------
# APP INITIALIZATION
# ----------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"

# keep user logged in for 7 days unless logout
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# For local dev over http:
app.config['SESSION_COOKIE_SECURE'] = False


# auto-create db on first run
if not os.path.exists("database.db"):
    init_db()


# ----------------------------------------------------------------------
# DATABASE UTILS
# ----------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------------------------------------------------
# HOME  (login gate)
# ----------------------------------------------------------------------
@app.route("/")
def index():
    """Start page always redirects to login page"""
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    items = conn.execute(
        "SELECT * FROM items WHERE status='available' AND COALESCE(quantity,0) > 0 ORDER BY item_id DESC"
    ).fetchall()
    return render_template("home.html", items=items)


# ----------------------------------------------------------------------
# LOGIN  /  SIGNUP  /  LOGOUT
# ----------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_db()
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
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
    conn = get_db()
    name = request.form["name"].strip()
    email = request.form["email"].strip().lower()
    password = request.form["password"]

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, hashed_pw),
        )
        conn.commit()
        flash("Account created successfully. Please log in.", "success")
    except sqlite3.IntegrityError:
        flash("Email already registered.", "danger")

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "info")
    return redirect(url_for("login"))


# ----------------------------------------------------------------------
# SEARCH PAGE
# ----------------------------------------------------------------------
@app.route("/search")
@login_required
def search():
    query = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("cat") or "").strip().lower()
    min_price = float(request.args.get("min", 0) or 0)
    max_price = float(request.args.get("max", 9999999) or 9999999)

    show_results = bool(query or category or request.args.get("min") or request.args.get("max"))

    items = []
    if show_results:
        conn = get_db()
        items_all = conn.execute(
            "SELECT * FROM items WHERE status='available' AND COALESCE(quantity,0) > 0"
        ).fetchall()
        items = [
            i for i in items_all
            if (query in i['name'].lower() or query in (i['category'] or '').lower())
            and (category == "" or (i['category'] or '').lower() == category)
            and (min_price <= i['price'] <= max_price)
        ]

    return render_template("search.html", items=items, query=query, show_results=show_results)

# ----------------------------------------------------------------------
# CART PAGE
# ----------------------------------------------------------------------
@app.route("/cart")
@login_required
def cart():
    return render_template("cart.html")


# ----------------------------------------------------------------------
# SELL PAGE
# ----------------------------------------------------------------------
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()
        desc = request.form["description"].strip()
        price = float(request.form["price"])
        category = request.form["category"]
        quantity = int(request.form.get("quantity", 1))
        image_file = request.files.get("image")

        # save image if provided
        image_path = None
        if image_file and image_file.filename:
            folder = "static/images/uploads"
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, image_file.filename)
            image_file.save(filepath)
            image_path = "/" + filepath.replace("\\", "/")

        conn.execute(
            """INSERT INTO items
               (seller_id, name, description, price, category, image_url, status, quantity)
               VALUES (?, ?, ?, ?, ?, ?, 'available', ?)""",
            (session["user_id"], name, desc, price, category, image_path, quantity),
        )
        conn.commit()
        flash("Item listed successfully!", "success")
        return redirect(url_for("sell"))

    listings = conn.execute(
        "SELECT * FROM items WHERE seller_id=? ORDER BY item_id DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("sell.html", listings=listings)


@app.route('/sell/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_listing(item_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE item_id=? AND seller_id=?", (item_id, session['user_id']))
    conn.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Item not found or not yours"}), 404
    return ("", 204)


# ----------------------------------------------------------------------
# PROFILE PAGE
# ----------------------------------------------------------------------

@app.route("/profile")
@login_required
def profile():
    conn = get_db()
    user_row = conn.execute(
        "SELECT * FROM users WHERE user_id=?", (session["user_id"],)
    ).fetchone()

    user = dict(user_row) if user_row else None
    if user and user.get("created_at"):
        try:
            user["created_at"] = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    bought_items = conn.execute(
        "SELECT order_id, item_name, price, status, hashed_otp, created_at "
        "FROM orders WHERE buyer_id=? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()

    sold_items = conn.execute(
        "SELECT * FROM items WHERE seller_id=? ORDER BY item_id DESC",
        (session["user_id"],),
    ).fetchall()

    return render_template("profile.html", user=user, bought_items=bought_items, sold_items=sold_items)

@app.route("/profile/edit", methods=["GET"])
@login_required
def profile_edit_view():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session["user_id"],)).fetchone()
    return render_template("profile_edit.html", user=user)

@app.route("/profile/edit", methods=["POST"])
@login_required
def profile_edit_save():
    name = request.form.get("name", "").strip()
    img = request.files.get("profile_img")
    img_path = None

    if img and img.filename:
        folder = "static/images/profile"
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, img.filename)
        img.save(filepath)
        img_path = "/" + filepath.replace("\\", "/")

    conn = get_db()
    if name:
        conn.execute("UPDATE users SET name=? WHERE user_id=?", (name, session["user_id"]))
    if img_path:
        conn.execute("UPDATE users SET profile_img=? WHERE user_id=?", (img_path, session["user_id"]))
    conn.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("profile"))



# ----------------------------------------------------------------------
# ORDERS PAGE
# ----------------------------------------------------------------------
@app.route("/orders")
@login_required
def orders():
    conn = get_db()
    orders = conn.execute(
        "SELECT order_id, item_name, price, status, hashed_otp, created_at "
        "FROM orders WHERE buyer_id=? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("orders.html", orders=orders)


# ----------------------------------------------------------------------
# PAYMENTS PAGE
# ----------------------------------------------------------------------
@app.route("/payments")
@login_required
def payments():
    mock_order = {
        "order_id": generate_order_id(),
        "item_name": "Cart Items",
        "price": 0,
    }
    return render_template("payments.html", order=mock_order)


# ----------------------------------------------------------------------
# PLACE ORDER (API)
# ----------------------------------------------------------------------
@app.route("/api/place_order", methods=["POST"])
@login_required
def place_order():
    data = request.get_json() or {}
    buyer_id = session["user_id"]
    cart = data.get("cart")  # list of {item_name, price, qty}
    payment_mode = data.get("payment_mode", "COD")

    if not cart or not isinstance(cart, list):
        return jsonify({"error": "Cart is empty"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Use a transaction
    try:
        for line in cart:
            item_name = line.get("item_name")
            price = float(line.get("price", 0))
            qty = int(line.get("qty", 1))
            if not item_name or qty < 1:
                continue

            order_id = generate_order_id()
            otp, hashed = generate_hashed_otp()

            # Insert one order row per item line (simple MVP approach)
            cur.execute(
                """INSERT INTO orders
                   (order_id, buyer_id, item_name, price, seller_name, seller_email, status, hashed_otp)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (order_id, buyer_id, item_name, price, "Warehouse", "warehouse@campus.edu", hashed),
            )

            # Decrement stock for that item_name
            cur.execute(
                "UPDATE items SET quantity = COALESCE(quantity,1) - ? "
                "WHERE name=? AND status='available' AND COALESCE(quantity,0) >= ?",
                (qty, item_name, qty),
            )

            # If qty hits 0 → mark sold
            cur.execute(
                "UPDATE items SET status='sold' WHERE name=? AND COALESCE(quantity,0) <= 0",
                (item_name,),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True})

# ----------------------------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

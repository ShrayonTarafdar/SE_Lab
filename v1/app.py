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
# LOGIN GATE
# ----------------------------------------------------------------------
@app.route("/")
def index():
    """
    This route now ALWAYS redirects to the login page,
    ensuring it's the first thing a new visitor sees.
    """
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    conn = get_db()
    items = conn.execute(
        "SELECT * FROM items WHERE status='available' AND quantity > 0 ORDER BY item_id DESC"
    ).fetchall()
    conn.close()
    return render_template("home.html", items=items)


# ----------------------------------------------------------------------
# LOGIN  /  SIGNUP  /  LOGOUT
# ----------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == "POST":
        conn = get_db()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
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
    finally:
        conn.close()

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
        image_path = None

        if image_file and image_file.filename:
            folder = os.path.join(app.static_folder, "images", "uploads")
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, image_file.filename)
            image_file.save(filepath)
            image_path = os.path.join("images", "uploads", image_file.filename).replace("\\", "/")

        conn.execute(
            """INSERT INTO items
               (seller_id, name, description, price, category, image_url, quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session["user_id"], name, desc, price, category, image_path, quantity),
        )
        conn.commit()
        flash("Item listed successfully!", "success")
        return redirect(url_for("sell"))

    listings = conn.execute(
        "SELECT * FROM items WHERE seller_id=? ORDER BY item_id DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("sell.html", listings=listings)


@app.route('/sell/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_listing(item_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE item_id=? AND seller_id=?", (item_id, session['user_id']))
    conn.commit()
    conn.close()
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
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session["user_id"],)).fetchone()

    bought_items = conn.execute("""
        SELECT o.order_id, i.name as item_name, o.price, o.order_status as status, o.created_at
        FROM orders o
        JOIN items i ON o.item_id = i.item_id
        WHERE o.buyer_id = ? 
        ORDER BY o.created_at DESC
    """, (session["user_id"],)).fetchall()

    sold_items = conn.execute(
        "SELECT * FROM items WHERE seller_id=? ORDER BY item_id DESC",
        (session["user_id"],),
    ).fetchall()
    
    conn.close()
    return render_template("profile.html", user=user, bought_items=bought_items, sold_items=sold_items)

@app.route("/profile/edit", methods=["GET"])
@login_required
def profile_edit_view():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("profile_edit.html", user=user)

@app.route("/profile/edit", methods=["POST"])
@login_required
def profile_edit_save():
    name = request.form.get("name", "").strip()
    img = request.files.get("profile_img")
    conn = get_db()
    if name:
        conn.execute("UPDATE users SET name=? WHERE user_id=?", (name, session["user_id"]))
    if img and img.filename:
        folder = os.path.join(app.static_folder, "images", "profile")
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, img.filename)
        img.save(filepath)
        img_path = os.path.join("images", "profile", img.filename).replace("\\", "/")
        conn.execute("UPDATE users SET profile_img=? WHERE user_id=?", (img_path, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Profile updated.", "success")
    return redirect(url_for("profile"))

# ----------------------------------------------------------------------
# ORDERS PAGE (FIXED)
# ----------------------------------------------------------------------
@app.route("/orders")
@login_required
def orders():
    conn = get_db()
    user_orders = conn.execute("""
        SELECT o.order_id, o.price, o.order_status as status, o.created_at, o.hashed_otp, i.name as item_name
        FROM orders o
        JOIN items i ON o.item_id = i.item_id
        WHERE o.buyer_id = ?
        ORDER BY o.created_at DESC
    """,(session["user_id"],)).fetchall()
    conn.close()
    # FIX: Pass the 'user_orders' variable to the template, not the 'orders' function.
    return render_template("orders.html", orders=user_orders)


# ----------------------------------------------------------------------
# PAYMENTS PAGE
# ----------------------------------------------------------------------
@app.route("/payments")
@login_required
def payments():
    return render_template("payments.html")


# ----------------------------------------------------------------------
# PLACE ORDER (API)
# ----------------------------------------------------------------------
@app.route("/api/place_order", methods=["POST"])
@login_required
def place_order():
    data = request.get_json() or {}
    buyer_id = session["user_id"]
    cart = data.get("cart")
    payment_mode = data.get("payment_mode", "COD")

    if not cart or not isinstance(cart, list):
        return jsonify({"ok": False, "error": "Cart is invalid or empty"}), 400

    conn = get_db()
    try:
        with conn:
            cur = conn.cursor()
            for item in cart:
                item_id = int(item.get("id"))
                quantity_ordered = int(item.get("qty", 1))
                item_name = item.get("name")
                item_data = cur.execute(
                    "SELECT seller_id, price, quantity FROM items WHERE item_id = ? AND status = 'available'", (item_id,)
                ).fetchone()
                if not item_data or item_data["quantity"] < quantity_ordered:
                    raise ValueError(f"'{item_name}' is out of stock or unavailable.")
                order_id = generate_order_id()
                _otp, hashed_otp = generate_hashed_otp()
                seller_id = item_data["seller_id"]
                price_at_sale = item_data["price"] * quantity_ordered
                cur.execute(
                    """
                    INSERT INTO orders (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, payment_mode, hashed_otp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, buyer_id, seller_id, item_id, price_at_sale, quantity_ordered, payment_mode, hashed_otp)
                )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except sqlite3.Error as e:
        return jsonify({"ok": False, "error": f"A database error occurred: {e}"}), 500
    finally:
        conn.close()

    return jsonify({"ok": True, "message": "Order placed successfully!"})


# ----------------------------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
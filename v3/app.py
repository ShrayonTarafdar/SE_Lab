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
from datetime import datetime, timedelta
from utils import (
    generate_order_id, generate_hashed_otp, init_db, login_required, check_otp
)

# ----------------------------------------------------------------------
# APP INITIALIZATION & CONFIG
# ----------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
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
# ADMIN ROUTES (Simplified Module)
# ----------------------------------------------------------------------

@app.route("/admin")
@login_required # An admin must also be a logged-in user
def admin_dashboard():
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
    order_id = request.form.get('order_id')
    conn = get_db()
    conn.execute("UPDATE orders SET order_status = 'in_transit' WHERE order_id = ? AND order_status = 'pending'", (order_id,))
    conn.commit()
    conn.close()
    flash(f"Order {order_id} marked as received. It is now in transit.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/complete_order", methods=['POST'])
@login_required
def admin_complete_order():
    order_id = request.form.get('order_id')
    submitted_otp = request.form.get('otp')
    
    conn = get_db()
    order = conn.execute("SELECT hashed_otp FROM orders WHERE order_id = ?", (order_id,)).fetchone()

    if not order:
        flash(f"Order ID '{order_id}' not found.", 'danger')
        return redirect(url_for('admin_dashboard'))

    if check_otp(submitted_otp, order['hashed_otp']):
        conn.execute("UPDATE orders SET order_status = 'completed' WHERE order_id = ? AND order_status = 'in_transit'", (order_id,))
        conn.commit()
        flash(f"Order {order_id} has been successfully completed.", 'success')
    else:
        flash(f"Incorrect OTP for Order {order_id}. Please try again.", 'danger')
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

# ----------------------------------------------------------------------
# USER-FACING ROUTES
# ----------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    conn = get_db()
    items = conn.execute("SELECT * FROM items WHERE status='available' AND quantity > 0 ORDER BY item_id DESC").fetchall()
    conn.close()
    return render_template("home.html", items=items)

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
        conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, hashed_pw))
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

@app.route("/cart")
@login_required
def cart_page():
    return render_template("cart.html")

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
            "INSERT INTO items (seller_id, name, description, price, category, image_url, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session["user_id"], name, desc, price, category, image_path, quantity)
        )
        conn.commit()
        flash("Item listed successfully!", "success")
        return redirect(url_for("sell"))
    listings = conn.execute("SELECT * FROM items WHERE seller_id=? ORDER BY item_id DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("sell.html", listings=listings)

@app.route('/sell/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_listing(item_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM items WHERE item_id=? AND seller_id=?", (item_id, session['user_id']))
        conn.commit()
        if cur.rowcount == 0: return jsonify({"error": "Item not found or not yours"}), 404
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()
    return ("", 204)

@app.route("/profile")
@login_required
def profile():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (session["user_id"],)).fetchone()
    bought_items = conn.execute("SELECT o.order_id, i.name as item_name, o.price, o.order_status as status, o.created_at FROM orders o JOIN items i ON o.item_id = i.item_id WHERE o.buyer_id = ? ORDER BY o.created_at DESC", (session["user_id"],)).fetchall()
    sold_items = conn.execute("""
        SELECT i.name, i.price, i.status, b.name as buyer_name
        FROM items i LEFT JOIN orders o ON i.item_id = o.item_id
        LEFT JOIN users b ON o.buyer_id = b.user_id
        WHERE i.seller_id = ? ORDER BY i.item_id DESC
    """, (session["user_id"],)).fetchall()
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

@app.route("/orders")
@login_required
def orders():
    conn = get_db()
    user_orders = conn.execute("""
        SELECT o.order_id, o.price, o.order_status as status, o.created_at, o.otp, i.name as item_name
        FROM orders o
        JOIN items i ON o.item_id = i.item_id
        WHERE o.buyer_id = ?
        ORDER BY o.created_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("orders.html", orders=user_orders)

@app.route('/orders/cancel/<string:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    conn = get_db()
    try:
        with conn:
            cur = conn.cursor()
            order = cur.execute("SELECT * FROM orders WHERE order_id = ? AND buyer_id = ?", (order_id, session['user_id'])).fetchone()
            if not order: return jsonify({"ok": False, "error": "Order not found or permission denied."}), 404
            if order['order_status'] not in ['pending', 'in_transit', 'ready_for_pickup']: return jsonify({"ok": False, "error": "This order cannot be cancelled."}), 400
            cur.execute("UPDATE orders SET order_status = 'cancelled' WHERE order_id = ?", (order_id,))
            cur.execute("UPDATE items SET quantity = quantity + ?, status = 'available' WHERE item_id = ?", (order['quantity_ordered'], order['item_id']))
    except sqlite3.Error as e: return jsonify({"ok": False, "error": "A database error occurred."}), 500
    finally: conn.close()
    return jsonify({"ok": True, "message": "Order successfully cancelled."})

@app.route('/orders/mark_received/<string:order_id>', methods=['POST'])
@login_required
def mark_received(order_id):
    conn = get_db()
    try:
        with conn:
            cur = conn.cursor()
            order = cur.execute("SELECT * FROM orders WHERE order_id = ? AND buyer_id = ?", (order_id, session['user_id'])).fetchone()
            if not order: return jsonify({"ok": False, "error": "Order not found or permission denied."}), 404
            if order['order_status'] in ['completed', 'cancelled']: return jsonify({"ok": False, "error": "This order is already finalized."}), 400
            cur.execute("UPDATE orders SET order_status = 'completed' WHERE order_id = ?", (order_id,))
    except sqlite3.Error as e: return jsonify({"ok": False, "error": "A database error occurred."}), 500
    finally: conn.close()
    return jsonify({"ok": True, "message": "Order marked as received."})

@app.route("/payments")
@login_required
def payments():
    return render_template("payments.html")

@app.route("/api/place_order", methods=["POST"])
@login_required
def place_order():
    data = request.get_json() or {}
    cart = data.get("cart")
    if not cart: return jsonify({"ok": False, "error": "Cart is invalid or empty"}), 400

    conn = get_db()
    try:
        with conn:
            cur = conn.cursor()
            for item in cart:
                item_id = int(item.get("id"))
                quantity_ordered = int(item.get("qty", 1))
                
                item_data = cur.execute("SELECT seller_id, price FROM items WHERE item_id = ? AND status = 'available' AND quantity >= ?", (item_id, quantity_ordered)).fetchone()
                if not item_data:
                    raise ValueError(f"'{item.get('name')}' is out of stock or unavailable.")
                
                order_id = generate_order_id()
                otp, hashed_otp = generate_hashed_otp()
                seller_id = item_data["seller_id"]
                price_at_sale = item_data["price"] * quantity_ordered
                
                cur.execute(
                    """INSERT INTO orders 
                       (order_id, buyer_id, seller_id, item_id, price, quantity_ordered, payment_mode, otp, hashed_otp) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (order_id, session["user_id"], seller_id, item_id, price_at_sale, quantity_ordered, 'COD', otp, hashed_otp)
                )
    except (ValueError, sqlite3.IntegrityError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    finally:
        conn.close()

    return jsonify({"ok": True, "message": "Order placed successfully!"})


if __name__ == "__main__":
    app.run(debug=True)
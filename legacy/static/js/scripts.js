/* ============================================================
   CAMPUSKART — FINAL FRONTEND LOGIC (Coffee Theme)
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  console.log("CampusKart JS loaded");

  // Ensure cart exists
  if (!localStorage.getItem("cart"))
    localStorage.setItem("cart", JSON.stringify([]));

  highlightActiveSidebar();
  updateCartBadge();
  setupQuantityButtons();
  setupAddToCartButtons();
  setupRemoveButtons();
  setupCheckoutButton();
  setupToastContainer();
});

/* -------------------- Sidebar -------------------- */
function highlightActiveSidebar() {
  const links = document.querySelectorAll(".nav-menu a");
  links.forEach((link) => {
    if (window.location.pathname === link.getAttribute("href")) {
      link.style.background = "#a47148";
    }
  });
}

/* -------------------- Cart Badge -------------------- */
function updateCartBadge() {
  const cart = JSON.parse(localStorage.getItem("cart"));
  const badgeEl = document.querySelector("#cart-count");
  if (!badgeEl) return;
  badgeEl.textContent = cart.length ? cart.length : "";
}

/* -------------------- Add to Cart -------------------- */
function setupAddToCartButtons() {
  document.querySelectorAll(".add-to-cart").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const name = btn.dataset.name;
      const price = parseFloat(btn.dataset.price);
      const qtyEl = document.getElementById(`qty-${id}`);
      const qty = qtyEl ? parseInt(qtyEl.textContent) : 1;
      addItemToCart(id, name, price, qty);
      showToast(`${name} (x${qty}) added to cart`);
    });
  });
}

function addItemToCart(id, name, price, qty) {
  let cart = JSON.parse(localStorage.getItem("cart"));
  const existing = cart.find((i) => i.id === id);
  if (existing) existing.qty += qty;
  else cart.push({ id, name, price, qty });
  localStorage.setItem("cart", JSON.stringify(cart));
  updateCartBadge();
}

/* -------------------- Remove from Cart -------------------- */
function setupRemoveButtons() {
  document.querySelectorAll(".remove-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      removeFromCart(id);
    });
  });
}
function removeFromCart(id) {
  let cart = JSON.parse(localStorage.getItem("cart"));
  cart = cart.filter((i) => i.id !== id);
  localStorage.setItem("cart", JSON.stringify(cart));
  showToast("Item removed from cart");
  setTimeout(() => location.reload(), 500);
}

/* -------------------- Quantity Control -------------------- */
function setupQuantityButtons() {
  document.querySelectorAll(".qty-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      const qtyEl = document.getElementById(`qty-${id}`);
      if (!qtyEl) return;
      let qty = parseInt(qtyEl.textContent);
      if (btn.classList.contains("plus")) qty++;
      else if (btn.classList.contains("minus") && qty > 1) qty--;
      qtyEl.textContent = qty;
    });
  });
}

/* -------------------- Checkout -------------------- */
function setupCheckoutButton() {
  const btn = document.querySelector("#checkout-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const cart = JSON.parse(localStorage.getItem("cart"));
    if (!cart.length) {
      showToast("Your cart is empty");
      return;
    }

    try {
      showToast("Processing your order...");
      const res = await fetch("/api/place_order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart, payment_mode: "COD" }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        localStorage.removeItem("cart");
        showToast("Order placed successfully!");
        setTimeout(() => (window.location.href = "/orders"), 1000);
      } else {
        showToast(data.error || "Order failed", true);
      }
    } catch (err) {
      showToast("Network error during checkout", true);
    }
  });
}

/* -------------------- Toast Notifications -------------------- */
function setupToastContainer() {
  if (document.querySelector(".toast-container")) return;
  const div = document.createElement("div");
  div.className = "toast-container";
  document.body.appendChild(div);
}

function showToast(msg, isError = false) {
  const container = document.querySelector(".toast-container");
  if (!container) return alert(msg);
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.style.background = isError ? "#b94a48" : "#a47148";
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

/* -------------------- Utilities -------------------- */
function formatCurrency(v) {
  return "₹" + Number(v).toFixed(2);
}

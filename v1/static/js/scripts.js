/* ============================================================
   CAMPUSKART — FINAL FRONTEND LOGIC (Coffee Theme)
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  console.log("CampusKart JS loaded");

  if (!localStorage.getItem("cart")) {
    localStorage.setItem("cart", JSON.stringify([]));
  }

  updateCartBadge();
  setupAddToCartButtons();
  setupQuantityButtons(); // This is the function we are fixing
  setupRemoveFromCartButtons();
  setupCheckoutButton();
  setupToastContainer();
});

/* -------------------- Cart Badge -------------------- */
function updateCartBadge() {
  const cart = JSON.parse(localStorage.getItem("cart")) || [];
  const badgeEl = document.getElementById("cart-count");
  if (badgeEl) {
    badgeEl.textContent = cart.length > 0 ? cart.length : "";
  }
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
  let cart = JSON.parse(localStorage.getItem("cart")) || [];
  const existingItem = cart.find((item) => item.id === id);
  if (existingItem) {
    existingItem.qty += qty;
  } else {
    cart.push({ id, name, price, qty });
  }
  localStorage.setItem("cart", JSON.stringify(cart));
  updateCartBadge();
}

/* -------------------- Remove from Cart -------------------- */
function setupRemoveFromCartButtons() {
  document.querySelectorAll(".remove-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      let cart = JSON.parse(localStorage.getItem("cart")) || [];
      cart = cart.filter((item) => item.id !== id);
      localStorage.setItem("cart", JSON.stringify(cart));
      showToast("Item removed from cart");
      setTimeout(() => location.reload(), 500);
    });
  });
}

/* -------------------- Quantity Control (FIXED) -------------------- */
function setupQuantityButtons() {
  document.querySelectorAll(".qty-control").forEach((control) => {
    const plusBtn = control.querySelector(".plus");
    const minusBtn = control.querySelector(".minus");
    const qtyEl = control.querySelector(".qty-count");
    const maxQty = parseInt(control.dataset.maxQuantity);

    plusBtn.addEventListener("click", () => {
      let currentQty = parseInt(qtyEl.textContent);
      if (currentQty < maxQty) {
        qtyEl.textContent = currentQty + 1;
      } else {
        showToast(`Only ${maxQty} available in stock.`, true);
      }
    });

    minusBtn.addEventListener("click", () => {
      let currentQty = parseInt(qtyEl.textContent);
      if (currentQty > 1) {
        qtyEl.textContent = currentQty - 1;
      }
    });
  });
}

/* -------------------- Checkout -------------------- */
function setupCheckoutButton() {
  const btn = document.getElementById("checkout-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const cart = JSON.parse(localStorage.getItem("cart"));
    if (!cart || cart.length === 0) {
      showToast("Your cart is empty", true);
      return;
    }
    try {
      showToast("Processing your order...");
      const res = await fetch("/api/place_order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart: cart, payment_mode: "COD" }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        localStorage.removeItem("cart");
        showToast("Order placed successfully!");
        setTimeout(() => (window.location.href = "/orders"), 1500);
      } else {
        showToast(data.error || "Order failed", true);
        setTimeout(() => location.reload(), 2500);
      }
    } catch (err) {
      showToast("A network error occurred. Please try again.", true);
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
  if (!container) {
    alert(msg);
    return;
  }
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.style.background = isError ? "#b94a48" : "#a47148";
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

/* ============================================================
   CAMPUSKART — FINAL FRONTEND LOGIC
   ============================================================ */
document.addEventListener("DOMContentLoaded", () => {
  console.log("CampusKart JS loaded");
  if (!localStorage.getItem("cart")) {
    localStorage.setItem("cart", JSON.stringify([]));
  }
  updateCartBadge();
  setupAddToCartButtons();
  setupQuantityButtons();
  setupRemoveFromCartButtons();
  setupCheckoutButton();
  setupToastContainer();
  setupCancelButtons();
  setupMarkReceivedButtons();
});

function updateCartBadge() {
  const cart = JSON.parse(localStorage.getItem("cart")) || [];
  const badgeEl = document.getElementById("cart-count");
  if (badgeEl) {
    badgeEl.textContent = cart.length > 0 ? cart.length : "";
  }
}

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

// SIMPLIFIED: This function now redirects to the user's "My Orders" page.
function setupCheckoutButton() {
  const btn = document.getElementById("checkout-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const cart = JSON.parse(localStorage.getItem("cart"));
    if (!cart || cart.length === 0) {
      return showToast("Your cart is empty", true);
    }
    try {
      showToast("Processing your order...");
      const res = await fetch("/api/place_order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart: cart }),
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        localStorage.removeItem("cart"); // Clear the cart
        showToast("Order placed successfully! Redirecting...");

        // Redirect to the user's own orders page
        setTimeout(() => {
          window.location.href = "/orders";
        }, 1500); // Delay allows user to see the success message
      } else {
        showToast(data.error || "Order failed", true);
        setTimeout(() => location.reload(), 2500);
      }
    } catch (err) {
      showToast("A network error occurred. Please try again.", true);
    }
  });
}

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

function setupCancelButtons() {
  document.querySelectorAll(".btn-cancel-order").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const orderId = event.target.dataset.orderId;
      if (
        !confirm(
          "Are you sure you want to cancel this order? The item will be restocked."
        )
      ) {
        return;
      }
      try {
        const response = await fetch(`/orders/cancel/${orderId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();
        if (response.ok && data.ok) {
          showToast("Order cancelled successfully.");
          setTimeout(() => location.reload(), 1500);
        } else {
          showToast(data.error || "Failed to cancel order.", true);
        }
      } catch (error) {
        showToast("A network error occurred. Please try again.", true);
      }
    });
  });
}

function setupMarkReceivedButtons() {
  document.querySelectorAll(".btn-mark-received").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const orderId = event.target.dataset.orderId;
      if (
        !confirm(
          "Confirm that you have received this item? This will complete the order."
        )
      ) {
        return;
      }
      try {
        const response = await fetch(`/orders/mark_received/${orderId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();
        if (response.ok && data.ok) {
          showToast("Order completed!");
          setTimeout(() => location.reload(), 1500);
        } else {
          showToast(data.error || "Failed to update order.", true);
        }
      } catch (error) {
        showToast("A network error occurred. Please try again.", true);
      }
    });
  });
}

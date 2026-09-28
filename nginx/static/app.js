const state = {
  token: localStorage.getItem("shopverse_token"),
  products: [],
  selected: null,
  register: false,
};

const $ = (id) => document.getElementById(id);

function showNotice(message) {
  $("notice").textContent = message;
  $("notice").classList.remove("hidden");
  setTimeout(() => $("notice").classList.add("hidden"), 5000);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong. Please try again.");
  return body;
}

function money(value) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(value);
}

async function loadProducts() {
  const container = $("products");
  container.innerHTML = "<p>Loading products…</p>";
  try {
    state.products = await api("/api/v1/products/");
    container.innerHTML = "";
    $("products-empty").classList.toggle("hidden", state.products.length !== 0);
    for (const product of state.products) {
      const card = document.createElement("article");
      card.className = "product-card";
      card.innerHTML = `
        <p class="eyebrow">${product.category}</p>
        <h2>${product.name}</h2>
        <p>${product.description}</p>
        <p class="price">${money(product.price)}</p>
        <button class="button">Reserve item</button>`;
      card.querySelector("button").addEventListener("click", () => openCheckout(product));
      container.appendChild(card);
    }
  } catch (error) {
    container.innerHTML = `<p class="error">${error.message}</p>`;
  }
}

function openCheckout(product) {
  if (!state.token) {
    showNotice("Sign in before placing an order.");
    $("auth-dialog").showModal();
    return;
  }
  state.selected = product;
  $("checkout-product").textContent = `${product.name} · ${money(product.price)}`;
  $("checkout-dialog").showModal();
}

async function loadOrders() {
  if (!state.token) {
    $("orders").innerHTML = "";
    $("orders-empty").textContent = "Sign in to see your orders.";
    $("orders-empty").classList.remove("hidden");
    return;
  }
  $("orders").innerHTML = "<p>Loading orders…</p>";
  try {
    const orders = await api("/api/v1/orders/");
    $("orders").innerHTML = "";
    $("orders-empty").textContent = "You have no orders yet.";
    $("orders-empty").classList.toggle("hidden", orders.length !== 0);
    for (const order of orders) {
      const card = document.createElement("article");
      card.className = "order-card";
      const stateLabel = order.reservation_state || "pending";
      card.innerHTML = `
        <div>
          <span class="status ${stateLabel}">${stateLabel}</span>
          <h2>${order.items.length} item${order.items.length === 1 ? "" : "s"}</h2>
          <p>${money(order.total_price)} · Order ${order._id}</p>
        </div>
        ${["pending", "reserved"].includes(stateLabel) ? '<button class="button secondary">Cancel</button>' : ""}`;
      const cancel = card.querySelector("button");
      if (cancel) cancel.addEventListener("click", () => cancelOrder(order._id));
      $("orders").appendChild(card);
    }
  } catch (error) {
    $("orders").innerHTML = `<p class="error">${error.message}</p>`;
  }
}

async function cancelOrder(orderId) {
  try {
    await api(`/api/v1/orders/${orderId}`, { method: "DELETE" });
    showNotice("Your order was cancelled. Stock release is being processed.");
    await loadOrders();
  } catch (error) {
    showNotice(error.message);
  }
}

$("checkout-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const product = state.selected;
  const idempotencyKey = crypto.randomUUID();
  try {
    const order = await api("/api/v1/orders/", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        items: [{ product_id: product._id, quantity: 1, price: product.price }],
        shipping_address: {
          line1: $("line1").value,
          city: $("city").value,
          state: $("state").value,
          postal_code: $("postal-code").value,
          country: $("country").value,
        },
      }),
    });
    $("checkout-dialog").close();
    event.target.reset();
    showNotice(`Order ${order._id} is pending. We are reserving your stock now.`);
    switchView("orders");
  } catch (error) {
    $("checkout-error").textContent = error.message;
    $("checkout-error").classList.remove("hidden");
  }
});

function setAuthMode(register) {
  state.register = register;
  $("auth-title").textContent = register ? "Create an account" : "Sign in";
  $("auth-submit").textContent = register ? "Create account" : "Sign in";
  $("auth-switch").textContent = register ? "I already have an account" : "Create an account";
  $("register-fields").classList.toggle("hidden", !register);
  $("first-name").required = register;
  $("last-name").required = register;
}

$("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("auth-error").classList.add("hidden");
  try {
    if (state.register) {
      await api("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: $("email").value,
          password: $("password").value,
          first_name: $("first-name").value,
          last_name: $("last-name").value,
        }),
      });
    }
    const body = new URLSearchParams({
      username: $("email").value,
      password: $("password").value,
    });
    const tokens = await api("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    state.token = tokens.access_token;
    localStorage.setItem("shopverse_token", state.token);
    $("auth-dialog").close();
    event.target.reset();
    updateAuthButton();
    showNotice("You are signed in.");
  } catch (error) {
    $("auth-error").textContent = error.message;
    $("auth-error").classList.remove("hidden");
  }
});

function updateAuthButton() {
  $("auth-button").textContent = state.token ? "Sign out" : "Sign in";
}

function switchView(view) {
  $("catalog-view").classList.toggle("hidden", view !== "catalog");
  $("orders-view").classList.toggle("hidden", view !== "orders");
  $("catalog-tab").classList.toggle("active", view === "catalog");
  $("orders-tab").classList.toggle("active", view === "orders");
  if (view === "orders") loadOrders();
}

$("catalog-tab").addEventListener("click", () => switchView("catalog"));
$("orders-tab").addEventListener("click", () => switchView("orders"));
$("refresh-orders").addEventListener("click", loadOrders);
$("auth-button").addEventListener("click", () => {
  if (state.token) {
    state.token = null;
    localStorage.removeItem("shopverse_token");
    updateAuthButton();
    switchView("catalog");
    showNotice("You are signed out.");
  } else {
    setAuthMode(false);
    $("auth-dialog").showModal();
  }
});
$("auth-switch").addEventListener("click", () => setAuthMode(!state.register));
document.querySelectorAll(".close").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

updateAuthButton();
loadProducts();

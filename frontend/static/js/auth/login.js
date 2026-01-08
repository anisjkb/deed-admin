// frontend/static/js/auth/login.js
document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const form = e.target;

  // UI elements
  const errorEl = document.getElementById("errorMsg");
  const btn = form.querySelector("button[type='submit']"); // define ONCE so catch/finally can use it

  // Reset messages
  if (errorEl) errorEl.textContent = "";
  ["logInIdError", "passwordError"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = "";
  });

  const logInId = form.querySelector("#logInId")?.value.trim();
  const password = form.querySelector("#password")?.value.trim();

  if (!logInId) {
    document.getElementById("logInIdError").textContent = "Login ID is required.";
    form.querySelector("#logInId")?.focus();
    return;
  }

  if (!password) {
    document.getElementById("passwordError").textContent = "Password is required.";
    form.querySelector("#password")?.focus();
    return;
  }

  // Disable button + show loading
  if (btn) {
    btn.disabled = true;
    btn.dataset.prevText = btn.textContent || "Log In";
    btn.textContent = "logging in...";
  }

  try {
    const data = new FormData(form);

    // CSRF token
    const csrfCookie = document.cookie
      .split("; ")
      .find((c) => c.startsWith("XSRF-TOKEN="));
    const csrfToken = csrfCookie ? csrfCookie.split("=")[1] : null;

    const res = await fetch("/auth/login", {
      method: "POST",
      body: data,
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
      credentials: "include",
    });

    // Parse response safely (maybe JSON, maybe not)
    let out = {};
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      out = await res.json().catch(() => ({}));
    } else {
      const text = await res.text().catch(() => "");
      out = { message: text };
    }

    if (res.ok) {
      if (out.access_token) Auth.setAccessToken(out.access_token);
      window.location.href = "/admin/master";
      return;
    }

    // Prefer backend detail (FastAPI) then message (your handler) then fallback
    const backendMsg =
      out.detail ||
      out.message ||
      `Login failed (HTTP ${res.status}). Please try again.`;

    console.error("Login failed:", res.status, out);

    if (errorEl) {
      errorEl.textContent = backendMsg;
    }
  } catch (networkErr) {
    console.error("Network error:", networkErr);
    if (errorEl) errorEl.textContent = "Network error, please try again.";
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.prevText || "Log In";
    }
  }
});
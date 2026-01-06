// frontend/static/js/auth/login.js
document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const form = e.target;
  const errorEl = document.getElementById("errorMsg");

  if (errorEl) errorEl.textContent = "";

  // Clear previous inline errors
  ["logInIdError", "passwordError"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = "";
  });

  const logInIdInput = form.querySelector("#logInId");
  const passwordInput = form.querySelector("#password");

  const logInId = (logInIdInput?.value || "").trim();
  const password = (passwordInput?.value || "").trim();

  if (!logInId) {
    document.getElementById("logInIdError").textContent = "Login ID is required.";
    logInIdInput?.focus();
    return;
  }

  if (!password) {
    document.getElementById("passwordError").textContent = "Password is required.";
    passwordInput?.focus();
    return;
  }

  // ✅ define btn outside try so catch/finally can use it
  const btn = form.querySelector("button[type='submit']");

  const setBtnLoading = (loading) => {
    if (!btn) return;
    if (loading) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent || "";
      btn.textContent = "logging in...";
    } else {
      btn.disabled = false;
      btn.textContent = btn.dataset.prevText || "Log In";
    }
  };

  try {
    setBtnLoading(true);

    const data = new FormData(form);

    // CSRF token from cookie (if present)
    const csrfCookie = document.cookie.split("; ").find((c) => c.startsWith("XSRF-TOKEN="));
    const csrfToken = csrfCookie ? decodeURIComponent(csrfCookie.split("=")[1]) : null;

    const res = await fetch("/auth/login", {
      method: "POST",
      body: data,
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
      credentials: "include",
    });

    // Try to parse JSON response
    const out = await res.json().catch(() => ({}));

    if (res.ok) {
      // Save access token (if your token.js provides Auth)
      if (out.access_token && window.Auth?.setAccessToken) {
        window.Auth.setAccessToken(out.access_token);
      }
      window.location.href = "/admin/master";
      return;
    }

    // Show backend error (your backend returns detail)
    console.error("Login failed:", res.status, out);
    if (errorEl) {
      errorEl.textContent = out.detail || out.message || "Invalid login ID or password.";
    }

  } catch (networkErr) {
    console.error("Network error:", networkErr);
    if (errorEl) errorEl.textContent = "Network error, please try again.";
  } finally {
    setBtnLoading(false);
  }
});
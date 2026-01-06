//frontend/static/js/auth/login.js
document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const form = e.target;
  const err = document.getElementById("errorMsg");
  if (err) err.textContent = "";

  // Clear previous inline errors
  ["logInIdError", "passwordError"].forEach(id => {
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

  // Submit login
  try {
    const data = new FormData(form);
    // Improved CSRF token handling
    const csrf = document.cookie.split("; ").find(c => c.startsWith("XSRF-TOKEN="));
    const csrfToken = csrf ? csrf.split("=")[1] : null;

    const btn = form.querySelector("button[type='submit']"); // Define the submit button

    if (btn) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent || "";
      btn.textContent = "logging in...";
    }

    const res = await fetch("/auth/login", {
      method: "POST",
      body: data,
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
      credentials: "include",
    });

    // Get the response object from the backend
    const out = await res.json().catch((err) => {
      console.error("Error parsing response:", err);
      return {};
    });

    // Check for successful login
    if (res.ok) {
      if (out.access_token) Auth.setAccessToken(out.access_token);
      window.location.href = "/admin/master"; // Redirect to admin master page
      return;
    }

    // Show backend error (your backend returns detail)
    console.error("Login failed:", res.status, out);
    if (err) {
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.dataset.prevText || "Log In";
      }
      err.textContent = out.detail || out.message || "Invalid login ID or password."; // Ensure error message is displayed
    }

  } catch (err) {
    const btn = form.querySelector("button[type='submit']"); // Define the submit button
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.prevText || "Log In";
    }
    console.error("Network error:", err); // Add error logging
    if (err) err.textContent = "Network error, please try again";
  } finally {
    const btn = form.querySelector("button[type='submit']"); // Define the submit button
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.prevText || "Log In";
    }
  }
});
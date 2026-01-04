// frontend/static/js/auth/forgot_password.js
(function () {
  const form = document.getElementById("forgotPasswordForm");
  if (!form) return;

  const loginIdEl = document.getElementById("login_id");
  const emailEl   = document.getElementById("email");
  const errEl     = document.getElementById("errorMsg");
  const loginErr  = document.getElementById("login_idError");
  const emailErr  = document.getElementById("emailError");
  const btn       = document.getElementById("forgotPasswordBtn");

  const setText = (el, t) => { if (el) el.textContent = t || ""; };
  const clearErrors = () => { setText(errEl, ""); setText(loginErr, ""); setText(emailErr, ""); };

  function getCookie(name) {
    if (window.CSRF?.getCookie) return window.CSRF.getCookie(name);
    const parts = document.cookie ? document.cookie.split("; ") : [];
    for (const part of parts) {
      const idx = part.indexOf("=");
      const k = idx === -1 ? part : part.slice(0, idx);
      if (k === name) return decodeURIComponent(idx === -1 ? "" : part.slice(idx + 1));
    }
    return "";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault(); // enhance with fetch; form still has proper action/method as fallback
    clearErrors();

    const login_id = (loginIdEl?.value || "").trim();
    const email    = (emailEl?.value || "").trim();

    if (!login_id) { setText(loginErr, "Login id is required."); loginIdEl?.focus(); return; }
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) { setText(emailErr, "Email is required."); emailEl?.focus(); return; }
    if (!emailPattern.test(email)) { setText(emailErr, "Please enter a valid email address."); emailEl?.focus(); return; }

    const csrf = getCookie("XSRF-TOKEN");

    if (btn) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent || "";
      btn.textContent = "Sending…";
    }

    try {
      const res = await fetch("/auth/link-forgot-password", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {})
        },
        body: JSON.stringify({ login_id, email })
      });

      if (!res.ok) {
        // try to read structured error
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = await res.json();
          if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
          if (Array.isArray(j?.detail)) {
            for (const d of j.detail) {
              const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
              if (field === "login_id") setText(loginErr, d.msg);
              if (field === "email") setText(emailErr, d.msg);
            }
          }
        } catch {}
        setText(errEl, msg);
        if (window.Toast) Toast.error(msg, { title: "Request Failed" });
        return;
      }

      const out = await res.json().catch(() => ({}));
      const successMsg = out.message || "Password reset link sent to your email.";
      if (window.Toast) Toast.success(successMsg, { title: "Email Sent" });
      form.reset();

      // Redirect to login after a beat for consistent UX
      setTimeout(() => { window.location.href = "/login"; }, 1200);

    } catch (err) {
      const msg = err?.message || "Network error: could not reach server.";
      setText(errEl, msg);
      if (window.Toast) Toast.error(msg, { title: "Network Error" });
      console.error(err);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.dataset.prevText || "Send Reset Link";
      }
    }
  });
})();
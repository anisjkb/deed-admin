// frontend/static/js/auth/reset_password.js
(function () {
  const form = document.getElementById("resetPasswordForm");
  if (!form) return;

  const passwordEl = document.getElementById("password");
  const confirmEl  = document.getElementById("confirmPassword");
  const codeEl     = document.getElementById("reset_code");

  const errEl      = document.getElementById("errorMsg");
  const passErrEl  = document.getElementById("passwordError");
  const confErrEl  = document.getElementById("confirmPasswordError");
  const btn        = document.getElementById("resetPasswordBtn");

  const setText = (el, t) => { if (el) el.textContent = t || ""; };
  const clearErrors = () => { setText(errEl, ""); setText(passErrEl, ""); setText(confErrEl, ""); };

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
    e.preventDefault(); // enhance with fetch (backend expects JSON model)
    clearErrors();

    const password = (passwordEl?.value || "").trim();
    const confirm  = (confirmEl?.value || "").trim();
    const reset_code = (codeEl?.value || "").trim();

    if (!password) { setText(passErrEl, "New password is required."); passwordEl?.focus(); return; }
    if (password.length < 4) { setText(passErrEl, "Use at least 4 characters."); passwordEl?.focus(); return; }
    if (!confirm) { setText(confErrEl, "Please confirm your new password."); confirmEl?.focus(); return; }
    if (password !== confirm) { setText(confErrEl, "Passwords do not match."); confirmEl?.focus(); return; }
    if (!reset_code) { setText(errEl, "Reset token is missing."); return; }

    const csrf = getCookie("XSRF-TOKEN");

    if (btn) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent || "";
      btn.textContent = "Resetting…";
    }

    try {
      const res = await fetch("/auth/reset-password", { 
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {})
        },
        body: JSON.stringify({ reset_code, password })
      });

      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = await res.json();
          if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
        } catch {}
        setText(errEl, msg);
        if (window.Toast) Toast.error(msg, { title: "Reset Failed" });
        return;
      }

      const out = await res.json().catch(() => ({}));
      const successMsg = out.message || "Password reset successful.";
      if (window.Toast) Toast.success(successMsg, { title: "Done" });

      // Clear and redirect to login
      form.reset();
      setTimeout(() => { window.location.href = "/login"; }, 1000);

    } catch (error) {
      const msg = error?.message || "Network error: could not reach server.";
      setText(errEl, msg);
      if (window.Toast) Toast.error(msg, { title: "Network Error" });
      console.error(error);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.dataset.prevText || "Reset Password";
      }
    }
  });
})();
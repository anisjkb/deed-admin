// frontend/static/js/auth/register.js
(function () {
  const form = document.getElementById("registerForm");
  if (!form) return;

  const btn  = document.getElementById("registerBtn");
  const err  = document.getElementById("errorMsg");

  const empIdEl   = document.getElementById("emp_id");
  const loginIdEl = document.getElementById("login_id");
  const roleIdEl  = document.getElementById("role_id");
  const emailEl   = document.getElementById("email");
  const passEl    = document.getElementById("password");
  const confEl    = document.getElementById("confirmPassword");

  const empErr  = document.getElementById("empIdError");
  const logErr  = document.getElementById("loginIdError");
  const roleErr = document.getElementById("roleIdError");
  const mailErr = document.getElementById("emailError");
  const pwdErr  = document.getElementById("passwordError");
  const cfmErr  = document.getElementById("confirmError");

  const setText = (el, t) => { if (el) el.textContent = t || ""; };
  const clearAll = () => {
    [empErr, logErr, roleErr, mailErr, pwdErr, cfmErr].forEach(e => setText(e, ""));
    setText(err, "");
  };

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
    e.preventDefault();
    clearAll();

    // simple client-side checks
    const emp  = (empIdEl?.value || "").trim();
    const log  = (loginIdEl?.value || "").trim();
    const role = (roleIdEl?.value || "").trim();
    const mail = (emailEl?.value || "").trim();
    const pwd  = (passEl?.value || "").trim();
    const cfm  = (confEl?.value || "").trim();

    let bad = false;
    if (!emp) { setText(empErr, "Employee ID is required."); bad = true; }
    if (!log) { setText(logErr, "Login ID is required."); bad = true; }
    if (!role) { setText(roleErr, "Role ID is required."); bad = true; }
    if (!mail) { setText(mailErr, "Email is required."); bad = true; }
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) { setText(mailErr, "Enter a valid email."); bad = true; }
    if (!pwd) { setText(pwdErr, "Password is required."); bad = true; }
    else if (pwd.length < 4) { setText(pwdErr, "Use at least 4 characters."); bad = true; }
    if (!cfm) { setText(cfmErr, "Confirm your password."); bad = true; }
    else if (cfm !== pwd) { setText(cfmErr, "Passwords do not match."); bad = true; }

    if (bad) return;

    const csrf = getCookie("XSRF-TOKEN");
    const fd = new FormData(form); // includes hidden csrf_token already

    if (btn) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent || "";
      btn.textContent = "Registering…";
    }

    try {
      const res = await fetch("/auth/register", {
        method: "POST",
        credentials: "include",
        // IMPORTANT: don't set Content-Type when sending FormData
        headers: { ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
        body: fd
      });

      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = await res.json();
          if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
        } catch {}
        setText(err, msg);
        if (window.Toast) Toast.error(msg, { title: "Registration failed" });
        return;
      }

      // registration_response likely sets cookies / redirects; if JSON, handle:
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const data = await res.json().catch(() => ({}));
        if (window.Toast) Toast.success("Registration successful", { title: "Welcome" });
        // If your backend returns next URL, use it. Otherwise go login.
        setTimeout(() => { window.location.href = "/login"; }, 800);
      } else {
        // If server responded with a redirect, follow it by letting location change
        window.location.href = "/login";
      }
    } catch (ex) {
      const msg = ex?.message || "Network error.";
      setText(err, msg);
      if (window.Toast) Toast.error(msg, { title: "Network Error" });
      console.error(ex);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.dataset.prevText || "Register";
      }
    }
  });
})();
// frontend/static/js/admin/security/change_password.js
(function () {
  const form = document.getElementById("changePasswordForm");
  if (!form) return;

  const oldPasswordEl = document.getElementById("oldPassword");
  const newPasswordEl = document.getElementById("newPassword");
  const errEl = document.getElementById("passwordError");
  const btn = document.getElementById("changePasswordBtn");

  const setText = (el, t) => { if (el) el.textContent = t || ""; };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setText(errEl, "");  // Clear previous error messages

    const oldPassword = oldPasswordEl.value.trim();
    const newPassword = newPasswordEl.value.trim();

    if (!oldPassword) { setText(errEl, "Old password is required."); return; }
    if (!newPassword) { setText(errEl, "New password is required."); return; }

    const csrf = getCookie("XSRF-TOKEN");

    if (btn) {
      btn.disabled = true;
      btn.textContent = "Changing...";
    }

    try {
      const res = await fetch("/auth/change-password", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });

      if (!res.ok) {
        let msg = `${res.status} ${res.statusText}`;
        try {
          const j = await res.json();
          if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
        } catch {}
        setText(errEl, msg);
        return;
      }

      const out = await res.json();
      const successMsg = out.message || "Password changed successfully.";
      alert(successMsg);  // Show success message

      // Refresh the page to reset the form
      location.reload();

    } catch (error) {
      setText(errEl, error?.message || "Network error: could not reach server.");
      console.error(error);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Change Password";
      }
    }
  });

  function getCookie(name) {
    const parts = document.cookie ? document.cookie.split("; ") : [];
    for (const part of parts) {
      const idx = part.indexOf("=");
      const k = idx === -1 ? part : part.slice(0, idx);
      if (k === name) return decodeURIComponent(idx === -1 ? "" : part.slice(idx + 1));
    }
    return "";
  }
})();
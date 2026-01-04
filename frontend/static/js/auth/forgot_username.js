// Requires toast.js globally loaded
(function () {
  const form = document.getElementById("forgotUsernameForm");
  if (!form) return;

  const emailEl = document.getElementById("email");
  const errEl = document.getElementById("errorMsg");
  const successEl = document.getElementById("successMsg");
  const emailErrorEl = document.getElementById("emailError");
  const btn = document.getElementById("submitBtn");

  const setText = (el, text) => { if (el) el.textContent = text || ""; };
  const clearErrors = () => { setText(errEl, ""); setText(successEl, ""); setText(emailErrorEl, ""); };

  async function parseErrorResponse(res) {
    let raw = "";
    try { raw = await res.text(); } catch {}
    if (!raw) return { message: `${res.status} ${res.statusText}` };
    try {
      const json = JSON.parse(raw);
      if (typeof json.detail === "string") return { message: json.detail };
      if (Array.isArray(json.detail)) {
        const fields = {}; const msgs = [];
        for (const d of json.detail) {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
          if (field) fields[field] = d.msg;
          msgs.push(d.msg);
        }
        return { message: msgs.join(" | "), fields };
      }
      if (json.message) return { message: json.message };
      return { message: raw };
    } catch { return { message: raw }; }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors();

    const email = emailEl?.value.trim();
    if (!email) {
      setText(emailErrorEl, "Email is required.");
      emailEl?.focus();
      return;
    }
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(email)) {
      setText(emailErrorEl, "Please enter a valid email address.");
      emailEl?.focus();
      return;
    }

    const csrf = (window.Auth && typeof Auth.getCookie === "function")
      ? Auth.getCookie("XSRF-TOKEN")
      : null;

    if (btn) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent || "";
      btn.textContent = "Sending...";
    }

    try {
      const res = await fetch("/auth/forgot-username", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {})
        },
        body: JSON.stringify({ email })
      });

      if (!res.ok) {
        const { message, fields } = await parseErrorResponse(res);
        if (fields?.email) setText(emailErrorEl, fields.email);
        setText(errEl, message);
        //if (window.Toast) Toast.error(message, { title: "Request Failed" });
        //console.error("Forgot login id error:", message);
        return;
      }

      const out = await res.json().catch(() => ({}));
      const successMsg = out.message || "Your login id has been sent to your email.";
      //setText(successEl, successMsg);
      if (window.Toast) Toast.success(successMsg, { title: "Email Sent" });
      errEl.value = "";
      emailEl.value = "";
      setTimeout(() => { window.location.href = "/login"; }, 1500);

    } catch (error) {
      const msg = error?.message || "Network error: could not reach server.";
      setText(errEl, msg);
      if (window.Toast) Toast.error(msg, { title: "Network Error" });
      console.error("Network failure:", error);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = btn.dataset.prevText || "Send login id";
      }
    }
  });
})();
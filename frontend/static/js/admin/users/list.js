// frontend/static/js/admin/users/list.js

(function () {
  function getCookie(name) {
    const v = `; ${document.cookie}`;
    const parts = v.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  async function apiDeleteUser(loginId) {
    const xsrf = getCookie("XSRF-TOKEN");
    const res = await fetch(`/api/users/${encodeURIComponent(loginId)}`, {
      method: "DELETE",
      headers: {
        "X-XSRF-TOKEN": xsrf || "",
        "Accept": "application/json",
      },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Delete failed (${res.status})`);
    }
    return res.json();
  }

  function handleDeleteClicks() {
    document.addEventListener("click", async (e) => {
      const btn = e.target.closest(".js-user-delete");
      if (!btn) return;
      e.preventDefault();
      const loginId = btn.getAttribute("data-login");
      if (!loginId) return;

      if (!confirm(`Delete user "${loginId}"? This cannot be undone.`)) return;

      btn.disabled = true;
      try {
        await apiDeleteUser(loginId);
        // remove row
        const tr = document.querySelector(`tr[data-login="${CSS.escape(loginId)}"]`);
        if (tr) tr.remove();
      } catch (err) {
        alert(err.message || "Failed to delete user.");
      } finally {
        btn.disabled = false;
      }
    });
  }

  handleDeleteClicks();
})();

// frontend/static/js/admin/ops/feedback_badge.js
// Handles unread badge click → AJAX mark-as-read

document.addEventListener("DOMContentLoaded", () => {

  function getCsrfToken() {
    const c = document.cookie.split("; ").find(v => v.startsWith("XSRF-TOKEN="));
    return c ? c.split("=")[1] : "";
  }

  document.querySelectorAll(".badge-unread").forEach(badge => {
    badge.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const id = badge.dataset.id;
      if (!id) return;

      try {
        const res = await fetch(`/admin/api/feedback/${id}/mark-read`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": getCsrfToken(),
          },
          credentials: "include",
        });

        if (!res.ok) {
          console.warn("Failed to mark feedback as read:", await res.text());
          return;
        }

        // UI update
        const row = badge.closest("tr");
        if (row) row.classList.remove("unread-row");
        badge.remove();

      } catch (err) {
        console.error("Error marking feedback as read:", err);
      }
    });
  });

});
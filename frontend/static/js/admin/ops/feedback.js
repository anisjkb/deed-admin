// frontend/static/js/admin/ops/feedback.js
(function () {
  // Simple “are you sure?” for delete forms (class: delete-confirm)
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("form.delete-confirm button[type=submit]");
    if (!btn) return;

    const form = btn.closest("form.delete-confirm");
    const msg = form?.dataset?.message || "Delete this item?";
    if (!confirm(msg)) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);

  // Optional: autofocus first input on create/edit pages
  const first = document.querySelector("form.form-card input[name=name]");
  if (first) first.focus();
})();
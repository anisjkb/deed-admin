// frontend/static/js/admin/org/desig_info.js
(function () {
  const idInput = document.querySelector('input[name="desig_id"]');
  const btn = document.getElementById('regenDesigId');
  if (!idInput) return;

  async function fetchNext() {
    try {
      const res = await fetch('/admin/designations/next-id', { credentials: 'include' });
      if (!res.ok) return;
      const data = await res.json();
      idInput.value = data.next_id || '';
    } catch (_) {}
  }

  if (!idInput.value) fetchNext();
  btn?.addEventListener('click', fetchNext);
})();

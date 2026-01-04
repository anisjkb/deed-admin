// frontend/static/js/admin/users/form.js

(function () {
  const empSelect = document.getElementById("empSelect");
  const loginIdInput = document.getElementById("loginIdInput");
  const nameDisp = document.getElementById("empNameDisplay");
  const emailDisp = document.getElementById("empEmailDisplay");

  // Load first 50 employees (or filterable later if you add a live search input)
  async function loadEmployees(q = "") {
    try {
      const url = q ? `/admin/users/options/employees?q=${encodeURIComponent(q)}` : `/admin/users/options/employees`;
      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) return;
      const items = await res.json();
      empSelect.innerHTML = '<option value="">-- Select Employee --</option>';
      for (const r of items) {
        const opt = document.createElement("option");
        opt.value = r.emp_id;
        opt.textContent = `${r.emp_id} — ${r.emp_name}`;
        opt.dataset.name = r.emp_name || "";
        opt.dataset.email = r.email || "";
        empSelect.appendChild(opt);
      }
    } catch (_) {}
  }

  function populateFromSelection() {
    const opt = empSelect.options[empSelect.selectedIndex];
    if (!opt || !opt.value) {
      nameDisp.value = "";
      emailDisp.value = "";
      return;
    }
    // Default login_id to emp_id WHEN user hasn't typed anything yet or matches old value
    if (!loginIdInput.value || loginIdInput.value === "" || loginIdInput.value === loginIdInput.dataset.autoFrom) {
      loginIdInput.value = opt.value;
      loginIdInput.dataset.autoFrom = opt.value; // remember last auto-fill
    }
    nameDisp.value = opt.dataset.name || "";
    emailDisp.value = opt.dataset.email || "";
  }

  empSelect.addEventListener("change", populateFromSelection);
  loadEmployees().then(() => {
    // If form had an initial employee (unlikely on create), select it:
    const initialEmp = "{{ form.emp_id or '' }}";
    if (initialEmp) {
      for (const opt of empSelect.options) {
        if (opt.value === initialEmp) { opt.selected = true; break; }
      }
      populateFromSelection();
    }
  });
})();
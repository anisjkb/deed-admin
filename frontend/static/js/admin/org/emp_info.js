// frontend/static/js/admin/org/emp_info.js
(function () {
  // --- Elements ---
  const groupSel  = document.getElementById('groupSelect');
  const orgSel    = document.getElementById('orgSelect');
  const zoneSel   = document.getElementById('zoneSelect');
  const branchSel = document.getElementById('branchSelect');
  const desigSel  = document.getElementById('desigSelect');

  // --- Helpers ---
  async function fetchJSON(url) {
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return null;
    try { return await res.json(); } catch { return null; }
  }

  function clearOptions(sel, placeholder) {
    if (!sel) return;
    sel.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = placeholder || '-- Select --';
    sel.appendChild(opt);
  }

  function fillOptions(sel, items, valueKey, labelKey, selectedValue) {
    if (!sel || !items) return;
    for (const it of items) {
      const opt = document.createElement('option');
      opt.value = it[valueKey];
      opt.textContent = `${it[labelKey]} - ${it[valueKey]}`;
      if (selectedValue && selectedValue === it[valueKey]) opt.selected = true;
      sel.appendChild(opt);
    }
  }

  // --- Cascading dropdowns ---
  async function onGroupChange() {
    const gid = groupSel?.value || '';
    clearOptions(orgSel, '-- Select Organization --');
    clearOptions(zoneSel, '-- Select Zone --');
    clearOptions(branchSel, '-- Select Branch --');
    if (!gid) return;
    const items = await fetchJSON(`/admin/employees/options/orgs?group_id=${encodeURIComponent(gid)}`);
    fillOptions(orgSel, items || [], 'org_id', 'org_name');
  }

  async function onOrgChange() {
    const oid = orgSel?.value || '';
    clearOptions(zoneSel, '-- Select Zone --');
    clearOptions(branchSel, '-- Select Branch --');
    if (!oid) return;
    const items = await fetchJSON(`/admin/employees/options/zones?org_id=${encodeURIComponent(oid)}`);
    fillOptions(zoneSel, items || [], 'zone_id', 'zone_name');
  }

  async function onZoneChange() {
    const zid = zoneSel?.value || '';
    clearOptions(branchSel, '-- Select Branch --');
    if (!zid) return;
    const items = await fetchJSON(`/admin/employees/options/branches?zone_id=${encodeURIComponent(zid)}`);
    fillOptions(branchSel, items || [], 'br_id', 'br_name');
  }

  async function loadDesignationsIfEmpty() {
    if (!desigSel || desigSel.options.length > 1) return;
    const items = await fetchJSON('/admin/employees/options/designations');
    clearOptions(desigSel, '-- Select Designation --');
    fillOptions(desigSel, items || [], 'desig_id', 'desig_name');
  }

  // Attach events
  groupSel?.addEventListener('change', onGroupChange);
  orgSel?.addEventListener('change', onOrgChange);
  zoneSel?.addEventListener('change', onZoneChange);

  // Initialize designations if needed
  loadDesignationsIfEmpty();
})();
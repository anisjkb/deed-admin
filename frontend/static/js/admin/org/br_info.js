/* frontend/static/js/admin/org/js/br_info.js */

(function () {
  const sel = document.getElementById("zoneSelect");
  const input = document.querySelector('input[name="br_id"]');
  if (!sel || !input) return;

  async function fillBranchId() {
    const zid = sel.value || "";
    if (!zid) { input.value = ""; return; }
    try {
      const res = await fetch(`/admin/branches/next-id?zone_id=${encodeURIComponent(zid)}`, { credentials: "include" });
      if (!res.ok) return;
      const data = await res.json();
      input.value = data.next_id || "";
    } catch (_) { /* no-op */ }
  }

  sel.addEventListener("change", fillBranchId);
  if (!input.value) fillBranchId();
})();
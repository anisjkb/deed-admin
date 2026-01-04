(function () {
  const sel = document.getElementById("orgSelect");
  const input = document.querySelector('input[name="zone_id"]');
  if (!sel || !input) return;

  async function fillZoneId() {
    const oid = sel.value || "";
    if (!oid) { input.value = ""; return; }
    try {
      const res = await fetch(`/admin/zones/next-id?org_id=${encodeURIComponent(oid)}`, { credentials: "include" });
      if (!res.ok) return;
      const data = await res.json();
      input.value = data.next_id || "";
    } catch (_) { /* no-op */ }
  }

  sel.addEventListener("change", fillZoneId);
  if (!input.value) fillZoneId();
})();

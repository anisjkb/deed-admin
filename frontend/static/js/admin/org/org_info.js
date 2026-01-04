(function () {
  const sel = document.getElementById("groupSelect");
  const input = document.querySelector('input[name="org_id"]');
  if (!sel || !input) return;

  async function fillOrgId() {
    const gid = sel.value || "";
    if (!gid) { input.value = ""; return; }
    try {
      const res = await fetch(`/admin/orgs/next-id?group_id=${encodeURIComponent(gid)}`, { credentials: "include" });
      if (!res.ok) return;
      const data = await res.json();
      input.value = data.next_id || "";
    } catch (_) { /* no-op */ }
  }

  sel.addEventListener("change", fillOrgId);
  if (!input.value) fillOrgId();
})();

(function () {
  const btn = document.getElementById("regenGroupId");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    try {
      const res = await fetch("/admin/groups/next-id", { credentials: "include" });
      if (!res.ok) return;
      const data = await res.json();
      const input = document.querySelector('input[name="group_id"]');
      if (input) input.value = data.next_id || "";
    } catch (_) { /* no-op */ }
  });
})();
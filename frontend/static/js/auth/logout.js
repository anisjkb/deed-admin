// frontend/static/js/auth/logout.js
document.getElementById("logoutBtn")?.addEventListener("click", async () => {
  try {
    const csrf = Auth.getCookie("XSRF-TOKEN");
    await fetch("/auth/logout", {
      method: "POST",
      headers: csrf ? { "X-CSRF-Token": csrf } : {},
      credentials: "include",
    });
  } catch (_) {}
  Auth.clearAccessToken();
  window.location.href = "/";
});
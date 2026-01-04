// frontend/static/js/menu-toggle.js
(function () {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.getElementById("main-nav");
  if (!toggle || !nav) return;

  const doToggle = () => nav.classList.toggle("show");
  toggle.addEventListener("click", doToggle);
  toggle.addEventListener("keypress", (e) => { if (e.key === "Enter") doToggle(); });
})();
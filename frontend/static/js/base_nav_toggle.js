// frontend/static/js/base_nav_toggle.js
(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector(".menu-toggle");
    const nav = document.querySelector("nav ul");
    if (!toggle || !nav) return;

    function doToggle() {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", (!expanded).toString());
      nav.classList.toggle("show");
    }

    toggle.addEventListener("click", doToggle);
    toggle.addEventListener("keypress", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        doToggle();
      }
    });
  });
})();
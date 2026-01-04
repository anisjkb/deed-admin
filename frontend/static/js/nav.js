// ---------------------------
  // nav.js
  //
  // JavaScript code for the navigation menu.
  // ---------------------------
(function () {
  "use strict";

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const throttle = (fn, wait = 150) => {
    let last = 0, t;
    return (...args) => {
      const now = Date.now();
      if (now - last >= wait) {
        last = now; fn(...args);
      } else {
        clearTimeout(t);
        t = setTimeout(() => { last = Date.now(); fn(...args); }, wait - (now - last));
      }
    };
  };

  document.addEventListener("DOMContentLoaded", () => {
    const toggle   = qs(".nav-toggle");
    const menu     = qs("#nav-menu");
    const closeBtn = qs(".nav-close");

    if (toggle && menu) {
      toggle.setAttribute("aria-controls", "nav-menu");
      toggle.setAttribute("aria-expanded", "false");
      menu.setAttribute("hidden", "");

      const openMenu = () => {
        toggle.setAttribute("aria-expanded", "true");
        menu.removeAttribute("hidden");
        menu.classList.add("active");
        document.body.classList.add("nav-open");
        if (closeBtn) closeBtn.hidden = false;
      };

      const closeMenu = () => {
        toggle.setAttribute("aria-expanded", "false");
        menu.setAttribute("hidden", "");
        menu.classList.remove("active");
        document.body.classList.remove("nav-open");
        if (closeBtn) closeBtn.hidden = true;
      };

      toggle.addEventListener("click", () => {
        const expanded = toggle.getAttribute("aria-expanded") === "true";
        expanded ? closeMenu() : openMenu();
      });

      if (closeBtn) closeBtn.addEventListener("click", closeMenu);

      document.addEventListener("click", (e) => {
        const expanded = toggle.getAttribute("aria-expanded") === "true";
        if (!expanded) return;
        if (
          !menu.contains(e.target) &&
          !toggle.contains(e.target) &&
          (!closeBtn || !closeBtn.contains(e.target))
        ) {
          closeMenu();
        }
      });

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeMenu();
      });

      // Reset when resizing
      window.addEventListener(
        "resize",
        throttle(() => {
          if (window.innerWidth >= 900) {
            menu.removeAttribute("hidden");
            menu.classList.remove("active");
            document.body.classList.remove("nav-open");
            if (closeBtn) closeBtn.hidden = true;
            toggle.setAttribute("aria-expanded", "true");
          } else if (toggle.getAttribute("aria-expanded") !== "true") {
            menu.setAttribute("hidden", "");
            menu.classList.remove("active");
            if (closeBtn) closeBtn.hidden = true;
          }
        }, 150)
      );
    }

    // ===========================
    // Dropdowns (.has-sub)
    // ===========================
    qsa(".has-sub .menu-parent").forEach((btn) => {
      const parent = btn.closest(".has-sub");
      const submenu = parent ? qs(".submenu", parent) : null;
      if (!submenu) return;

      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-haspopup", "true");
      submenu.setAttribute("role", "menu");
      submenu.setAttribute("hidden", "");

      const open = () => {
        btn.setAttribute("aria-expanded", "true");
        submenu.removeAttribute("hidden");
        submenu.style.display = "block";
      };

      const close = () => {
        btn.setAttribute("aria-expanded", "false");
        submenu.setAttribute("hidden", "");
        submenu.style.display = "none";
      };

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const expanded = btn.getAttribute("aria-expanded") === "true";
        qsa(".has-sub .menu-parent").forEach((other) => {
          if (other !== btn) {
            const sibSub = other.parentElement.querySelector(".submenu");
            if (sibSub) {
              other.setAttribute("aria-expanded", "false");
              sibSub.setAttribute("hidden", "");
              sibSub.style.display = "none";
            }
          }
        });
        expanded ? close() : open();
      });

      btn.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          const expanded = btn.getAttribute("aria-expanded") === "true";
          expanded ? close() : open();
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          open();
          const firstItem = qs("a,button,[tabindex]:not([tabindex='-1'])", submenu);
          firstItem && firstItem.focus();
        } else if (e.key === "Escape") {
          close(); btn.focus();
        }
      });

      document.addEventListener("click", (e) => { if (!parent.contains(e.target)) close(); });
      submenu.addEventListener("keydown", (e) => {
        if (e.key === "Escape") { e.stopPropagation(); close(); btn.focus(); }
      });
    });
  });
})();
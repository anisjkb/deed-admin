// frontend/static/js/admin/scripts.js
document.addEventListener("DOMContentLoaded", function () {
  // === Notification Dropdown ===
  const notificationBtn = document.querySelector(".notification-btn");
  const notificationDropdown = document.querySelector(".notification-dropdown");
  const closeBtn = document.querySelector(".close-btn");

  // Profile dropdown elements
  const profileImg = document.querySelector(".profile-img");
  const profileBtn = document.querySelector(".dropbtn");
  const profileDropdown = document.querySelector(".dropdown-content");

  function toggleProfile(e) {
    if (!profileDropdown || !profileBtn) return;
    profileDropdown.classList.toggle("show");
    const chevron = profileBtn.querySelector("i");
    if (chevron) {
      chevron.classList.toggle("fa-chevron-up");
      chevron.classList.toggle("fa-chevron-down");
    }
    e.stopPropagation();
    if (notificationDropdown && notificationDropdown.classList.contains("show")) {
      notificationDropdown.classList.remove("show");
    }
  }

  function toggleNotification(e) {
    if (!notificationDropdown) return;
    notificationDropdown.classList.toggle("show");
    e.stopPropagation();
    if (profileDropdown && profileDropdown.classList.contains("show")) {
      profileDropdown.classList.remove("show");
      if (profileBtn) {
        const chevron = profileBtn.querySelector("i");
        if (chevron) {
          chevron.classList.remove("fa-chevron-up");
          chevron.classList.add("fa-chevron-down");
        }
      }
    }
  }

  if (notificationBtn && notificationDropdown) notificationBtn.addEventListener("click", toggleNotification);
  if (closeBtn && notificationDropdown) {
    closeBtn.addEventListener("click", (e) => {
      notificationDropdown.classList.remove("show");
      e.stopPropagation();
    });
  }
  if (profileImg) profileImg.addEventListener("click", toggleProfile);
  if (profileBtn) profileBtn.addEventListener("click", toggleProfile);

  window.addEventListener("click", (e) => {
    if (
      profileDropdown && profileBtn && profileImg &&
      !profileDropdown.contains(e.target) &&
      !profileBtn.contains(e.target) &&
      !profileImg.contains(e.target)
    ) {
      profileDropdown.classList.remove("show");
      const chevron = profileBtn.querySelector("i");
      if (chevron) {
        chevron.classList.remove("fa-chevron-up");
        chevron.classList.add("fa-chevron-down");
      }
    }
    if (
      notificationDropdown && notificationBtn &&
      !notificationDropdown.contains(e.target) &&
      !notificationBtn.contains(e.target)
    ) {
      notificationDropdown.classList.remove("show");
    }
  });

  if (profileDropdown) {
    profileDropdown.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => profileDropdown.classList.remove("show"));
    });
  }

  // === Sidebar: Caret Toggle + Active Highlight ===
  const sidebarContainer = document.querySelector(".left-slidebar.app-nav");

  const toggleMenuItem = (li) => {
    if (!li) return;
    const willOpen = !li.classList.contains("open");
    const parentList = li.parentElement;
    if (parentList) {
      parentList.querySelectorAll(":scope > .menu-item.has-children.open").forEach((sib) => {
        if (sib !== li) {
          sib.classList.remove("open");
          const sibAnchor = sib.querySelector(":scope > a");
          if (sibAnchor) sibAnchor.setAttribute("aria-expanded", "false");
        }
      });
    }
    li.classList.toggle("open", willOpen);
    const anchor = li.querySelector(":scope > a");
    if (anchor) anchor.setAttribute("aria-expanded", String(willOpen));
  };

  if (sidebarContainer) {
    sidebarContainer.addEventListener("click", (e) => {
      // Parent toggle
      const anchor = e.target.closest(".menu-item.has-children > a");
      if (anchor) {
        e.preventDefault();
        toggleMenuItem(anchor.parentElement);
        setTimeout(positionEdgeToggle, 0); // reposition orb
        return;
      }

      // Block placeholder links (#)
      const anyAnchor = e.target.closest(".side-menu a");
      if (anyAnchor) {
        const href = (anyAnchor.getAttribute("href") || "").trim();
        if (href === "#" || href === "/#" || href.startsWith("#")) e.preventDefault();
      }

      // Leaf active highlight
      const leafAnchor = e.target.closest(".side-menu a");
      if (leafAnchor && !leafAnchor.closest(".menu-item.has-children > a")) {
        const allLis = sidebarContainer.querySelectorAll(".side-menu li");
        allLis.forEach((i) => i.classList.remove("active"));
        const leafLi = leafAnchor.closest("li");
        if (leafLi) leafLi.classList.add("active");
      }
    });

    // Keyboard toggle for parent rows
    sidebarContainer.addEventListener("keydown", (e) => {
      const anchor = e.target.closest(".menu-item.has-children > a");
      if (!anchor) return;
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleMenuItem(anchor.parentElement);
        setTimeout(positionEdgeToggle, 0);
      }
    });

    // ARIA init
    sidebarContainer.querySelectorAll(".menu-item.has-children > a").forEach((a) => {
      a.setAttribute("role", "button");
      a.setAttribute("aria-expanded", "false");
      a.setAttribute("aria-haspopup", "true");
      a.setAttribute("tabindex", "0");
    });

    // Auto-open based on current path
    const currentPath = window.location.pathname.replace(/\/+$/, "");
    const activeLink = sidebarContainer.querySelector(`.side-menu a[href="${currentPath}"]`);
    if (activeLink) {
      const leafLi = activeLink.closest("li");
      if (leafLi) leafLi.classList.add("active");
      let ancestor = activeLink.closest(".menu-item");
      while (ancestor) {
        if (ancestor.classList.contains("has-children")) {
          ancestor.classList.add("open");
          const a = ancestor.querySelector(":scope > a");
          if (a) a.setAttribute("aria-expanded", "true");
        }
        ancestor = ancestor.parentElement?.closest(".menu-item");
      }
      setTimeout(positionEdgeToggle, 0);
    }
  }

  // Simple fallback active highlight (non-parent)
  const sidebarItems = document.querySelectorAll(".left-slidebar.app-nav li");
  sidebarItems.forEach((item) => {
    item.addEventListener("click", () => {
      if (item.classList.contains("has-children")) return;
      sidebarItems.forEach((i) => i.classList.remove("active"));
      item.classList.add("active");
    });
  });

  // === Sidebar: mind-blowing edge orb toggle (position + magnetic + persist) ===
  const nav = document.querySelector('.left-slidebar.app-nav');
  const navToggle = document.getElementById('navToggle');

  function positionEdgeToggle() {
    if (!nav || !navToggle) return;
    const items = nav.querySelectorAll('.side-menu > .menu-item');
    if (items.length < 2) { navToggle.style.top = '12px'; return; }

    const rectSidebar = nav.getBoundingClientRect();
    const r1 = items[0].getBoundingClientRect();
    const r2 = items[1].getBoundingClientRect();
    const btnH = navToggle.getBoundingClientRect().height || 46;

    const midY = (r1.bottom + r2.top) / 2;
    const topPx = Math.max(8, midY - rectSidebar.top - btnH / 2);
    navToggle.style.top = `${topPx}px`;
  }

  function setButtonState(collapsed) {
    const icon = navToggle?.querySelector('i');
    if (!icon) return;
    if (collapsed) {
      icon.classList.remove('fa-chevron-left');
      icon.classList.add('fa-chevron-right');
      navToggle.setAttribute('title', 'Expand sidebar');
      navToggle.setAttribute('aria-label', 'Expand sidebar');
    } else {
      icon.classList.remove('fa-chevron-right');
      icon.classList.add('fa-chevron-left');
      navToggle.setAttribute('title', 'Collapse sidebar');
      navToggle.setAttribute('aria-label', 'Collapse sidebar');
    }
  }

  // Magnetic hover (subtle)
  let magnetRAF = null;
  function enableMagnetism() {
    if (!nav || !navToggle) return;
    const maxPull = 6;   // px
    const magnetZone = 64;

    function onMove(e) {
      cancelAnimationFrame(magnetRAF);
      magnetRAF = requestAnimationFrame(() => {
        const orb = navToggle.getBoundingClientRect();
        const cx = orb.left + orb.width / 2;
        const cy = orb.top + orb.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const dist = Math.sqrt(dx*dx + dy*dy);

        if (dist < magnetZone) {
          const pull = (1 - dist / magnetZone) * maxPull;
          const nx = (dx / (dist || 1)) * pull;
          const ny = (dy / (dist || 1)) * pull;
          navToggle.style.transform = `translate(${nx}px, ${ny - 1}px)`;
        } else {
          navToggle.style.transform = '';
        }
      });
    }

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseleave', () => (navToggle.style.transform = ''));
  }

  (function initOrbToggle(){
    if (!nav || !navToggle) return;

    // Restore persisted collapsed state
    const saved = localStorage.getItem('sidebar-collapsed');
    if (saved === '1') nav.classList.add('is-collapsed');
    setButtonState(nav.classList.contains('is-collapsed'));

    // Initial positioning after layout/fonts
    requestAnimationFrame(() => {
      positionEdgeToggle();
      setTimeout(positionEdgeToggle, 120);
    });

    // Reposition on resize and when menu opens/closes
    window.addEventListener('resize', positionEdgeToggle);
    nav.addEventListener('click', (e) => {
      if (e.target.closest('.menu-item.has-children > a')) {
        setTimeout(positionEdgeToggle, 0);
      }
    });

    // Toggle behavior
    navToggle.addEventListener('click', () => {
      const collapsed = !nav.classList.contains('is-collapsed');
      nav.classList.toggle('is-collapsed', collapsed);
      setButtonState(collapsed);
      localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
      setTimeout(positionEdgeToggle, 0);
      if (!navToggle.classList.contains('hint')) {
        navToggle.classList.add('hint');
        setTimeout(() => navToggle.classList.remove('hint'), 3000);
      }
    });

    // Magnetic hover
    enableMagnetism();
  })();

  // === Logout ===
  const logoutLink = document.getElementById("logoutLink");
  if (logoutLink) {
    logoutLink.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        const csrf = document.cookie.split("; ").find(c => c.startsWith("XSRF-TOKEN="));
        const csrfToken = csrf ? csrf.split("=")[1] : "";
        await fetch("/auth/logout", {
          method: "POST",
          headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
          credentials: "include"
        });
        try { localStorage.removeItem("access_token"); } catch(_) {}
        window.location.href = "/login";
      } catch (err) {
        console.error("Logout failed:", err);
        window.location.href = "/login";
      }
    });
  }
});

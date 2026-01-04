// frontend/static/js/dashboard.js
(async function () {
  // 1) Check logged-in user (auto-refresh on 401 via Auth.authFetch)
  let me = null;
  try {
    const res = await Auth.authFetch("/auth/me", { method: "GET" });

    if (!res.ok) {
      const text = await res.text();
      console.error("Auth check failed: ", res.status, text);
      throw new Error(`Not authenticated (${res.status})`);
    }
    me = await res.json();
    console.log("Authenticated user:", me);
  } catch (e) {
    console.warn("Auth check failed, redirecting → /login", e);
    window.location.href = "/login";
    return;
  }

  // Greeting
  const greet = document.getElementById("greeting");
  if (greet && me?.username) greet.textContent = `Welcome, ${me.username}!`;

  // Show logout button
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) logoutBtn.style.display = "inline-block";

  // 2) Fetch menu (now via Auth.authFetch so Authorization is attached)
  let menuData = { items: [], role: "guest" };
  try {
    const mres = await Auth.authFetch("/api/menu");
    if (mres.ok) {
      menuData = await mres.json();
      console.log("Menu data:", menuData);
    } else {
      console.warn("Menu fetch failed:", mres.status);
    }
  } catch (e) {
    console.error("Menu fetch error:", e);
  }

  // 3) Render menu
  const panel = document.getElementById("menu-panel");
  if (panel) {
    panel.innerHTML = "";
    if (Array.isArray(menuData.items) && menuData.items.length) {
      for (const item of menuData.items) {
        const el = document.createElement("button");
        el.type = "button";
        el.className = "menu-item";
        el.textContent = item.label || "Item";
        if (item.id) el.id = item.id;

        el.addEventListener("click", (ev) => {
          ev.preventDefault();
          if (item.href && item.href !== "#") {
            window.location.href = item.href;
          } else if (item.page_name) {
            loadContent(item.page_name);
          }
        });
        panel.appendChild(el);
      }
    } else {
      const msg = document.createElement("div");
      msg.className = "menu-empty";
      msg.textContent = "No menu items.";
      panel.appendChild(msg);
    }
  }

  // 4) Logout
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async (ev) => {
      ev.preventDefault();
      const csrf = Auth.getCookie("XSRF-TOKEN");
      try {
        await fetch("/auth/logout", {
          method: "POST",
          headers: csrf ? { "X-CSRF-Token": csrf } : {},
          credentials: "include",
        });
      } catch (err) {
        console.error("Logout request failed:", err);
      }
      Auth.clearAccessToken();
      console.log("Logged out → redirecting home");
      window.location.href = "/";
    });
  }
})();

function loadContent(pageName) {
  const panel = document.getElementById("content-panel");
  if (panel) panel.innerHTML = `<h2>Loading ${pageName}...</h2>`;
}
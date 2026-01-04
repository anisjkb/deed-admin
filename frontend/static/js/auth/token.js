// frontend/static/js/auth/token.js
(function () {
  const ACCESS_KEY = "access_token";

  // single-flight guard for refresh
  let refreshInFlight = null;

  // prevent spamming modals/redirects if many requests fail together
  let handlingAuthFailure = false;

  // ✅ Optional cross-script guard (used by activity-refresh.js if present)
  // If activity-refresh sets window.__authRefreshing = true during proactive refresh,
  // token.js will avoid starting a second refresh on a simultaneous 401.
  function isProactiveRefreshInProgress() {
    try {
      return Boolean(window.__authRefreshing);
    } catch {
      return false;
    }
  }

  function setAccessToken(token) {
    if (token) {
      sessionStorage.setItem(ACCESS_KEY, token);
      // console.log("✅ Access token stored");
    }
  }

  function getAccessToken() {
    return sessionStorage.getItem(ACCESS_KEY);
  }

  function clearAccessToken() {
    sessionStorage.removeItem(ACCESS_KEY);
    // console.log("🧹 Access token cleared");
  }

  // Prefer global helper from csrf.js (no regex), fallback inline
  function getCookie(name) {
    if (window.CSRF?.getCookie) return window.CSRF.getCookie(name);
    const parts = document.cookie ? document.cookie.split("; ") : [];
    for (const part of parts) {
      const idx = part.indexOf("=");
      const k = idx === -1 ? part : part.slice(0, idx);
      if (k === name) return decodeURIComponent(idx === -1 ? "" : part.slice(idx + 1));
    }
    return "";
  }

  // Clear non-httpOnly cookies (best effort)
  function clearNonHttpOnlyCookies() {
    try {
      const cookies = document.cookie ? document.cookie.split("; ") : [];
      for (const c of cookies) {
        const eq = c.indexOf("=");
        const name = eq > -1 ? c.slice(0, eq) : c;
        document.cookie = `${name}=; Max-Age=0; path=/`;
      }
    } catch {}
  }

  // Should we attach Authorization header to this URL?
  function shouldAttachAuth(url) {
    try {
      const u = new URL(url, window.location.origin);
      // Only attach to same-origin requests
      if (u.origin !== window.location.origin) return false;
      // Never attach Authorization to auth endpoints
      return !/^\/auth\/(login|register|refresh|logout)$/.test(u.pathname);
    } catch {
      // if url parsing fails, assume it's relative and safe
      return true;
    }
  }

  // Some endpoints should not trigger session timeout UI (assets etc.)
  function isSkippablePath(url) {
    try {
      const u = new URL(url, window.location.origin);
      return (
        u.pathname.startsWith("/static/") ||
        u.pathname.startsWith("/favicon") ||
        u.pathname.endsWith(".css") ||
        u.pathname.endsWith(".js") ||
        u.pathname.endsWith(".png") ||
        u.pathname.endsWith(".jpg") ||
        u.pathname.endsWith(".jpeg") ||
        u.pathname.endsWith(".webp") ||
        u.pathname.endsWith(".avif") ||
        u.pathname.endsWith(".ico")
      );
    } catch {
      return false;
    }
  }

  async function serverLogoutBestEffort() {
    // Clears HTTP-only cookies on the server response
    try {
      const csrf = getCookie("XSRF-TOKEN");
      await fetch("/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: csrf ? { "X-CSRF-Token": csrf } : {},
        cache: "no-store",
      });
    } catch {}
  }

  function showSessionTimeoutModalOnce() {
    if (handlingAuthFailure) return;
    handlingAuthFailure = true;

    if (window.SessionTimeout?.show) {
      window.SessionTimeout.show();
      return;
    }

    // fallback
    clearAccessToken();
    clearNonHttpOnlyCookies();
    serverLogoutBestEffort().finally(() => {
      window.location.href = "/login";
    });
  }

  function showForbiddenModalOnce(detail) {
    if (handlingAuthFailure) return;
    handlingAuthFailure = true;

    if (window.SessionTimeout?.forbidden) {
      window.SessionTimeout.forbidden(detail);
      return;
    }

    // fallback: just go home
    window.location.href = "/";
  }

  async function doRefresh() {
    const csrf = getCookie("XSRF-TOKEN");
    const res = await fetch("/auth/refresh", {
      method: "POST",
      headers: csrf ? { "X-CSRF-Token": csrf } : {},
      credentials: "include",
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`Refresh failed: ${res.status}`);
    }

    const data = await res.json().catch(() => ({}));
    if (!data.access_token) {
      throw new Error("Refresh response missing access_token");
    }

    setAccessToken(data.access_token);
    return data.access_token;
  }

  async function refreshOnce() {
    if (!refreshInFlight) {
      refreshInFlight = (async () => {
        try {
          return await doRefresh();
        } finally {
          // allow next refresh on next tick
          setTimeout(() => (refreshInFlight = null), 0);
        }
      })();
    }
    return refreshInFlight;
  }

  function parseJsonSafely(res) {
    return res.clone().json().catch(() => null);
  }

  async function authFetch(url, options = {}) {
    const opts = { credentials: "include", cache: "no-store", ...options };
    const method = (opts.method || "GET").toUpperCase();

    // Build headers
    let headers = new Headers(opts.headers || {});

    // Attach Authorization (only if you keep access token in sessionStorage)
    if (shouldAttachAuth(url)) {
      const at = getAccessToken();
      if (at && !headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${at}`);
      }
    }

    // Add CSRF header for mutating requests
    if (method !== "GET" && !headers.has("X-CSRF-Token")) {
      const csrf = getCookie("XSRF-TOKEN");
      if (csrf) headers.set("X-CSRF-Token", csrf);
    }

    // First attempt
    let res = await fetch(url, { ...opts, headers });

    // Handle 403 (permission)
    if (res.status === 403 && !isSkippablePath(url)) {
      const body = await parseJsonSafely(res);
      const detail = body?.error_details || body?.detail || body?.message || "Forbidden";
      showForbiddenModalOnce(detail);
      return res;
    }

    // If not 401 or auth not required, return
    if (res.status !== 401 || !shouldAttachAuth(url) || isSkippablePath(url)) {
      return res;
    }

    // ✅ Optional enterprise-clean overlap handling:
    // If proactive refresh is already running (activity-refresh.js), don't start another refresh.
    // Let the request return 401; caller can retry, or next navigation/API call will succeed.
    if (isProactiveRefreshInProgress()) {
      return res;
    }

    // If we don't even have a JS token, this is likely cookie-based navigation.
    // Avoid infinite refresh loops; allow backend redirect handling / modal logic.
    // (Your app uses full navigation + httpOnly cookies too.)
    if (!getAccessToken()) {
      showSessionTimeoutModalOnce();
      return res;
    }

    // console.warn("⚠️ 401 → attempting silent refresh…");

    // Try refresh + retry
    try {
      await refreshOnce();

      // Rebuild headers from scratch (avoid stale Authorization)
      headers = new Headers(opts.headers || {});
      const fresh = getAccessToken();
      if (fresh) headers.set("Authorization", `Bearer ${fresh}`);

      if (method !== "GET" && !headers.has("X-CSRF-Token")) {
        const csrf = getCookie("XSRF-TOKEN");
        if (csrf) headers.set("X-CSRF-Token", csrf);
      }

      const retry = await fetch(url, { ...opts, headers });

      // Handle 403 after retry
      if (retry.status === 403 && !isSkippablePath(url)) {
        const body = await parseJsonSafely(retry);
        const detail = body?.error_details || body?.detail || body?.message || "Forbidden";
        showForbiddenModalOnce(detail);
      }

      // Still 401 → show session timeout modal once
      if (retry.status === 401 && !isSkippablePath(url)) {
        showSessionTimeoutModalOnce();
      }

      return retry;
    } catch (e) {
      // console.error("❌ Silent refresh failed:", e);
      showSessionTimeoutModalOnce();
      return res;
    }
  }

  // Utility: fetch wrapper that returns JSON if possible
  async function authFetchJson(url, options = {}) {
    const res = await authFetch(url, options);
    const data = await res.json().catch(() => null);
    return { res, data };
  }

  window.Auth = {
    setAccessToken,
    getAccessToken,
    clearAccessToken,
    getCookie,
    authFetch,
    authFetchJson,
  };
})();
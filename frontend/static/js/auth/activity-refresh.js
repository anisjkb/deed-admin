// frontend/static/js/auth/activity-refresh.js
(function () {
  // Only run on admin pages
  if (!location.pathname.startsWith("/admin/")) return;

  // Refresh only when remaining lifetime below this (seconds)
  // Keep <= 25-40 sec so we refresh only very close to expiry.
  const SKEW_SECONDS = 30;

  // Heartbeat checks while user is active (does NOT always refresh)
  const HEARTBEAT_MS = 60_000; // 60s (lighter than 30s)

  // Idle-only expiration behavior: stop keepalive after inactivity
  const MAX_IDLE_MS = 2 * 60 * 1000; // 2 minutes

  // Prevent refresh storms + reduce DB writes
  // With ACCESS_TOKEN_EXPIRE_MINUTES=3, 90s gap is a good balance.
  const MIN_REFRESH_GAP_MS = 90_000; // 90s

  // Activity debounce (we only need to know "user is active")
  const ACTIVITY_DEBOUNCE_MS = 2_000;

  let lastActivityAt = Date.now();
  let lastRefreshAttemptAt = 0;

  // Single-flight guard
  let refreshPromise = null;

  function now() {
    return Date.now();
  }

  function markActivity() {
    lastActivityAt = now();
  }

  // Decode exp from JWT without verification (frontend convenience)
  function getJwtExpSeconds(token) {
    try {
      const part = token.split(".")[1];
      if (!part) return null;
      const json = JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/")));
      return typeof json.exp === "number" ? json.exp : null;
    } catch {
      return null;
    }
  }

  function secondsUntilExpiry(token) {
    const exp = getJwtExpSeconds(token);
    if (!exp) return null;
    const nowSec = Math.floor(Date.now() / 1000);
    return exp - nowSec;
  }

  function needsRefreshSoon() {
    const at = window.Auth?.getAccessToken?.();
    if (!at) return false; // important: don't refresh just because missing

    const left = secondsUntilExpiry(at);
    if (left == null) {
      // token exists but cannot parse -> refresh once (rare due to MIN_REFRESH_GAP_MS)
      return true;
    }
    return left <= SKEW_SECONDS;
  }

  function isIdleTooLong() {
    return now() - lastActivityAt > MAX_IDLE_MS;
  }

  async function refreshAccessTokenOnce() {
    if (refreshPromise) return refreshPromise;

    refreshPromise = (async () => {
      try {
        const csrf = window.Auth?.getCookie?.("XSRF-TOKEN") || "";
        const res = await fetch("/auth/refresh", {
          method: "POST",
          credentials: "include",
          cache: "no-store",
          headers: csrf ? { "X-CSRF-Token": csrf } : {},
        });

        if (!res.ok) return false;

        const data = await res.json().catch(() => ({}));
        if (data?.access_token && window.Auth?.setAccessToken) {
          window.Auth.setAccessToken(data.access_token);
        }
        return true;
      } catch {
        return false;
      } finally {
        // release single-flight quickly
        setTimeout(() => (refreshPromise = null), 250);
      }
    })();

    return refreshPromise;
  }

  async function maybeRefreshOrLogout(reason) {
    // throttle hard (major DB-write reduction)
    if (now() - lastRefreshAttemptAt < MIN_REFRESH_GAP_MS) return true;

    // idle-only: do not keep session alive in background
    if (isIdleTooLong()) return true;

    // only refresh if actually needed
    if (!needsRefreshSoon()) return true;

    lastRefreshAttemptAt = now();
    const ok = await refreshAccessTokenOnce();
    if (ok) return true;

    // refresh failed -> your UX
    if (window.SessionTimeout?.show) {
      window.SessionTimeout.show();
    } else {
      window.location.href = "/login";
    }
    return false;
  }

  // 1) Heartbeat: check sometimes, refresh ONLY if near expiry + user active
  setInterval(async () => {
    if (isIdleTooLong()) return;
    await maybeRefreshOrLogout("heartbeat");
  }, HEARTBEAT_MS);

  // 2) Activity signals (cheap): mark user as active
  let activityTimer = null;
  function debouncedActivity() {
    if (activityTimer) return;
    activityTimer = setTimeout(() => {
      activityTimer = null;
      markActivity();
    }, ACTIVITY_DEBOUNCE_MS);
  }

  ["click", "keydown", "mousemove", "scroll", "touchstart"].forEach((ev) => {
    window.addEventListener(ev, debouncedActivity, { passive: true });
  });

  // Also mark activity when tab becomes visible again
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) markActivity();
  });

  // 3) Before admin navigation:
  // IMPORTANT CHANGE:
  // - Only block navigation if refresh is actually needed soon.
  // - Otherwise let the browser navigate normally (no refresh, no DB write).
  document.addEventListener(
    "click",
    async (e) => {
      const a = e.target?.closest?.("a");
      if (!a) return;

      const href = a.getAttribute("href") || "";
      if (!href.startsWith("/admin/")) return;

      // allow new tab / modified clicks
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (a.target && a.target !== "_self") return;

      // If not near expiry, do NOT refresh, do NOT prevent default
      if (!needsRefreshSoon() || isIdleTooLong()) return;

      // Near expiry: refresh then navigate (throttled)
      e.preventDefault();
      const ok = await maybeRefreshOrLogout("nav");
      if (ok) window.location.href = href;
    },
    true
  );

  // 4) Before protected form submit:
  // IMPORTANT CHANGE:
  // - Only block submit if near expiry.
  document.addEventListener(
    "submit",
    async (e) => {
      const form = e.target;
      if (!form || !(form instanceof HTMLFormElement)) return;

      const action = form.getAttribute("action") || location.pathname;
      if (!action.startsWith("/admin/")) return;

      // If not near expiry, submit normally
      if (!needsRefreshSoon() || isIdleTooLong()) return;

      e.preventDefault();
      const ok = await maybeRefreshOrLogout("submit");
      if (ok) form.submit();
    },
    true
  );
})();
// frontend/static/js/auth/session-timeout.js
(function () {
  let modalOpen = false;

  function toast(msg) {
    try {
      if (window.showToast) return window.showToast(msg);
      if (window.Toast?.show) return window.Toast.show(msg);
    } catch {}
    // final fallback
    try { console.warn(msg); } catch {}
  }

  function safeClearClientState() {
    try {
      // client-side token (sessionStorage)
      if (window.Auth?.clearAccessToken) window.Auth.clearAccessToken();
      else sessionStorage.removeItem("access_token");
    } catch {}

    // clear non-httpOnly cookies (httpOnly cannot be cleared by JS)
    try {
      const cookies = document.cookie ? document.cookie.split("; ") : [];
      for (const c of cookies) {
        const eq = c.indexOf("=");
        const name = eq > -1 ? c.slice(0, eq) : c;
        document.cookie = `${name}=; Max-Age=0; path=/`;
      }
    } catch {}
  }

  async function logoutServerSide() {
    // clears HTTP-only cookies on server response
    try {
      const csrf = window.Auth?.getCookie ? window.Auth.getCookie("XSRF-TOKEN") : "";
      await fetch("/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: csrf ? { "X-CSRF-Token": csrf } : {},
      });
    } catch {}
  }

  function showModal({
    title,
    message,
    okText,
    noText,
    onOk,
    onNo,
    okClass,
    noClass,
    toastFallbackText,
  }) {
    if (modalOpen) return;
    modalOpen = true;

    // If confirm.js isn't loaded, fallback behavior
    if (!window.openConfirmModal) {
      toast(toastFallbackText || message || "Session expired.");
      (async () => {
        safeClearClientState();
        await logoutServerSide();
        window.location.href = "/login";
      })();
      return;
    }

    window.openConfirmModal({
      title,
      message,
      okText,
      noText,
      okClass: okClass || "btn btn-primary",
      noClass: noClass || "btn btn-secondary",
      onOk: async () => {
        try {
          await onOk?.();
        } finally {
          modalOpen = false;
          if (window.closeConfirmModal) window.closeConfirmModal();
        }
      },
      onNo: async () => {
        try {
          await onNo?.();
        } finally {
          modalOpen = false;
          if (window.closeConfirmModal) window.closeConfirmModal();
        }
      },
    });
  }

  function showSessionTimeoutModal() {
    showModal({
      title: '<i class="fas fa-clock"></i> Session Expired',
      message:
        "Your session has timed out. Please log in again to continue.",
      okText: "Login",
      noText: "Home",
      toastFallbackText: "Session expired. Redirecting to login…",
      onOk: async () => {
        safeClearClientState();
        await logoutServerSide();
        window.location.href = "/login";
      },
      onNo: async () => {
        safeClearClientState();
        await logoutServerSide();
        window.location.href = "/";
      },
    });
  }

  function showForbiddenModal(detail) {
    const msg = detail
      ? `Access denied. You don't have permission to access this page.\n\n${detail}`
      : "Access denied. You don't have permission to access this page.";

    showModal({
      title: '<i class="fas fa-ban"></i> Access Denied',
      message: msg,
      okText: "Okay",
      noText: "Home",
      okClass: "btn btn-primary",
      noClass: "btn btn-secondary",
      toastFallbackText: "Access denied.",
      onOk: async () => {
        // close only
        if (window.closeConfirmModal) window.closeConfirmModal();
      },
      onNo: async () => {
        window.location.href = "/";
      },
    });
  }

  // ✅ For home.html bootstrap: /?auth=expired|forbidden
  function handleAuthFlag(flag) {
    const f = (flag || "").toLowerCase();
    if (f === "expired") return showSessionTimeoutModal();
    if (f === "forbidden") return showForbiddenModal();
  }

  // Expose for token.js (or others) to call
  window.SessionTimeout = {
    show: showSessionTimeoutModal,
    forbidden: showForbiddenModal,
    handleAuthFlag,
    clear: async () => {
      safeClearClientState();
      await logoutServerSide();
    },
  };
})();
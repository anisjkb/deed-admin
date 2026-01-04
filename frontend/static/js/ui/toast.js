// frontend/static/js/ui/toast.js
// No inline <style> injection. No inline style assignments.
// Uses class toggles + WAAPI for progress timing.

(function () {
  if (window.Toast) return;

  function ensureRoot() {
    let r = document.getElementById("toast-root");
    if (!r) {
      r = document.createElement("div");
      r.id = "toast-root";
      r.setAttribute("aria-live", "polite");
      r.setAttribute("aria-atomic", "true");
      document.body.appendChild(r);
    }
    return r;
  }

  const root = ensureRoot();

  function remove(node) {
    node.classList.add("toast--closing");
    setTimeout(() => node.remove(), 160);
  }

  function show({ title, message, type = "info", duration = 4000, dismissible = true }) {
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.setAttribute("role", "status");

    const content = document.createElement("div");
    content.className = "toast__content";

    if (title) {
      const t = document.createElement("div");
      t.className = "toast__title";
      t.textContent = title;
      content.appendChild(t);
    }

    if (message) {
      const m = document.createElement("div");
      m.className = "toast__msg";
      m.textContent = message;
      content.appendChild(m);
    }

    el.appendChild(content);

    if (dismissible) {
      const closeBtn = document.createElement("button");
      closeBtn.className = "toast__close";
      closeBtn.setAttribute("aria-label", "Dismiss notification");
      closeBtn.textContent = "×";
      closeBtn.addEventListener("click", () => remove(el));
      el.appendChild(closeBtn);
    }

    const progress = document.createElement("div");
    progress.className = "toast__progress";
    const bar = document.createElement("div");
    bar.className = "toast__bar";
    progress.appendChild(bar);
    el.appendChild(progress);

    root.appendChild(el);

    // Progress with WAAPI (doesn't use inline style attributes)
    if (duration > 0 && bar.animate) {
      const anim = bar.animate([{ width: "100%" }, { width: "0%" }], {
        duration,
        easing: "linear",
        fill: "forwards",
      });

      let remaining = duration;
      let start = performance.now();
      let timer = setTimeout(() => remove(el), duration);

      el.addEventListener("mouseenter", () => {
        try { anim.pause(); } catch {}
        clearTimeout(timer);
        remaining -= performance.now() - start;
      });

      el.addEventListener("mouseleave", () => {
        start = performance.now();
        try { anim.play(); } catch {}
        timer = setTimeout(() => remove(el), remaining);
      });
    } else if (duration > 0) {
      setTimeout(() => remove(el), duration);
    }

    return el;
  }

  window.Toast = {
    show,
    success: (message, opts = {}) => show({ message, type: "success", ...opts }),
    error:   (message, opts = {}) => show({ message, type: "error",   ...opts }),
    info:    (message, opts = {}) => show({ message, type: "info",    ...opts }),
    warn:    (message, opts = {}) => show({ message, type: "warn",    ...opts }),
  };
})();
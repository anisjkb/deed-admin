// frontend/static/js/admin/confirm.js
// static/js/admin/confirm.js

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("deleteConfirmModal");
  const messageBox = document.getElementById("deleteMessage");
  const confirmBtn = document.getElementById("confirmDeleteBtn");
  const cancelBtn = document.getElementById("cancelDeleteBtn");

  if (!modal || !messageBox || !confirmBtn || !cancelBtn) return;

  // ----------------------------
  // Generic modal controller
  // ----------------------------
  let onOk = null;
  let onNo = null;

  function setTitle(htmlTitle) {
    const h3 = modal.querySelector("h3");
    if (h3) h3.innerHTML = htmlTitle;
  }

  function hideModal() {
    modal.style.display = "none";
    onOk = null;
    onNo = null;
  }

  function openConfirmModal(opts = {}) {
    const {
      title = '<i class="fas fa-exclamation-triangle"></i> Confirm',
      message = "Are you sure?",
      okText = "Okay",
      noText = "Cancel",
      okClass = "btn btn-primary",
      noClass = "btn btn-secondary",
      onOk: okHandler = () => hideModal(),
      onNo: noHandler = () => hideModal(),
    } = opts;

    setTitle(title);
    messageBox.innerText = message;

    confirmBtn.textContent = okText;
    cancelBtn.textContent = noText;

    confirmBtn.className = okClass;
    cancelBtn.className = noClass;

    onOk = okHandler;
    onNo = noHandler;

    modal.style.display = "flex";
  }

  // expose globally for session timeout, forbidden, etc.
  window.openConfirmModal = openConfirmModal;
  window.closeConfirmModal = hideModal;

  // ----------------------------
  // Existing delete-confirm forms behavior
  // ----------------------------
  const forms = document.querySelectorAll("form.delete-confirm");
  let pendingForm = null;

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      pendingForm = form;

      const msg = form.dataset.message || "Are you sure you want to delete this?";

      openConfirmModal({
        title: '<i class="fas fa-exclamation-triangle"></i> Confirm Deletion',
        message: msg,
        okText: "Yes, Delete",
        noText: "Cancel",
        okClass: "btn btn-danger",
        noClass: "btn btn-secondary",
        onOk: () => {
          // hide first to avoid double clicks
          hideModal();
          if (pendingForm) pendingForm.submit();
          pendingForm = null;
        },
        onNo: () => {
          hideModal();
          pendingForm = null;
        },
      });
    });
  });

  // ----------------------------
  // Button handlers (generic)
  // ----------------------------
  confirmBtn.addEventListener("click", function () {
    try {
      if (typeof onOk === "function") return onOk();
    } finally {
      // If handler didn't hide modal, keep it open intentionally.
      // (So you can keep modal open during async ops if you want)
    }
  });

  cancelBtn.addEventListener("click", function () {
    if (typeof onNo === "function") onNo();
    else hideModal();
  });

  // Close by clicking outside modal-box
  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      if (typeof onNo === "function") onNo();
      else hideModal();
    }
  });
});
// frontend/static/js/admin/ops/image_editor.js
document.addEventListener("DOMContentLoaded", function () {
  const fileInput       = document.getElementById("ie-file-input");
  const dropzone        = document.getElementById("ie-dropzone");
  const fileSizeLabel   = document.getElementById("ie-file-size");

  const imgEl           = document.getElementById("ie-image");
  const previewCanvas   = document.getElementById("ie-preview-canvas");
  const zoomRange       = document.getElementById("ie-zoom-range");

  const clearBtn        = document.getElementById("ie-clear-btn");
  const downloadBtn     = document.getElementById("ie-download-btn");

  const brightnessEl    = document.getElementById("ie-brightness");
  const contrastEl      = document.getElementById("ie-contrast");
  const saturationEl    = document.getElementById("ie-saturation");
  const grayscaleEl     = document.getElementById("ie-grayscale");
  const resetFiltersBtn = document.getElementById("ie-reset-filters");

  // Crop data fields
  const dataX       = document.getElementById("ie-data-x");
  const dataY       = document.getElementById("ie-data-y");
  const dataWidth   = document.getElementById("ie-data-width");
  const dataHeight  = document.getElementById("ie-data-height");
  const dataRotate  = document.getElementById("ie-data-rotate");
  const dataScaleX  = document.getElementById("ie-data-scale-x");
  const dataScaleY  = document.getElementById("ie-data-scale-y");

  let cropper = null;
  let scaleX = 1;
  let scaleY = 1;

  // Filters (percent)
  const filters = {
    brightness: 100,
    contrast:   100,
    saturation: 100,
    grayscale:  0,
  };

  // ---------- Config ----------
  const MAX_BYTES = 2 * 1024 * 1024; // 2 MB (keep your current limit)
  const ACCEPTED_IMAGE_MIMES = new Set([
    "image/avif",
    "image/webp",
    "image/png",
    "image/jpeg",
    "image/jpg"
  ]);
  const EXPORT_ORDER = ["image/avif", "image/webp", "image/png"]; // try in this order
  const EXPORT_QUALITY = 0.92; // used by AVIF/WebP if browser honors it

  // Make the input accept attribute AVIF-aware (nice UX)
  if (fileInput && !fileInput.hasAttribute("accept")) {
    fileInput.setAttribute("accept", "image/avif,image/webp,image/jpeg,image/png");
  }

  /* ------------------ Helpers ------------------ */

  function updateFileSizeLabel(file) {
    if (!file) {
      fileSizeLabel && (fileSizeLabel.textContent = "0 KB");
      return;
    }
    const kb = file.size / 1024;
    fileSizeLabel && (fileSizeLabel.textContent = `${kb.toFixed(1)} KB`);
  }

  function showMessage(type, msg) {
    const messageContainer = document.getElementById("messageContainer");
    const messageDiv = document.createElement("div");
    messageDiv.classList.add(type === "error" ? "error-message" : "message");
    messageDiv.textContent = msg;
    messageContainer && messageContainer.appendChild(messageDiv);
    setTimeout(() => { messageDiv.remove(); }, 5000);
  }

  function getFilterString() {
    return `brightness(${filters.brightness}%) `
         + `contrast(${filters.contrast}%) `
         + `saturate(${filters.saturation}%) `
         + `grayscale(${filters.grayscale}%)`;
  }

  function resetFilters() {
    filters.brightness = 100;
    filters.contrast   = 100;
    filters.saturation = 100;
    filters.grayscale  = 0;

    if (brightnessEl) brightnessEl.value = 100;
    if (contrastEl)   contrastEl.value   = 100;
    if (saturationEl) saturationEl.value = 100;
    if (grayscaleEl)  grayscaleEl.value  = 0;

    updatePreviewCanvas();
  }

  function initCropper() {
    if (!imgEl.src) return;

    if (cropper) cropper.destroy();

    cropper = new Cropper(imgEl, {
      viewMode: 1,
      dragMode: "move",
      autoCropArea: 0.8,
      background: false,
      responsive: true,
      checkOrientation: false,
      preview: null,
      ready() {
        if (zoomRange) zoomRange.value = 1;
        scaleX = 1;
        scaleY = 1;
        updatePreviewCanvas();
      },
      crop(event) {
        const d = event.detail;
        // Update numeric data
        if (dataX)      dataX.value      = Math.round(d.x);
        if (dataY)      dataY.value      = Math.round(d.y);
        if (dataWidth)  dataWidth.value  = Math.round(d.width);
        if (dataHeight) dataHeight.value = Math.round(d.height);
        if (dataRotate) dataRotate.value = Math.round(d.rotate || 0);
        if (dataScaleX) dataScaleX.value = d.scaleX != null ? d.scaleX.toFixed(2) : "1";
        if (dataScaleY) dataScaleY.value = d.scaleY != null ? d.scaleY.toFixed(2) : "1";

        updatePreviewCanvas();
      }
    });
  }

  // Robust MIME detection: prefer file.type, fall back to extension
  function sniffImageMime(file) {
    const t = (file.type || "").toLowerCase();
    if (t) return t;
    const name = (file.name || "").toLowerCase();
    if (name.endsWith(".avif")) return "image/avif";
    if (name.endsWith(".webp")) return "image/webp";
    if (name.endsWith(".png"))  return "image/png";
    if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
    return "application/octet-stream";
  }

  function loadImageFile(file) {
    if (!file) return;

    const mime = sniffImageMime(file);
    if (!mime.startsWith("image/") || !ACCEPTED_IMAGE_MIMES.has(mime)) {
      showMessage("error", "Please select a valid image file (AVIF/WebP/JPG/PNG).");
      return;
    }

    if (file.size > MAX_BYTES) {
      showMessage("error", `File is too large. Maximum size is ${(MAX_BYTES / (1024*1024)).toFixed(0)} MB.`);
      return;
    }

    updateFileSizeLabel(file);

    const reader = new FileReader();
    reader.onload = (e) => {
      imgEl.src = e.target.result;
      imgEl.style.display = "block";
      initCropper();
    };
    reader.readAsDataURL(file);
  }

  function updatePreviewCanvas() {
    if (!cropper || !previewCanvas) return;
    const croppedCanvas = cropper.getCroppedCanvas();
    if (!croppedCanvas) return;

    const ctx = previewCanvas.getContext("2d");
    const targetMaxWidth  = 260;
    const targetMaxHeight = 180;

    const scale = Math.min(
      targetMaxWidth / croppedCanvas.width,
      targetMaxHeight / croppedCanvas.height
    );

    const drawWidth  = Math.max(1, croppedCanvas.width * scale);
    const drawHeight = Math.max(1, croppedCanvas.height * scale);

    previewCanvas.width  = drawWidth;
    previewCanvas.height = drawHeight;

    ctx.clearRect(0, 0, drawWidth, drawHeight);
    ctx.filter = getFilterString();
    ctx.drawImage(croppedCanvas, 0, 0, drawWidth, drawHeight);
  }

  // Helper: try toBlob with a given MIME; fallback to next if result is null
  function exportCanvasBlob(canvas, mime, quality) {
    return new Promise((resolve) => {
      // Some browsers ignore unsupported MIME and return PNG; we guard by checking 'type'
      canvas.toBlob((blob) => {
        if (!blob) return resolve(null);
        // We accept the blob even if browser encoded to another type,
        // but most modern browsers encode to requested type if supported.
        resolve(blob);
      }, mime, quality);
    });
  }

  async function exportBestBlob(canvas) {
    for (const mime of EXPORT_ORDER) {
      const blob = await exportCanvasBlob(canvas, mime, EXPORT_QUALITY);
      if (blob) {
        // Try to infer real type if the browser silently picked something else
        const chosen = blob.type || mime;
        return { blob, mime: chosen };
      }
    }
    // Absolute last resort: PNG via dataURL conversion
    try {
      const url = canvas.toDataURL("image/png");
      const res = await fetch(url);
      const blob = await res.blob();
      return { blob, mime: "image/png" };
    } catch {
      return { blob: null, mime: "" };
    }
  }

  function mimeToExtension(mime) {
    if (mime.includes("avif")) return ".avif";
    if (mime.includes("webp")) return ".webp";
    if (mime.includes("png"))  return ".png";
    if (mime.includes("jpeg") || mime.includes("jpg")) return ".jpg";
    // Fallback
    return ".png";
  }

  async function downloadCroppedImage() {
    if (!cropper) {
      showMessage("error", "Please upload and crop an image first.");
      return;
    }

    const baseCanvas = cropper.getCroppedCanvas();
    if (!baseCanvas) {
      showMessage("error", "Unable to generate cropped image.");
      return;
    }

    // Apply filters into a new canvas so the export has them baked in
    const outCanvas = document.createElement("canvas");
    outCanvas.width  = baseCanvas.width;
    outCanvas.height = baseCanvas.height;
    const ctx = outCanvas.getContext("2d");
    ctx.filter = getFilterString();
    ctx.drawImage(baseCanvas, 0, 0);

    const { blob, mime } = await exportBestBlob(outCanvas);
    if (!blob) {
      showMessage("error", "Failed to export image.");
      return;
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const ext = mimeToExtension(mime);
    a.href = url;
    a.download = `edited-image${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showMessage("success", `Image exported as ${ext.toUpperCase().slice(1)}.`);
  }

  function clearEditor() {
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    imgEl.src = "";
    imgEl.style.display = "none";
    if (previewCanvas) {
      const ctx = previewCanvas.getContext("2d");
      ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    }
    if (fileInput) fileInput.value = "";
    updateFileSizeLabel(null);

    if (dataX) dataX.value = "";
    if (dataY) dataY.value = "";
    if (dataWidth) dataWidth.value = "";
    if (dataHeight) dataHeight.value = "";
    if (dataRotate) dataRotate.value = "";
    if (dataScaleX) dataScaleX.value = "";
    if (dataScaleY) dataScaleY.value = "";

    resetFilters();
  }

  /* ------------------ Events ------------------ */

  // File input
  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      loadImageFile(file);
    });
  }

  // Drag & drop
  if (dropzone) {
    ["dragenter", "dragover"].forEach((evt) => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (!dt || !dt.files || !dt.files.length) return;
      const file = dt.files[0];
      loadImageFile(file);
    });

    // Also allow click to trigger file dialog
    dropzone.addEventListener("click", () => {
      fileInput && fileInput.click();
    });
  }

  // Toolbar buttons (move, crop, zoom, rotate, flip, reset)
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".ie-btn");
    if (!btn || !cropper) return;

    const action = btn.dataset.action;
    if (!action) return;

    switch (action) {
      case "move":
        cropper.setDragMode("move");
        break;
      case "crop":
        cropper.setDragMode("crop");
        break;
      case "reset":
        cropper.reset();
        if (zoomRange) zoomRange.value = 1;
        scaleX = 1;
        scaleY = 1;
        resetFilters();
        break;
      case "zoom-in":
        cropper.zoom(0.1);
        if (zoomRange) zoomRange.value = Math.min(3, parseFloat(zoomRange.value || "1") + 0.1);
        break;
      case "zoom-out":
        cropper.zoom(-0.1);
        if (zoomRange) zoomRange.value = Math.max(0.2, parseFloat(zoomRange.value || "1") - 0.1);
        break;
      case "rotate-left":
        cropper.rotate(-90);
        break;
      case "rotate-right":
        cropper.rotate(90);
        break;
      case "flip-h":
        scaleX = scaleX * -1;
        cropper.scaleX(scaleX);
        break;
      case "flip-v":
        scaleY = scaleY * -1;
        cropper.scaleY(scaleY);
        break;
      default:
        break;
    }
  });

  // Zoom range slider
  if (zoomRange) {
    zoomRange.addEventListener("input", (e) => {
      if (!cropper) return;
      const val = parseFloat(e.target.value || "1");
      cropper.zoomTo(val);
    });
  }

  // Aspect ratio buttons
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".ie-aspect-buttons .ie-btn");
    if (!btn || !cropper) return;
    const aspectStr = btn.dataset.aspect;

    let aspectRatio = NaN;
    if (aspectStr && aspectStr !== "NaN") {
      try {
        const ratio = aspectStr.split("/").map(Number);
        if (ratio.length === 2 && !isNaN(ratio[0]) && !isNaN(ratio[1])) {
          aspectRatio = ratio[0] / ratio[1];
        }
      } catch { aspectRatio = NaN; }
    }
    cropper.setAspectRatio(aspectRatio);
  });

  // Filters
  function attachFilterSlider(el, key) {
    if (!el) return;
    el.addEventListener("input", (e) => {
      filters[key] = parseInt(e.target.value, 10) || filters[key];
      updatePreviewCanvas();
    });
  }
  attachFilterSlider(brightnessEl, "brightness");
  attachFilterSlider(contrastEl, "contrast");
  attachFilterSlider(saturationEl, "saturation");
  attachFilterSlider(grayscaleEl, "grayscale");

  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", () => resetFilters());
  }

  // Clear
  if (clearBtn) {
    clearBtn.addEventListener("click", () => clearEditor());
  }

  // Download
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => downloadCroppedImage());
  }

  // Initialize preview canvas size
  if (previewCanvas) {
    previewCanvas.width  = 260;
    previewCanvas.height = 180;
  }
});
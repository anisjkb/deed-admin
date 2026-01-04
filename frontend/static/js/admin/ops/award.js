// static/js/admin/ops/award.js

document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("imageInput");
  const fileSizeSpan = document.getElementById("fileSize");
  const previewImg = document.getElementById("previewImage");
  const newImageLabel = document.getElementById("newImageLabel");
  const cropContainer = document.getElementById("cropContainer");
  const cropImage = document.getElementById("cropImage");
  const deleteImageBtn = document.getElementById("deleteImageBtn");
  const deleteImageFlag = document.getElementById("deleteImageFlag");
  const existingImg = document.getElementById("existingImage");

  const MAX_SIZE = 2 * 1024 * 1024; // 2MB
  let cropper = null;

  // Allowed MIME types (now includes AVIF & WebP)
  const validTypes = [
    "image/avif",
    "image/webp",
    "image/png",
    "image/jpeg",
    "image/jpg",
  ];

  /* ---------------------- UTILITIES ---------------------- */
  function updateCropData() {
    if (!cropper) return;
    const data = cropper.getData();
    document.getElementById("dataX").value = Math.round(data.x);
    document.getElementById("dataY").value = Math.round(data.y);
    document.getElementById("dataWidth").value = Math.round(data.width);
    document.getElementById("dataHeight").value = Math.round(data.height);
    document.getElementById("dataRotate").value = Math.round(data.rotate || 0);
    document.getElementById("dataScaleX").value = data.scaleX || 1;
    document.getElementById("dataScaleY").value = data.scaleY || 1;
  }

  function resetCropArea() {
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    cropContainer.style.display = "none";
    previewImg.style.display = "none";
    newImageLabel.style.display = "none";
  }

  /* ---------------------- FILE INPUT ---------------------- */
  fileInput.addEventListener("change", function (event) {
    const file = event.target.files[0];
    if (!file) return resetCropArea();

    // Validate file type
    if (!validTypes.includes(file.type)) {
      alert("Invalid image format. Allowed: AVIF, WebP, JPG, PNG.");
      fileInput.value = "";
      return resetCropArea();
    }

    // Validate file size
    if (file.size > MAX_SIZE) {
      alert("Maximum file size is 2MB.");
      fileInput.value = "";
      return resetCropArea();
    }

    // Display size info
    fileSizeSpan.textContent = (file.size / 1024).toFixed(1) + " KB";

    // Hide existing image
    if (existingImg) existingImg.style.display = "none";

    // Load image into cropper
    const reader = new FileReader();
    reader.onload = function (e) {
      cropImage.src = e.target.result;
      cropContainer.style.display = "block";
    };
    reader.readAsDataURL(file);
  });

  /* ---------------------- CROPPER INIT ---------------------- */
  cropImage.addEventListener("load", function () {
    if (!cropImage.src) return;
    if (cropper) cropper.destroy();

    cropper = new Cropper(cropImage, {
      viewMode: 2,
      autoCropArea: 1,
      responsive: true,
      zoomOnWheel: true,
      minCropBoxWidth: 200,
      minCropBoxHeight: 200,
      ready() {
        updateCropData();
      },
      crop() {
        updateCropData();
      },
    });
  });

  /* ---------------------- TOOLBAR BUTTONS ---------------------- */
  document.getElementById("moveBtn").onclick = () => cropper.setDragMode("move");
  document.getElementById("cropBtn").onclick = () => cropper.setDragMode("crop");
  document.getElementById("zoomInBtn").onclick = () => cropper.zoom(0.1);
  document.getElementById("zoomOutBtn").onclick = () => cropper.zoom(-0.1);
  document.getElementById("rotateLeftBtn").onclick = () => cropper.rotate(-90);
  document.getElementById("rotateRightBtn").onclick = () => cropper.rotate(90);
  document.getElementById("flipXBtn").onclick = () =>
    cropper.scaleX(cropper.getData().scaleX * -1);
  document.getElementById("flipYBtn").onclick = () =>
    cropper.scaleY(cropper.getData().scaleY * -1);
  document.getElementById("resetBtn").onclick = () => cropper.reset();
  document.getElementById("undoBtn").onclick = () => cropper.undo?.();
  document.getElementById("redoBtn").onclick = () => cropper.redo?.();
  document.getElementById("lockBtn").onclick = () => cropper.disable();
  document.getElementById("unlockBtn").onclick = () => cropper.enable();
  document.getElementById("replaceBtn").onclick = () => fileInput.click();

  /* ---------------------- ASPECT RATIO ---------------------- */
  document.getElementById("ar169").onclick = () => cropper.setAspectRatio(16 / 9);
  document.getElementById("ar43").onclick = () => cropper.setAspectRatio(4 / 3);
  document.getElementById("ar11").onclick = () => cropper.setAspectRatio(1);
  document.getElementById("ar23").onclick = () => cropper.setAspectRatio(2 / 3);
  document.getElementById("arFree").onclick = () => cropper.setAspectRatio(NaN);

  /* ---------------------- CROP CONFIRM ---------------------- */
  document.getElementById("cropConfirmBtn").onclick = async function () {
    const canvas = cropper.getCroppedCanvas({ maxWidth: 1200, maxHeight: 1200 });
    if (!canvas) return alert("Could not crop image.");

    // Helper: export to first supported format (AVIF → WebP → JPEG)
    async function exportBest(canvas) {
      const types = ["image/avif", "image/webp", "image/jpeg"];
      for (const type of types) {
        try {
          const blob = await new Promise((res) =>
            canvas.toBlob(res, type, 0.92)
          );
          if (blob) return { blob, type };
        } catch {
          continue;
        }
      }
      return null;
    }

    const result = await exportBest(canvas);
    if (!result || !result.blob) return alert("Export failed.");

    const ext =
      result.type === "image/avif"
        ? "avif"
        : result.type === "image/webp"
        ? "webp"
        : "jpg";

    const croppedFile = new File([result.blob], `cropped.${ext}`, {
      type: result.type,
      lastModified: Date.now(),
    });

    const dt = new DataTransfer();
    dt.items.add(croppedFile);
    fileInput.files = dt.files;

    previewImg.src = URL.createObjectURL(croppedFile);
    previewImg.style.display = "block";
    newImageLabel.style.display = "block";
  };

  /* ---------------------- DELETE EXISTING ---------------------- */
  if (deleteImageBtn) {
    deleteImageBtn.addEventListener("click", () => {
      if (!confirm("Delete this image?")) return;
      existingImg.style.display = "none";
      deleteImageFlag.value = "1";
    });
  }
});
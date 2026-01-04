//static/js/admin/ops/banner.js
document.addEventListener('DOMContentLoaded', function () {
  // Elements for handling file input and preview
  const imageInput = document.getElementById('imageInput');
  const previewImage = document.getElementById('previewImage');
  const newImageLabel = document.getElementById('newImageLabel');
  const fileSizeElem = document.getElementById('fileSize');
  const deleteImageBtn = document.getElementById('deleteImageBtn');
  const deleteImageFlag = document.getElementById('deleteImageFlag');

  // Elements for existing image and new image preview side by side
  const existingImageContainer = document.getElementById('existingImageContainer');
  const previewSection = document.getElementById('previewSection');

  // Handle the image file change event (for new image uploads)
  if (imageInput) {
    imageInput.addEventListener('change', function (event) {
      const file = event.target.files[0];
      const fileSize = file ? file.size / 1024 : 0; // in KB

      // Display file size in KB
      fileSizeElem.textContent = `${fileSize.toFixed(2)} KB`;

      // Show image preview if file is selected
      if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          // Display new image preview
          previewImage.src = e.target.result;
          previewImage.style.display = 'block';
          newImageLabel.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Handle delete image button (edit mode) for the existing image
  if (deleteImageBtn) {
    deleteImageBtn.addEventListener('click', function () {
      // Optionally trigger a confirmation before deleting
      if (confirm("Are you sure you want to delete this image?")) {
        deleteImageFlag.value = '1'; // Flag to delete image
        previewImage.style.display = 'none'; // Hide preview of the new image
        newImageLabel.style.display = 'none'; // Hide new image label
        existingImageContainer.style.display = 'none'; // Hide existing image
      }
    });
  }
});
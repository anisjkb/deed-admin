(function () {
  const branchSel = document.getElementById('projBranch');
  const ownerSel = document.getElementById('projOwner');
  const heroImageInput = document.getElementById('heroImageFile');
  const heroImagePreview = document.getElementById('newHeroImagePreview'); // Updated preview element
  const brochureInput = document.getElementById('brochureFile');
  const brochurePreview = document.getElementById('newBrochurePreview'); // Updated preview element
  const toggleBrochurePreviewButton = document.getElementById('toggleBrochurePreview');

  // Handling Hero Image Preview
  if (heroImageInput) {
    heroImageInput.addEventListener('change', function (event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          heroImagePreview.src = e.target.result;
          heroImagePreview.style.display = 'block'; // Show preview
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Handling Brochure Preview (e.g., displaying the file name for PDFs or images)
  if (brochureInput) {
    brochureInput.addEventListener('change', function (event) {
      const file = event.target.files[0];
      if (file) {
        // Ensure we handle only PDF or Image files
        const fileName = file.name;
        brochurePreview.style.display = 'none'; // Hide any previous previews
        brochurePreview.innerHTML = ''; // Clear any previous content

        if (file.type.includes("pdf")) {
          // For PDF Preview
          const objectTag = document.createElement('object');
          objectTag.data = URL.createObjectURL(file); // Set the PDF file URL
          objectTag.type = "application/pdf"; // Set type to pdf
          objectTag.width = "100%"; // Set width for the object to be 100% of the container
          objectTag.height = "500px"; // Set height for the object
          brochurePreview.appendChild(objectTag);
          brochurePreview.style.display = 'block'; // Show the object element
        } else if (file.type.includes("image")) {
          // For Image Preview
          const imagePreview = document.createElement('img');
          imagePreview.src = URL.createObjectURL(file);
          imagePreview.style.maxWidth = '100%';
          imagePreview.style.maxHeight = '300px';
          brochurePreview.appendChild(imagePreview);
          brochurePreview.style.display = 'block'; // Show the image preview
        } else {
          alert("Only PDF and image files are allowed for the brochure.");
        }
      }
    });
  }

  // Toggle Brochure Preview visibility
  if (toggleBrochurePreviewButton) {
    toggleBrochurePreviewButton.addEventListener('click', function () {
      if (brochurePreview.style.display === 'none' || brochurePreview.style.display === '') {
        brochurePreview.style.display = 'block'; // Show preview
      } else {
        brochurePreview.style.display = 'none'; // Hide preview
      }
    });
  }
})();
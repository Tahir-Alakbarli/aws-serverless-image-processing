const FUNCTION_URL = "https://3nl2u26uckmpof5ewrgrr3gbom0jvunu.lambda-url.eu-central-1.on.aws/";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

const imageInput = document.querySelector("#image-input");
const dropZone = document.querySelector("#drop-zone");
const previewPanel = document.querySelector("#preview-panel");
const imagePreview = document.querySelector("#image-preview");
const fileName = document.querySelector("#file-name");
const fileSize = document.querySelector("#file-size");
const uploadButton = document.querySelector("#upload-button");
const uploadStatus = document.querySelector("#upload-status");
const yearElement = document.querySelector("#year");

let selectedFile = null;

if (yearElement) {
  yearElement.textContent = new Date().getFullYear();
}

function showStatus(message, type = "") {
  uploadStatus.textContent = message;
  uploadStatus.className = `upload-status ${type}`.trim();
}

function formatBytes(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function selectFile(file) {
  showStatus("");
  selectedFile = null;
  uploadButton.disabled = true;

  if (!file) {
    previewPanel.hidden = true;
    return;
  }

  if (!ALLOWED_TYPES.has(file.type)) {
    previewPanel.hidden = true;
    showStatus("Choose a JPG, PNG, or WebP image.", "error");
    return;
  }

  if (file.size > MAX_FILE_SIZE) {
    previewPanel.hidden = true;
    showStatus("The selected image is larger than 5 MB.", "error");
    return;
  }

  selectedFile = file;
  imagePreview.src = URL.createObjectURL(file);
  fileName.textContent = file.name;
  fileSize.textContent = `${file.type} - ${formatBytes(file.size)}`;
  previewPanel.hidden = false;
  uploadButton.disabled = false;
}

imageInput.addEventListener("change", () => selectFile(imageInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
});

dropZone.addEventListener("drop", (event) => {
  selectFile(event.dataTransfer.files[0]);
});

uploadButton.addEventListener("click", async () => {
  if (!selectedFile) {
    return;
  }

  if (FUNCTION_URL.includes("PASTE_YOUR")) {
    showStatus("Add your Lambda Function URL in uploader.js first.", "error");
    return;
  }

  uploadButton.disabled = true;
  showStatus("Requesting temporary upload permission...", "loading");

  try {
    const permissionResponse = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fileName: selectedFile.name,
        fileType: selectedFile.type
      })
    });

    const permission = await permissionResponse.json();

    if (!permissionResponse.ok) {
      throw new Error(permission.message || "AWS could not create upload permission.");
    }

    showStatus("Uploading directly to the private S3 bucket...", "loading");

    const formData = new FormData();
    Object.entries(permission.fields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append("file", selectedFile);

    const uploadResponse = await fetch(permission.uploadUrl, {
      method: "POST",
      body: formData
    });

    if (!uploadResponse.ok) {
      throw new Error("S3 rejected the upload.");
    }

    showStatus(`Upload complete. Stored as ${permission.objectKey}. Processing will finish shortly.`, "success");
    selectedFile = null;
    imageInput.value = "";
    uploadButton.disabled = true;
  } catch (error) {
    console.error(error);
    showStatus(error.message || "Upload failed. Check the AWS configuration and try again.", "error");
    uploadButton.disabled = false;
  }
});

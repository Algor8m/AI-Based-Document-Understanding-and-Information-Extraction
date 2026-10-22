/**
 * IVP+AI — Frontend Orchestration & Interactive Logic
 * NMIMS-Inspired Document Intelligence System
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const healthDot = document.getElementById("health-dot");
  const healthText = document.getElementById("health-text");

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const previewCard = document.getElementById("file-preview-card");
  const previewThumb = document.getElementById("preview-thumb");
  const previewFilename = document.getElementById("preview-filename");
  const previewSize = document.getElementById("preview-size");
  const btnReplace = document.getElementById("btn-replace");
  const btnRemove = document.getElementById("btn-remove");
  const btnProcess = document.getElementById("btn-process");
  const uploadHint = document.getElementById("upload-hint");
  const errorBox = document.getElementById("error-box");
  const errorMessage = document.getElementById("error-message");

  const progressCard = document.getElementById("progress-card");
  const pipelineStatusBadge = document.getElementById("pipeline-status-badge");
  const pipelineMessage = document.getElementById("pipeline-message");
  const steps = [
    document.getElementById("step-1"),
    document.getElementById("step-2"),
    document.getElementById("step-3"),
    document.getElementById("step-4"),
    document.getElementById("step-5"),
  ];

  const resultsContainer = document.getElementById("results-container");
  const warningsBanner = document.getElementById("warnings-banner");
  const btnReset = document.getElementById("btn-reset");

  const overviewList = document.getElementById("overview-list");
  const badgeProcessingStatus = document.getElementById("badge-processing-status");
  const classificationList = document.getElementById("classification-list");
  const badgeClassificationConfidence = document.getElementById("badge-classification-confidence");
  const factsList = document.getElementById("facts-list");
  const reasoningList = document.getElementById("reasoning-list");

  const ocrTextView = document.getElementById("ocr-text-view");
  const wordCount = document.getElementById("word-count");
  const charCount = document.getElementById("char-count");
  const btnCopyText = document.getElementById("btn-copy-text");
  const btnDownloadText = document.getElementById("btn-download-text");

  const stagesCountBadge = document.getElementById("stages-count-badge");
  const imgCompareOrig = document.getElementById("img-compare-orig");
  const imgCompareProc = document.getElementById("img-compare-proc");
  const stagesGallery = document.getElementById("stages-gallery");

  const jsonView = document.getElementById("json-view");
  const btnCopyJson = document.getElementById("btn-copy-json");
  const btnDownloadJson = document.getElementById("btn-download-json");

  const imageModal = document.getElementById("image-modal");
  const modalImg = document.getElementById("modal-img");
  const modalCaption = document.getElementById("modal-caption");
  const modalClose = document.getElementById("modal-close");

  let selectedFile = null;
  let previewUrl = null;
  let lastResult = null;

  // ========================================================================
  // 1. Live System Health Check
  // ========================================================================
  async function checkHealth() {
    try {
      const resp = await fetch("/api/v1/health", { cache: "no-store" });
      if (resp.ok) {
        healthDot.className = "health-dot online";
        healthText.textContent = "System Online";
      } else {
        throw new Error("Service degraded");
      }
    } catch {
      healthDot.className = "health-dot offline";
      healthText.textContent = "System Offline";
    }
  }
  checkHealth();
  setInterval(checkHealth, 30000);

  // ========================================================================
  // 2. File Selection & Drag-and-Drop
  // ========================================================================
  function selectFile(file) {
    if (!file) return;

    // Validate MIME / extension
    const validTypes = ["image/png", "image/jpeg", "image/jpg"];
    const ext = file.name.split(".").pop().toLowerCase();
    if (!validTypes.includes(file.type) && !["png", "jpg", "jpeg"].includes(ext)) {
      showError("Unsupported file format. Please upload a PNG or JPEG document.");
      return;
    }

    // Validate size (10 MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      showError("File too large. Maximum supported size is 10 MB.");
      return;
    }

    clearError();
    selectedFile = file;

    // Revoke previous object URL if any
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);

    previewThumb.src = previewUrl;
    previewFilename.textContent = file.name;
    previewSize.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;

    dropzone.style.display = "none";
    previewCard.style.display = "flex";
    btnProcess.disabled = false;
    uploadHint.textContent = "Document loaded. Click Process Document to execute pipeline.";
  }

  function removeFile() {
    selectedFile = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    fileInput.value = "";
    previewCard.style.display = "none";
    dropzone.style.display = "flex";
    btnProcess.disabled = true;
    uploadHint.textContent = "Select a file to begin document understanding.";
    clearError();
  }

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      selectFile(e.target.files[0]);
    }
  });

  btnReplace.addEventListener("click", () => fileInput.click());
  btnRemove.addEventListener("click", removeFile);

  // Drag & drop handlers
  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selectFile(e.dataTransfer.files[0]);
    }
  });

  // ========================================================================
  // 3. Pipeline Progress State Management
  // ========================================================================
  function setPipelineStep(stepIndex, message, isError = false) {
    progressCard.style.display = "block";
    pipelineMessage.textContent = message;

    if (isError) {
      pipelineStatusBadge.className = "badge badge-red";
      pipelineStatusBadge.textContent = "Failed";
    } else if (stepIndex === 5) {
      pipelineStatusBadge.className = "badge badge-green";
      pipelineStatusBadge.textContent = "Completed";
    } else {
      pipelineStatusBadge.className = "badge badge-amber";
      pipelineStatusBadge.textContent = "In Progress";
    }

    steps.forEach((step, idx) => {
      step.classList.remove("active", "completed");
      if (idx + 1 < stepIndex) {
        step.classList.add("completed");
      } else if (idx + 1 === stepIndex) {
        if (isError) {
          step.classList.add("active");
        } else if (stepIndex === 5) {
          step.classList.add("completed");
        } else {
          step.classList.add("active");
        }
      }
    });
  }

  // ========================================================================
  // 4. Document Processing Execution
  // ========================================================================
  btnProcess.addEventListener("click", async () => {
    if (!selectedFile) return;

    clearError();
    resultsContainer.style.display = "none";
    btnProcess.disabled = true;

    setPipelineStep(1, "Uploading document to gateway...");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      // Simulate real step updates while waiting for synchronous pipeline response
      setTimeout(() => {
        if (btnProcess.disabled) setPipelineStep(2, "Applying EXIF, grayscale, upscaling & contrast...");
      }, 400);

      setTimeout(() => {
        if (btnProcess.disabled) setPipelineStep(3, "Executing Tesseract OCR extraction...");
      }, 1000);

      setTimeout(() => {
        if (btnProcess.disabled) setPipelineStep(4, "AI Engine: Classifying & evaluating forward chaining...");
      }, 1800);

      const resp = await fetch("/api/v1/documents/process", {
        method: "POST",
        body: formData,
      });

      const payload = await resp.json();

      if (!resp.ok) {
        const errDetail = payload.detail?.error || payload.error || {};
        const code = errDetail.code ? `[${errDetail.code}] ` : "";
        const msg = errDetail.message || "Document processing failed.";
        throw new Error(`${code}${msg}`);
      }

      setPipelineStep(5, "Processing completed successfully.");
      lastResult = payload;
      renderResults(payload);

      // Scroll smoothly to results
      resultsContainer.style.display = "block";
      resultsContainer.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
      setPipelineStep(4, "Pipeline execution halted due to an error.", true);
      showError(err.message || "An unexpected processing error occurred.");
    } finally {
      btnProcess.disabled = false;
    }
  });

  // ========================================================================
  // 5. Render Processing Results
  // ========================================================================
  function renderResults(result) {
    const data = result.data || {};
    const prep = result.prepared_document || {};
    const meta = prep.metadata || {};
    const facts = data.extracted_facts || {};
    const classification = data.classification || {};
    const stages = result.intermediate_images || [];

    // --- Overview ---
    badgeProcessingStatus.className = "badge badge-green";
    badgeProcessingStatus.textContent = result.status?.toUpperCase() || "SUCCESS";

    renderKV(overviewList, {
      "Document ID": result.document_id || "N/A",
      "Original File": prep.source?.filename || selectedFile?.name || "N/A",
      "Dimensions": meta.image_width ? `${meta.image_width} × ${meta.image_height} px` : "N/A",
      "OCR Engine": meta.ocr_engine ? `${meta.ocr_engine} (PSM 3)` : "tesseract",
      "OCR Status": result.processing?.image_processing || "completed",
      "AI Status": result.processing?.ai_extraction || "completed",
      "Total Processing Time": meta.processing_duration_ms ? `${meta.processing_duration_ms} ms` : "N/A",
    });

    // --- Classification ---
    const conf = classification.confidence || "unknown";
    badgeClassificationConfidence.textContent = `${conf.toUpperCase()} CONFIDENCE`;
    badgeClassificationConfidence.className = conf === "high" || conf === "medium" ? "badge badge-green" : "badge badge-amber";

    renderKV(classificationList, {
      "Document Type": data.document_type ? data.document_type.replace(/_/g, " ").toUpperCase() : "UNKNOWN",
      "Confidence Level": conf,
      "Classification Method": classification.classification_method || "keyword_rules",
      "Has Contact Method": data.inferred_facts?.has_contact_method ? "Yes" : "No",
      "Contact Info Present": data.inferred_facts?.contact_information_present ? "Yes" : "No",
    });

    // --- Extracted Facts ---
    renderKV(factsList, {
      "Invoice Number": facts.invoice_number ? facts.invoice_number : "(Not detected)",
      "Invoice Date": facts.invoice_date ? facts.invoice_date : "(Not detected)",
      "Amount Due": facts.amount_due ? `INR / USD ${facts.amount_due}` : "(Not detected)",
      "Emails": facts.emails && facts.emails.length ? facts.emails.join(", ") : "(None)",
      "Phone Numbers": facts.phone_numbers && facts.phone_numbers.length ? facts.phone_numbers.join(", ") : "(None)",
      "Dates Identified": facts.dates && facts.dates.length ? facts.dates.join(", ") : "(None)",
    });

    // --- Inferences & Rules ---
    const reasoning = data.reasoning || [];
    if (reasoning.length > 0) {
      const reasoningItems = {};
      reasoning.forEach((r, i) => {
        const conclusions = Object.entries(r.conclusion || {})
          .map(([k, v]) => `${k}=${v}`)
          .join(", ");
        reasoningItems[`Rule ${i + 1}: ${r.rule}`] = `${r.explanation} (→ ${conclusions})`;
      });
      renderKV(reasoningList, reasoningItems);
    } else {
      renderKV(reasoningList, {
        "Fired Rules": "(No forward-chaining rules triggered for this document)",
      });
    }

    // --- Extracted Text ---
    const text = prep.text || "";
    ocrTextView.textContent = text || "(No readable text detected in document image.)";
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    wordCount.textContent = `${words} words`;
    charCount.textContent = `${text.length} characters`;

    // --- Warnings ---
    const warnings = result.warnings || prep.warnings || [];
    if (warnings.length > 0) {
      warningsBanner.style.display = "block";
      warningsBanner.innerHTML = `<strong>Warnings:</strong> ${warnings.map((w) => `[${w.code}] ${w.message}`).join("; ")}`;
    } else {
      warningsBanner.style.display = "none";
    }

    // --- Intermediate Images & Comparison ---
    stagesCountBadge.textContent = `${stages.length} Stages`;

    if (result.original_image_url) {
      imgCompareOrig.src = result.original_image_url;
      imgCompareOrig.onclick = () => openModal(result.original_image_url, "Original Document (Raw Upload)");
    }
    if (result.processed_image_url) {
      imgCompareProc.src = result.processed_image_url;
      imgCompareProc.onclick = () => openModal(result.processed_image_url, "Final Preprocessed Image Supplied to OCR Engine");
    }

    // Gallery Cards
    stagesGallery.innerHTML = "";
    stages.forEach((stg) => {
      const card = document.createElement("div");
      card.className = `stage-card ${stg.is_ocr_input ? "ocr-input" : ""}`;

      card.innerHTML = `
        <div class="stage-img-wrap" title="Click to view full size">
          <img class="stage-img" src="${stg.image_url}" alt="${stg.title}">
        </div>
        <div class="stage-body">
          <div class="stage-header">
            <div class="stage-title">${stg.title}</div>
            ${stg.is_ocr_input ? '<span class="badge badge-red">OCR INPUT</span>' : ""}
          </div>
          <div class="stage-desc">${stg.description || ""}</div>
          <div class="stage-dims">${stg.dimensions ? `${stg.dimensions[0]} × ${stg.dimensions[1]} px` : ""}</div>
        </div>
      `;

      card.querySelector(".stage-img-wrap").addEventListener("click", () => {
        openModal(stg.image_url, `${stg.title} — ${stg.description || ""}`);
      });

      stagesGallery.appendChild(card);
    });

    // --- JSON Viewer ---
    jsonView.textContent = JSON.stringify(result, null, 2);
  }

  function renderKV(container, data) {
    container.innerHTML = "";
    Object.entries(data).forEach(([key, val]) => {
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = key;
      dd.textContent = String(val);
      container.append(dt, dd);
    });
  }

  // ========================================================================
  // 6. Modal Image Viewer
  // ========================================================================
  function openModal(imgSrc, caption) {
    modalImg.src = imgSrc;
    modalCaption.textContent = caption || "";
    imageModal.classList.add("open");
  }

  function closeModal() {
    imageModal.classList.remove("open");
    modalImg.src = "";
  }

  modalClose.addEventListener("click", closeModal);
  imageModal.addEventListener("click", (e) => {
    if (e.target === imageModal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && imageModal.classList.contains("open")) {
      closeModal();
    }
  });

  // ========================================================================
  // 7. Copy and Download Buttons
  // ========================================================================
  btnCopyText.addEventListener("click", async () => {
    const text = ocrTextView.textContent || "";
    if (!text) return;
    await navigator.clipboard.writeText(text);
    const orig = btnCopyText.textContent;
    btnCopyText.textContent = "Copied!";
    setTimeout(() => { btnCopyText.textContent = orig; }, 1500);
  });

  btnDownloadText.addEventListener("click", () => {
    const text = ocrTextView.textContent || "";
    downloadFile(text, "extracted_text.txt", "text/plain");
  });

  btnCopyJson.addEventListener("click", async () => {
    if (!lastResult) return;
    await navigator.clipboard.writeText(JSON.stringify(lastResult, null, 2));
    const orig = btnCopyJson.textContent;
    btnCopyJson.textContent = "Copied!";
    setTimeout(() => { btnCopyJson.textContent = orig; }, 1500);
  });

  btnDownloadJson.addEventListener("click", () => {
    if (!lastResult) return;
    const jsonStr = JSON.stringify(lastResult, null, 2);
    downloadFile(jsonStr, "ivp_result.json", "application/json");
  });

  function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ========================================================================
  // 8. Reset Application State
  // ========================================================================
  btnReset.addEventListener("click", () => {
    removeFile();
    resultsContainer.style.display = "none";
    progressCard.style.display = "none";
    lastResult = null;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // Hero section jump
  document.getElementById("btn-hero-analyse").addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById("analysis").scrollIntoView({ behavior: "smooth" });
  });

  // ========================================================================
  // 9. Error Handling
  // ========================================================================
  function showError(msg) {
    errorMessage.textContent = msg;
    errorBox.style.display = "flex";
  }

  function clearError() {
    errorMessage.textContent = "";
    errorBox.style.display = "none";
  }
});

/**
 * Reliable Multi-Client File Transfer System - Dashboard Controller
 * Handles TCP Server Status, Real-Time File Management, Transfer Pipeline,
 * SHA-256 Verification feedback, and Audit History.
 */

// Application State
const state = {
    files: [],
    transfers: [],
    serverOnline: false,
    selectedFile: null,
    pendingDeleteFilename: null,
    historyFilterOp: 'all',
    fileSearchQuery: '',
    historySearchQuery: '',
    fileSortBy: 'name-asc'
};

// ==========================================================================
// Utility Functions
// ==========================================================================

function formatFileSize(bytes) {
    if (bytes === 0) return "0 B";
    if (isNaN(bytes) || bytes < 0) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const size = bytes / Math.pow(1024, index);
    return `${size.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    const div = document.createElement("div");
    div.textContent = String(value);
    return div.innerHTML;
}

function escapeJs(value) {
    return String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<svg class="toast-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else if (type === 'error') {
        iconSvg = `<svg class="toast-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else {
        iconSvg = `<svg class="toast-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
        ${iconSvg}
        <span>${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function copyToClipboard(text, event) {
    if (event) event.stopPropagation();

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('SHA-256 hash copied to clipboard', 'success');
        }).catch(() => {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        showToast('SHA-256 hash copied to clipboard', 'success');
    } catch (err) {
        showToast('Unable to copy hash', 'error');
    }
    document.body.removeChild(textArea);
}

// ==========================================================================
// Server Status & Real-time Metrics
// ==========================================================================

async function loadServerStatus() {
    const badge = document.getElementById("serverStatusBadge");
    const statusText = document.getElementById("serverStatusText");
    const metricStatus = document.getElementById("metricServerStatus");
    const metricDetail = document.getElementById("metricServerDetail");

    try {
        const response = await fetch("/api/status");
        if (!response.ok) throw new Error("Status check failed");

        const data = await response.json();
        state.serverOnline = data.online;

        if (data.online) {
            badge.className = "status-badge online";
            statusText.textContent = `TCP Server Online (${data.host}:${data.port})`;
            metricStatus.textContent = "Online";
            metricStatus.className = "metric-value text-success";
            metricDetail.textContent = `${data.host}:${data.port} \u2022 ${data.latency_ms}ms latency`;
        } else {
            badge.className = "status-badge offline";
            statusText.textContent = `TCP Server Offline (${data.host}:${data.port})`;
            metricStatus.textContent = "Offline";
            metricStatus.className = "metric-value text-danger";
            metricDetail.textContent = "Waiting for server to start...";
        }

        // Update counts from real server storage & history
        if (data.total_storage !== undefined) {
            document.getElementById("totalStorage").textContent = formatFileSize(data.total_storage);
        }
        if (data.total_transfers !== undefined) {
            document.getElementById("transferCount").textContent = data.total_transfers;
            document.getElementById("successCount").textContent = data.successful_transfers;
            document.getElementById("successRate").textContent = `${data.success_rate}%`;
        }

    } catch (err) {
        state.serverOnline = false;
        badge.className = "status-badge offline";
        statusText.textContent = "TCP Server Disconnected";
        metricStatus.textContent = "Offline";
        metricStatus.className = "metric-value text-danger";
        metricDetail.textContent = "Server connection refused";
    }
}

// ==========================================================================
// Server Files Management
// ==========================================================================

async function loadFiles() {
    const tableBody = document.getElementById("filesTableBody");

    try {
        const response = await fetch("/api/files");
        if (!response.ok) throw new Error("Failed to load server files.");

        const files = await response.json();
        state.files = files;

        document.getElementById("fileCount").textContent = files.length;

        let totalBytes = files.reduce((acc, f) => acc + (f.size || 0), 0);
        document.getElementById("totalStorage").textContent = formatFileSize(totalBytes);

        renderFilesTable();

    } catch (error) {
        console.error("loadFiles error:", error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="4" class="state-cell">
                    <div class="empty-state-content">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <strong>Unable to connect to server files repository</strong>
                        <span>Verify that the TCP backend server is running.</span>
                    </div>
                </td>
            </tr>
        `;
    }
}

function renderFilesTable() {
    const tableBody = document.getElementById("filesTableBody");
    tableBody.innerHTML = "";

    let filtered = [...state.files];

    // Filter by Search Query
    if (state.fileSearchQuery.trim()) {
        const q = state.fileSearchQuery.toLowerCase().trim();
        filtered = filtered.filter(f => f.filename.toLowerCase().includes(q));
    }

    // Sort Files
    filtered.sort((a, b) => {
        switch (state.fileSortBy) {
            case 'name-asc':
                return a.filename.localeCompare(b.filename);
            case 'name-desc':
                return b.filename.localeCompare(a.filename);
            case 'size-desc':
                return b.size - a.size;
            case 'size-asc':
                return a.size - b.size;
            case 'date-desc':
                return (b.modified || 0) - (a.modified || 0);
            default:
                return a.filename.localeCompare(b.filename);
        }
    });

    if (filtered.length === 0) {
        const msg = state.fileSearchQuery.trim()
            ? `No files match search "${escapeHtml(state.fileSearchQuery)}"`
            : "No files currently stored on the server.";
        const submsg = state.fileSearchQuery.trim()
            ? "Try a different search keyword."
            : "Upload a file using the panel above to begin.";

        tableBody.innerHTML = `
            <tr>
                <td colspan="4" class="state-cell">
                    <div class="empty-state-content">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <strong>${msg}</strong>
                        <span>${submsg}</span>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    filtered.forEach(file => {
        const row = document.createElement("tr");

        const ext = file.extension ? file.extension.toUpperCase() : (file.filename.split('.').pop() || 'FILE').toUpperCase();

        row.innerHTML = `
            <td>
                <div class="file-cell">
                    <span class="file-badge">${escapeHtml(ext.slice(0, 4))}</span>
                    <div>
                        <div class="file-name-title">${escapeHtml(file.filename)}</div>
                    </div>
                </div>
            </td>
            <td>
                <strong>${formatFileSize(file.size)}</strong>
            </td>
            <td>
                <div class="hash-wrapper">
                    <code class="hash-code" title="${escapeHtml(file.sha256)}">${escapeHtml(file.sha256)}</code>
                    <button class="btn-copy" onclick="copyToClipboard('${escapeJs(file.sha256)}', event)" title="Copy SHA-256 hash" aria-label="Copy SHA-256 hash">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                    </button>
                </div>
            </td>
            <td>
                <div class="actions-cell">
                    <button class="btn btn-sm btn-action-download" onclick="downloadFile('${escapeJs(file.filename)}')" title="Download file via reliable TCP">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>Download</span>
                    </button>
                    <button class="btn btn-sm btn-action-delete" onclick="promptDeleteFile('${escapeJs(file.filename)}')" title="Delete file from server">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                        <span>Delete</span>
                    </button>
                </div>
            </td>
        `;

        tableBody.appendChild(row);
    });
}

// ==========================================================================
// Transfer History & Protocol Audit Log
// ==========================================================================

async function loadTransfers() {
    const tableBody = document.getElementById("transfersTableBody");

    try {
        const response = await fetch("/api/transfers");
        if (!response.ok) throw new Error("Failed to load transfer history.");

        const transfers = await response.json();
        state.transfers = transfers;

        document.getElementById("transferCount").textContent = transfers.length;

        const successful = transfers.filter(t => t.status === "SUCCESS").length;
        document.getElementById("successCount").textContent = successful;

        const rate = transfers.length > 0 ? ((successful / transfers.length) * 100).toFixed(1) : 100.0;
        document.getElementById("successRate").textContent = `${rate}%`;

        renderTransfersTable();

    } catch (error) {
        console.error("loadTransfers error:", error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="state-cell">
                    <div class="empty-state-content">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <strong>Unable to load transfer history</strong>
                        <span>Could not read transfer audit log.</span>
                    </div>
                </td>
            </tr>
        `;
    }
}

function renderTransfersTable() {
    const tableBody = document.getElementById("transfersTableBody");
    tableBody.innerHTML = "";

    let list = [...state.transfers].reverse();

    // Filter by Operation
    if (state.historyFilterOp !== 'all') {
        list = list.filter(t => (t.operation || '').toUpperCase() === state.historyFilterOp);
    }

    // Filter by Search Query
    if (state.historySearchQuery.trim()) {
        const q = state.historySearchQuery.toLowerCase().trim();
        list = list.filter(t =>
            (t.filename && t.filename.toLowerCase().includes(q)) ||
            (t.client && t.client.toLowerCase().includes(q)) ||
            (t.status && t.status.toLowerCase().includes(q))
        );
    }

    if (list.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="state-cell">
                    <div class="empty-state-content">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <polyline points="17 1 21 5 17 9"></polyline>
                            <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
                            <polyline points="7 23 3 19 7 15"></polyline>
                            <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
                        </svg>
                        <strong>No transfer history found</strong>
                        <span>No records matching the selected filter criteria.</span>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    list.forEach(t => {
        const row = document.createElement("tr");

        const isUpload = (t.operation || '').toUpperCase() === 'UPLOAD';
        const opBadge = isUpload
            ? `<span class="tag-badge tag-op-upload">UPLOAD</span>`
            : `<span class="tag-badge tag-op-download">DOWNLOAD</span>`;

        const isSuccess = t.status === 'SUCCESS';
        const statusBadge = isSuccess
            ? `<span class="tag-badge tag-success">&#10003; SUCCESS</span>`
            : `<span class="tag-badge tag-danger">&#10007; ${escapeHtml(t.status)}</span>`;

        row.innerHTML = `
            <td style="white-space: nowrap; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);">${escapeHtml(t.timestamp)}</td>
            <td><code>${escapeHtml(t.client)}</code></td>
            <td>${opBadge}</td>
            <td style="font-weight: 500;">${escapeHtml(t.filename)}</td>
            <td>${escapeHtml(t.size)}</td>
            <td>${escapeHtml(t.duration)}</td>
            <td style="font-weight: 600; color: var(--brand-accent);">${escapeHtml(t.speed)}</td>
            <td>${statusBadge}</td>
        `;

        tableBody.appendChild(row);
    });
}

// ==========================================================================
// Upload Pipeline
// ==========================================================================

function handleFileSelection(file) {
    if (!file) return;

    state.selectedFile = file;

    const dropZone = document.getElementById("dropZone");
    const preview = document.getElementById("fileSelectionPreview");
    const extBadge = document.getElementById("selectedFileExt");
    const nameLabel = document.getElementById("selectedFileName");
    const sizeLabel = document.getElementById("selectedFileSize");

    const ext = (file.name.split('.').pop() || 'FILE').toUpperCase().slice(0, 4);
    extBadge.textContent = ext;
    nameLabel.textContent = file.name;
    sizeLabel.textContent = formatFileSize(file.size);

    dropZone.classList.add("hidden");
    preview.classList.remove("hidden");
}

function clearFileSelection() {
    state.selectedFile = null;
    const input = document.getElementById("fileInput");
    if (input) input.value = "";

    const dropZone = document.getElementById("dropZone");
    const preview = document.getElementById("fileSelectionPreview");
    const pipeline = document.getElementById("transferPipeline");

    preview.classList.add("hidden");
    pipeline.classList.add("hidden");
    dropZone.classList.remove("hidden");
}

function updatePipelineStep(stepIndex, statusText) {
    const steps = [
        document.getElementById("stepHandshake"),
        document.getElementById("stepMetadata"),
        document.getElementById("stepStreaming"),
        document.getElementById("stepIntegrity"),
        document.getElementById("stepCommit")
    ];

    const fill = document.getElementById("pipelineProgressFill");
    const statusLabel = document.getElementById("uploadStatusText");

    steps.forEach((el, idx) => {
        if (!el) return;
        el.classList.remove("active", "completed");
        if (idx < stepIndex) {
            el.classList.add("completed");
        } else if (idx === stepIndex) {
            el.classList.add("active");
        }
    });

    const percent = Math.min(100, Math.max(10, ((stepIndex + 1) / steps.length) * 100));
    if (fill) fill.style.width = `${percent}%`;
    if (statusLabel) statusLabel.textContent = statusText;
}

async function uploadFile() {
    if (!state.selectedFile) {
        showToast("Please choose a file to upload first.", "error");
        return;
    }

    const uploadBtn = document.getElementById("uploadButton");
    const cancelBtn = document.getElementById("cancelSelectBtn");
    const pipeline = document.getElementById("transferPipeline");

    uploadBtn.disabled = true;
    cancelBtn.disabled = true;
    pipeline.classList.remove("hidden");

    // Pipeline Step 1: Handshake
    updatePipelineStep(0, "Initiating TCP Socket Handshake (HELLO \u2192 HELLO_ACK)...");

    const formData = new FormData();
    formData.append("file", state.selectedFile);

    try {
        // Step 2: Metadata Negotiation
        setTimeout(() => updatePipelineStep(1, "Negotiating UPLOAD parameters & acquiring per-file lock..."), 300);

        // Step 3: TCP Packet Streaming
        setTimeout(() => updatePipelineStep(2, `Streaming 4096-byte TCP chunks (${formatFileSize(state.selectedFile.size)})...`), 700);

        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        // Step 4: SHA-256 Verification
        updatePipelineStep(3, "Server performing SHA-256 integrity verification...");

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Upload failed on the TCP server.");
        }

        // Step 5: Atomic Replace Commit
        updatePipelineStep(4, "SHA-256 verified! Atomic replacement completed.");

        showToast(`Successfully uploaded "${result.filename}" with verified SHA-256 checksum!`, "success");

        setTimeout(() => {
            clearFileSelection();
            loadDashboard();
        }, 1200);

    } catch (error) {
        console.error("Upload error:", error);
        showToast(error.message || "Upload failed. Check TCP server connection.", "error");

        const statusLabel = document.getElementById("uploadStatusText");
        if (statusLabel) {
            statusLabel.textContent = `Upload failed: ${error.message}`;
            statusLabel.style.color = "var(--danger)";
        }
    } finally {
        uploadBtn.disabled = false;
        cancelBtn.disabled = false;
    }
}

// ==========================================================================
// Download Handling
// ==========================================================================

function downloadFile(filename) {
    if (!filename) return;

    showToast(`Initiating reliable TCP download for "${filename}"...`, "info");

    const url = "/api/download/" + encodeURIComponent(filename);

    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Refresh transfers table after a brief moment to show download entry
    setTimeout(() => {
        loadTransfers();
        loadServerStatus();
    }, 1500);
}

// ==========================================================================
// Delete Handling with Native Modal Dialog
// ==========================================================================

function promptDeleteFile(filename) {
    state.pendingDeleteFilename = filename;
    const dialog = document.getElementById("deleteConfirmDialog");
    const targetLabel = document.getElementById("deleteTargetFilename");

    if (targetLabel) targetLabel.textContent = `"${filename}"`;
    if (dialog) dialog.showModal();
}

async function confirmDeleteFile() {
    const filename = state.pendingDeleteFilename;
    const dialog = document.getElementById("deleteConfirmDialog");
    const confirmBtn = document.getElementById("confirmDeleteBtn");

    if (!filename) return;

    confirmBtn.disabled = true;
    confirmBtn.textContent = "Deleting...";

    try {
        const response = await fetch("/api/delete/" + encodeURIComponent(filename), {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "File could not be deleted from server.");
        }

        if (dialog) dialog.close();
        showToast(`File "${filename}" deleted successfully.`, "success");
        await loadDashboard();

    } catch (error) {
        console.error("Delete error:", error);
        showToast(error.message || "Delete failed. Check server connection.", "error");
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Confirm Delete";
        state.pendingDeleteFilename = null;
    }
}

// ==========================================================================
// Main Dashboard Refresh
// ==========================================================================

async function loadDashboard() {
    const refreshBtn = document.getElementById("refreshButton");
    const spinIcon = refreshBtn ? refreshBtn.querySelector(".spin-icon") : null;

    if (spinIcon) spinIcon.classList.add("spinning");

    const errorBanner = document.getElementById("errorMessage");
    if (errorBanner) errorBanner.classList.add("hidden");

    try {
        await Promise.all([
            loadServerStatus(),
            loadFiles(),
            loadTransfers()
        ]);
    } catch (err) {
        console.error("Dashboard reload error:", err);
    } finally {
        if (spinIcon) {
            setTimeout(() => spinIcon.classList.remove("spinning"), 400);
        }
    }
}

// ==========================================================================
// Event Listeners & Initialization
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    // Initial Load
    loadDashboard();

    // Auto status poll every 10 seconds to keep connection pill fresh
    setInterval(loadServerStatus, 10000);

    // Refresh Button
    const refreshBtn = document.getElementById("refreshButton");
    if (refreshBtn) refreshBtn.addEventListener("click", loadDashboard);

    // File Input & Drag and Drop Zone
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => fileInput.click());

        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });

        dropZone.addEventListener("dragleave", () => {
            dropZone.classList.remove("dragover");
        });

        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files.length > 0) {
                handleFileSelection(fileInput.files[0]);
            }
        });
    }

    // Cancel Selection Button
    const cancelSelectBtn = document.getElementById("cancelSelectBtn");
    if (cancelSelectBtn) cancelSelectBtn.addEventListener("click", clearFileSelection);

    // Upload Action Button
    const uploadBtn = document.getElementById("uploadButton");
    if (uploadBtn) uploadBtn.addEventListener("click", uploadFile);

    // Search and Sort Files
    const fileSearchInput = document.getElementById("fileSearchInput");
    if (fileSearchInput) {
        fileSearchInput.addEventListener("input", (e) => {
            state.fileSearchQuery = e.target.value;
            renderFilesTable();
        });
    }

    const fileSortSelect = document.getElementById("fileSortSelect");
    if (fileSortSelect) {
        fileSortSelect.addEventListener("change", (e) => {
            state.fileSortBy = e.target.value;
            renderFilesTable();
        });
    }

    // History Filters
    const pillButtons = document.querySelectorAll(".pill-btn");
    pillButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            pillButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.historyFilterOp = btn.getAttribute("data-filter-op") || 'all';
            renderTransfersTable();
        });
    });

    const transferSearchInput = document.getElementById("transferSearchInput");
    if (transferSearchInput) {
        transferSearchInput.addEventListener("input", (e) => {
            state.historySearchQuery = e.target.value;
            renderTransfersTable();
        });
    }

    // Delete Confirmation Modal
    const deleteModal = document.getElementById("deleteConfirmDialog");
    const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");

    if (cancelDeleteBtn && deleteModal) {
        cancelDeleteBtn.addEventListener("click", () => {
            deleteModal.close();
            state.pendingDeleteFilename = null;
        });
    }

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", confirmDeleteFile);
    }

    if (deleteModal) {
        // Close modal when clicking outside on backdrop
        deleteModal.addEventListener("click", (e) => {
            const rect = deleteModal.getBoundingClientRect();
            const isInDialog = (rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
                                rect.left <= e.clientX && e.clientX <= rect.left + rect.width);
            if (!isInDialog) {
                deleteModal.close();
                state.pendingDeleteFilename = null;
            }
        });
    }

    // Keyboard Shortcuts (R to refresh)
    document.addEventListener("keydown", (e) => {
        if ((e.key === "r" || e.key === "R") && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
            e.preventDefault();
            loadDashboard();
        }
    });
});
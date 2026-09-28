async function loadFiles() {

    const tableBody =
        document.getElementById(
            "filesTableBody"
        );

    try {

        const response =
            await fetch("/api/files");


        if (!response.ok) {
            throw new Error(
                "Failed to load server files."
            );
        }


        const files =
            await response.json();


        tableBody.innerHTML = "";


        let totalStorage = 0;


        document.getElementById(
            "fileCount"
        ).textContent = files.length;


        if (files.length === 0) {

            document.getElementById(
                "totalStorage"
            ).textContent = "0 B";


            tableBody.innerHTML = `
                <tr>
                    <td
                        colspan="4"
                        class="empty"
                    >
                        No files available on the server.
                    </td>
                </tr>
            `;

            return;
        }


        files.forEach(file => {

            totalStorage += file.size;


            const row =
                document.createElement("tr");


            row.innerHTML = `
                <td>
                    ${escapeHtml(
                        file.filename
                    )}
                </td>

                <td>
                    ${formatFileSize(
                        file.size
                    )}
                </td>

                <td class="hash">
                    ${escapeHtml(
                        file.sha256
                    )}
                </td>

                <td class="actions">

                    <button
                        class="download-button"
                        onclick="downloadFile(
                            '${escapeJs(
                                file.filename
                            )}'
                        )"
                    >
                        Download
                    </button>

                    <button
                        class="delete-button"
                        onclick="deleteFile(
                            '${escapeJs(
                                file.filename
                            )}'
                        )"
                    >
                        Delete
                    </button>

                </td>
            `;


            tableBody.appendChild(row);

        });


        document.getElementById(
            "totalStorage"
        ).textContent =
            formatFileSize(totalStorage);


    } catch (error) {

        tableBody.innerHTML = `
            <tr>
                <td
                    colspan="4"
                    class="empty"
                >
                    Unable to load server files.
                </td>
            </tr>
        `;

        throw error;
    }
}


async function loadTransfers() {

    const tableBody =
        document.getElementById(
            "transfersTableBody"
        );


    try {

        const response =
            await fetch("/api/transfers");


        if (!response.ok) {
            throw new Error(
                "Failed to load transfer history."
            );
        }


        const transfers =
            await response.json();


        tableBody.innerHTML = "";


        document.getElementById(
            "transferCount"
        ).textContent =
            transfers.length;


        const successfulTransfers =
            transfers.filter(
                transfer =>
                    transfer.status === "SUCCESS"
            );


        document.getElementById(
            "successCount"
        ).textContent =
            successfulTransfers.length;


        if (transfers.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td
                        colspan="8"
                        class="empty"
                    >
                        No transfer history available.
                    </td>
                </tr>
            `;

            return;
        }


        transfers
            .slice()
            .reverse()
            .forEach(transfer => {

                const row =
                    document.createElement("tr");


                row.innerHTML = `
                    <td>
                        ${escapeHtml(
                            transfer.timestamp
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.client
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.operation
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.filename
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.size
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.duration
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.speed
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            transfer.status
                        )}
                    </td>
                `;


                tableBody.appendChild(row);

            });


    } catch (error) {

        tableBody.innerHTML = `
            <tr>
                <td
                    colspan="8"
                    class="empty"
                >
                    Unable to load transfer history.
                </td>
            </tr>
        `;

        throw error;
    }
}


async function uploadFile() {

    const input =
        document.getElementById(
            "fileInput"
        );

    const status =
        document.getElementById(
            "uploadStatus"
        );


    if (!input.files.length) {

        status.textContent =
            "Please select a file first.";

        return;
    }


    const file =
        input.files[0];


    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    status.textContent =
        "Uploading file...";


    try {

        const response =
            await fetch(
                "/api/upload",
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        if (!result.success) {

            status.textContent =
                result.message ||
                "Upload failed.";

            return;
        }


        status.textContent =
            "Upload completed successfully.";


        input.value = "";


        await loadDashboard();


    } catch (error) {

        console.error(error);

        status.textContent =
            "Upload failed. Check the server connection.";
    }
}


function downloadFile(filename) {

    const url =
        "/api/download/" +
        encodeURIComponent(filename);


    window.location.href = url;
}


async function deleteFile(filename) {

    const confirmed =
        confirm(
            `Are you sure you want to delete "${filename}"?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                "/api/delete/" +
                encodeURIComponent(filename),
                {
                    method: "DELETE"
                }
            );


        const result =
            await response.json();


        if (!result.success) {

            alert(
                result.message ||
                "Delete failed."
            );

            return;
        }


        await loadDashboard();


    } catch (error) {

        console.error(error);

        alert(
            "Delete failed. Check the server connection."
        );
    }
}


function formatFileSize(bytes) {

    if (bytes === 0) {
        return "0 B";
    }


    const units = [
        "B",
        "KB",
        "MB",
        "GB"
    ];


    const index =
        Math.floor(
            Math.log(bytes) /
            Math.log(1024)
        );


    const size =
        bytes /
        Math.pow(1024, index);


    return (
        size.toFixed(2) +
        " " +
        units[index]
    );
}


function escapeHtml(value) {

    const div =
        document.createElement("div");


    div.textContent =
        String(value);


    return div.innerHTML;
}


function escapeJs(value) {

    return String(value)
        .replace(
            /\\/g,
            "\\\\"
        )
        .replace(
            /'/g,
            "\\'"
        );
}


async function loadDashboard() {

    const errorMessage =
        document.getElementById(
            "errorMessage"
        );


    errorMessage.style.display =
        "none";


    try {

        await Promise.all([
            loadFiles(),
            loadTransfers()
        ]);

    } catch (error) {

        console.error(error);


        errorMessage.textContent =
            "Some dashboard data could not be loaded.";


        errorMessage.style.display =
            "block";
    }
}


document
    .getElementById(
        "uploadButton"
    )
    .addEventListener(
        "click",
        uploadFile
    );


document
    .getElementById(
        "refreshButton"
    )
    .addEventListener(
        "click",
        loadDashboard
    );


document.addEventListener(
    "DOMContentLoaded",
    loadDashboard
);
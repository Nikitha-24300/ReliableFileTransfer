import os
import socket
import threading
import time

from shared.config import SERVER_HOST, SERVER_PORT
from shared.network import (
    send_message,
    receive_message,
    send_file,
    receive_file
)
from shared.protocol import (
    HELLO,
    HELLO_ACK,
    LIST,
    UPLOAD,
    DOWNLOAD,
    DELETE,
    EXIT,
    GOODBYE,
    ERROR,
    UPLOAD_READY,
    UPLOAD_REJECTED,
    DOWNLOAD_READY,
    DOWNLOAD_REJECTED,
    DOWNLOAD_COMPLETE,
    DOWNLOAD_INTEGRITY_OK,
    DOWNLOAD_INTEGRITY_FAILED,
    TRANSFER_COMPLETE,
    INTEGRITY_OK,
    INTEGRITY_FAILED,
    UPLOAD_SUCCESS,
    DELETE_SUCCESS,
    DELETE_FAILED
)

from server.file_manager import (
    list_files,
    get_storage_path,
    calculate_sha256,
    atomic_replace,
    is_valid_filename,
    is_valid_file_size,
    is_valid_sha256
)

from server.transfer_logger import (
    initialize_logger,
    log_transfer
)


file_locks = {}
file_locks_manager = threading.Lock()

progress_display_lock = threading.Lock()


def get_file_lock(filename):
    with file_locks_manager:
        if filename not in file_locks:
            file_locks[filename] = threading.Lock()

        return file_locks[filename]


def calculate_transfer_speed(
    file_size,
    duration
):
    if duration <= 0:
        return 0

    return file_size / duration


def format_transfer_speed(speed):
    if speed < 1024:
        return f"{speed:.2f} B/s"

    if speed < 1024 * 1024:
        return f"{speed / 1024:.2f} KB/s"

    return f"{speed / (1024 * 1024):.2f} MB/s"


def display_transfer_statistics(
    file_size,
    duration
):
    speed = calculate_transfer_speed(
        file_size,
        duration
    )

    formatted_speed = format_transfer_speed(
        speed
    )

    print(
        f"Transfer duration : {duration:.2f} seconds"
    )

    print(
        f"Transfer speed    : "
        f"{formatted_speed}"
    )

    return formatted_speed


def display_progress(
    transferred,
    total,
    client_address,
    operation,
    filename
):
    if total <= 0:
        percentage = 100
    else:
        percentage = (
            transferred / total
        ) * 100

    bar_length = 30

    filled_length = (
        int(
            bar_length
            * transferred
            / total
        )
        if total > 0
        else bar_length
    )

    progress_bar = (
        "=" * filled_length
        + " " * (
            bar_length
            - filled_length
        )
    )

    with progress_display_lock:
        print(
            f"\r[{client_address}] "
            f"{operation} {filename}: "
            f"[{progress_bar}] "
            f"{percentage:6.2f}% "
            f"({transferred} / {total} bytes)",
            end="",
            flush=True
        )

        if transferred >= total:
            print()


def cleanup_stale_temp_files():
    print(
        "Checking for stale temporary files..."
    )

    storage_dir = os.path.dirname(
        get_storage_path("dummy")
    )

    if not os.path.exists(storage_dir):
        print(
            "Storage directory does not exist."
        )
        return

    cleaned_count = 0

    for filename in os.listdir(storage_dir):
        if not filename.endswith(".tmp"):
            continue

        file_path = os.path.join(
            storage_dir,
            filename
        )

        if not os.path.isfile(file_path):
            continue

        try:
            os.remove(file_path)

            cleaned_count += 1

            print(
                f"Removed stale temporary file: "
                f"{filename}"
            )

        except OSError as error:
            print(
                f"Could not remove temporary file "
                f"{filename}: {error}"
            )

    if cleaned_count == 0:
        print(
            "No stale temporary files found."
        )

    else:
        print(
            f"Cleaned up {cleaned_count} "
            f"stale temporary file(s)."
        )


def handle_client(
    client_socket,
    client_address
):
    print(
        f"Client connected: {client_address}"
    )

    try:
        message = receive_message(
            client_socket
        )

        print(
            f"Received: {message}"
        )

        if message != HELLO:
            send_message(
                client_socket,
                ERROR
            )
            return

        send_message(
            client_socket,
            HELLO_ACK
        )

        print(
            f"[{client_address}] "
            f"Sent: HELLO_ACK"
        )

        while True:
            command = receive_message(
                client_socket
            )

            print(
                f"[{client_address}] "
                f"Command: {command}"
            )

            if command == LIST:
                print(
                    f"[{client_address}] "
                    f"LIST request received."
                )

                files = list_files()

                if not files:
                    send_message(
                        client_socket,
                        "FILE_LIST_EMPTY"
                    )

                else:
                    file_list = "\n".join(
                        files
                    )

                    send_message(
                        client_socket,
                        f"FILE_LIST\n{file_list}"
                    )

            elif command == UPLOAD:
                print(
                    f"[{client_address}] "
                    f"UPLOAD request received."
                )

                metadata = receive_message(
                    client_socket
                )

                parts = metadata.split("|")

                if len(parts) != 2:
                    print(
                        f"[{client_address}] "
                        f"Invalid upload metadata."
                    )

                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                filename = parts[0]

                try:
                    file_size = int(
                        parts[1]
                    )

                except ValueError:
                    print(
                        f"[{client_address}] "
                        f"Invalid upload file size."
                    )

                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                if not is_valid_filename(
                    filename
                ):
                    print(
                        f"[{client_address}] "
                        f"Invalid filename rejected: "
                        f"{filename}"
                    )

                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                if not is_valid_file_size(
                    file_size
                ):
                    print(
                        f"[{client_address}] "
                        f"Invalid file size rejected: "
                        f"{file_size}"
                    )

                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                print(
                    f"[{client_address}] "
                    f"Upload filename: {filename}"
                )

                print(
                    f"[{client_address}] "
                    f"Upload size: "
                    f"{file_size} bytes"
                )

                file_lock = get_file_lock(
                    filename
                )

                print(
                    f"[{client_address}] "
                    f"Waiting for lock: "
                    f"{filename}"
                )

                with file_lock:
                    print(
                        f"[{client_address}] "
                        f"Lock acquired: "
                        f"{filename}"
                    )

                    temp_path = get_storage_path(
                        filename + ".tmp"
                    )

                    final_path = get_storage_path(
                        filename
                    )

                    upload_completed = False
                    transfer_duration = 0
                    transfer_speed = "0.00 B/s"

                    try:
                        send_message(
                            client_socket,
                            UPLOAD_READY
                        )

                        print(
                            f"[{client_address}] "
                            f"Receiving file: "
                            f"{filename}"
                        )

                        transfer_start_time = (
                            time.perf_counter()
                        )

                        receive_file(
                            client_socket,
                            temp_path,
                            file_size,
                            progress_callback=lambda transferred, total:
                                display_progress(
                                    transferred,
                                    total,
                                    client_address,
                                    "UPLOAD",
                                    filename
                                )
                        )

                        transfer_end_time = (
                            time.perf_counter()
                        )

                        transfer_duration = (
                            transfer_end_time
                            - transfer_start_time
                        )

                        print(
                            f"[{client_address}] "
                            f"Temporary file received."
                        )

                        transfer_speed = (
                            display_transfer_statistics(
                                file_size,
                                transfer_duration
                            )
                        )

                        send_message(
                            client_socket,
                            TRANSFER_COMPLETE
                        )

                        expected_hash = receive_message(
                            client_socket
                        )

                        if not is_valid_sha256(
                            expected_hash
                        ):
                            print(
                                f"[{client_address}] "
                                f"Invalid SHA-256 hash "
                                f"received."
                            )

                            send_message(
                                client_socket,
                                INTEGRITY_FAILED
                            )

                            log_transfer(
                                client_address,
                                "UPLOAD",
                                filename,
                                file_size,
                                transfer_duration,
                                transfer_speed,
                                "FAILED"
                            )

                            continue

                        received_hash = calculate_sha256(
                            temp_path
                        )

                        print(
                            f"[{client_address}] "
                            f"Client SHA-256: "
                            f"{expected_hash}"
                        )

                        print(
                            f"[{client_address}] "
                            f"Server SHA-256: "
                            f"{received_hash}"
                        )

                        if (
                            expected_hash.lower()
                            == received_hash.lower()
                        ):
                            send_message(
                                client_socket,
                                INTEGRITY_OK
                            )

                            atomic_replace(
                                temp_path,
                                final_path
                            )

                            upload_completed = True

                            send_message(
                                client_socket,
                                UPLOAD_SUCCESS
                            )

                            log_transfer(
                                client_address,
                                "UPLOAD",
                                filename,
                                file_size,
                                transfer_duration,
                                transfer_speed,
                                "SUCCESS"
                            )

                            print(
                                f"[{client_address}] "
                                f"Upload completed: "
                                f"{filename}"
                            )

                        else:
                            send_message(
                                client_socket,
                                INTEGRITY_FAILED
                            )

                            log_transfer(
                                client_address,
                                "UPLOAD",
                                filename,
                                file_size,
                                transfer_duration,
                                transfer_speed,
                                "INTEGRITY_FAILED"
                            )

                            print(
                                f"[{client_address}] "
                                f"Integrity verification "
                                f"failed: {filename}"
                            )

                    except Exception as error:
                        print(
                            f"[{client_address}] "
                            f"Upload failed: "
                            f"{filename}"
                        )

                        print(
                            f"[{client_address}] "
                            f"Reason: {error}"
                        )

                        if transfer_duration > 0:
                            log_transfer(
                                client_address,
                                "UPLOAD",
                                filename,
                                file_size,
                                transfer_duration,
                                transfer_speed,
                                "FAILED"
                            )

                        raise

                    finally:
                        if (
                            not upload_completed
                            and os.path.exists(
                                temp_path
                            )
                        ):
                            try:
                                os.remove(
                                    temp_path
                                )

                                print(
                                    f"[{client_address}] "
                                    f"Temporary file "
                                    f"cleaned up: "
                                    f"{filename}.tmp"
                                )

                            except OSError as cleanup_error:
                                print(
                                    f"[{client_address}] "
                                    f"Could not remove "
                                    f"temporary file: "
                                    f"{cleanup_error}"
                                )

                    print(
                        f"[{client_address}] "
                        f"Lock released: "
                        f"{filename}"
                    )

            elif command == DOWNLOAD:
                print(
                    f"[{client_address}] "
                    f"DOWNLOAD request received."
                )

                filename = receive_message(
                    client_socket
                )

                if not is_valid_filename(
                    filename
                ):
                    print(
                        f"[{client_address}] "
                        f"Invalid download filename "
                        f"rejected: {filename}"
                    )

                    send_message(
                        client_socket,
                        DOWNLOAD_REJECTED
                    )
                    continue

                file_path = get_storage_path(
                    filename
                )

                if not os.path.isfile(
                    file_path
                ):
                    print(
                        f"[{client_address}] "
                        f"File not found: "
                        f"{filename}"
                    )

                    send_message(
                        client_socket,
                        DOWNLOAD_REJECTED
                    )
                    continue

                file_lock = get_file_lock(
                    filename
                )

                print(
                    f"[{client_address}] "
                    f"Waiting for lock: "
                    f"{filename}"
                )

                with file_lock:
                    print(
                        f"[{client_address}] "
                        f"Download lock acquired: "
                        f"{filename}"
                    )

                    if not os.path.isfile(
                        file_path
                    ):
                        send_message(
                            client_socket,
                            DOWNLOAD_REJECTED
                        )
                        continue

                    file_size = os.path.getsize(
                        file_path
                    )

                    if not is_valid_file_size(
                        file_size
                    ):
                        print(
                            f"[{client_address}] "
                            f"Invalid file size for "
                            f"{filename}"
                        )

                        send_message(
                            client_socket,
                            DOWNLOAD_REJECTED
                        )
                        continue

                    file_hash = calculate_sha256(
                        file_path
                    )

                    if not is_valid_sha256(
                        file_hash
                    ):
                        print(
                            f"[{client_address}] "
                            f"Invalid SHA-256 for "
                            f"{filename}"
                        )

                        send_message(
                            client_socket,
                            DOWNLOAD_REJECTED
                        )
                        continue

                    metadata = (
                        f"{file_size}|"
                        f"{file_hash}"
                    )

                    send_message(
                        client_socket,
                        DOWNLOAD_READY
                    )

                    send_message(
                        client_socket,
                        metadata
                    )

                    print(
                        f"[{client_address}] "
                        f"Sending file: "
                        f"{filename}"
                    )

                    print(
                        f"[{client_address}] "
                        f"File size: "
                        f"{file_size} bytes"
                    )

                    print(
                        f"[{client_address}] "
                        f"SHA-256: "
                        f"{file_hash}"
                    )

                    transfer_start_time = (
                        time.perf_counter()
                    )

                    send_file(
                        client_socket,
                        file_path,
                        file_size,
                        progress_callback=lambda transferred, total:
                            display_progress(
                                transferred,
                                total,
                                client_address,
                                "DOWNLOAD",
                                filename
                            )
                    )

                    transfer_end_time = (
                        time.perf_counter()
                    )

                    transfer_duration = (
                        transfer_end_time
                        - transfer_start_time
                    )

                    transfer_speed = (
                        display_transfer_statistics(
                            file_size,
                            transfer_duration
                        )
                    )

                    send_message(
                        client_socket,
                        DOWNLOAD_COMPLETE
                    )

                    response = receive_message(
                        client_socket
                    )

                    if (
                        response
                        == DOWNLOAD_INTEGRITY_OK
                    ):
                        log_transfer(
                            client_address,
                            "DOWNLOAD",
                            filename,
                            file_size,
                            transfer_duration,
                            transfer_speed,
                            "SUCCESS"
                        )

                        print(
                            f"[{client_address}] "
                            f"Download integrity "
                            f"verified: {filename}"
                        )

                    elif (
                        response
                        == DOWNLOAD_INTEGRITY_FAILED
                    ):
                        log_transfer(
                            client_address,
                            "DOWNLOAD",
                            filename,
                            file_size,
                            transfer_duration,
                            transfer_speed,
                            "INTEGRITY_FAILED"
                        )

                        print(
                            f"[{client_address}] "
                            f"Download integrity "
                            f"verification failed: "
                            f"{filename}"
                        )

                    else:
                        log_transfer(
                            client_address,
                            "DOWNLOAD",
                            filename,
                            file_size,
                            transfer_duration,
                            transfer_speed,
                            "PROTOCOL_ERROR"
                        )

                        print(
                            f"[{client_address}] "
                            f"PROTOCOL ERROR: Invalid "
                            f"download integrity response: "
                            f"{response}"
                        )

                        print(
                            f"[{client_address}] "
                            f"Closing connection because "
                            f"protocol state is invalid."
                        )

                        return

                    print(
                        f"[{client_address}] "
                        f"Download lock released: "
                        f"{filename}"
                    )

            elif command == DELETE:
                print(
                    f"[{client_address}] "
                    f"DELETE request received."
                )

                filename = receive_message(
                    client_socket
                )

                if not is_valid_filename(
                    filename
                ):
                    print(
                        f"[{client_address}] "
                        f"Invalid delete filename "
                        f"rejected: {filename}"
                    )

                    send_message(
                        client_socket,
                        DELETE_FAILED
                    )
                    continue

                file_path = get_storage_path(
                    filename
                )

                file_lock = get_file_lock(
                    filename
                )

                print(
                    f"[{client_address}] "
                    f"Waiting for delete lock: "
                    f"{filename}"
                )

                with file_lock:
                    print(
                        f"[{client_address}] "
                        f"Delete lock acquired: "
                        f"{filename}"
                    )

                    if os.path.isfile(
                        file_path
                    ):
                        os.remove(
                            file_path
                        )

                        send_message(
                            client_socket,
                            DELETE_SUCCESS
                        )

                        print(
                            f"[{client_address}] "
                            f"File deleted: "
                            f"{filename}"
                        )

                    else:
                        send_message(
                            client_socket,
                            DELETE_FAILED
                        )

                        print(
                            f"[{client_address}] "
                            f"File not found for "
                            f"deletion: {filename}"
                        )

                    print(
                        f"[{client_address}] "
                        f"Delete lock released: "
                        f"{filename}"
                    )

            elif command == EXIT:
                send_message(
                    client_socket,
                    GOODBYE
                )

                print(
                    f"[{client_address}] "
                    f"Client requested disconnect."
                )

                break

            else:
                send_message(
                    client_socket,
                    ERROR
                )

                print(
                    f"[{client_address}] "
                    f"Unknown command: {command}"
                )

    except ConnectionError as error:
        print(
            f"Connection error with "
            f"{client_address}: {error}"
        )

    except Exception as error:
        print(
            f"Unexpected error with "
            f"{client_address}: {error}"
        )

    finally:
        client_socket.close()

        print(
            f"Client disconnected: "
            f"{client_address}"
        )


def start_server():
    cleanup_stale_temp_files()

    initialize_logger()

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server_socket.bind(
        (SERVER_HOST, SERVER_PORT)
    )

    server_socket.listen()

    print("=" * 50)
    print(
        "       RELIABLE FILE TRANSFER SERVER"
    )
    print("=" * 50)
    print(
        f"Server IP   : {SERVER_HOST}"
    )
    print(
        f"Server Port : {SERVER_PORT}"
    )
    print(
        "Status      : Running"
    )
    print(
        "Mode        : Multi-Client"
    )
    print(
        "Locking     : Per-File"
    )
    print(
        "Temp Cleanup: Enabled"
    )
    print(
        "Validation  : Enabled"
    )
    print(
        "Progress    : Enabled"
    )
    print(
        "Protocol    : Hardened"
    )
    print(
        "Statistics  : Enabled"
    )
    print(
        "Logging     : Enabled"
    )
    print(
        "Waiting for clients..."
    )
    print("=" * 50)

    while True:
        client_socket, client_address = (
            server_socket.accept()
        )

        client_thread = threading.Thread(
            target=handle_client,
            args=(
                client_socket,
                client_address
            )
        )

        client_thread.start()

        print(
            f"Active client thread started "
            f"for {client_address}"
        )


if __name__ == "__main__":
    start_server()
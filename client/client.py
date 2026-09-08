
import hashlib
import os
import re
import socket
import time

from shared.config import SERVER_HOST, SERVER_PORT
from shared.network import (
    send_message,
    receive_message,
    receive_file,
    send_file
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
    TRANSFER_COMPLETE,
    INTEGRITY_OK,
    INTEGRITY_FAILED,
    UPLOAD_SUCCESS,
    DOWNLOAD_READY,
    DOWNLOAD_REJECTED,
    DOWNLOAD_COMPLETE,
    DOWNLOAD_INTEGRITY_OK,
    DOWNLOAD_INTEGRITY_FAILED,
    DELETE_SUCCESS,
    DELETE_FAILED
)


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(4096)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def is_valid_filename(filename):
    if not filename:
        return False

    if len(filename) > 255:
        return False

    if os.path.basename(filename) != filename:
        return False

    if filename in (".", ".."):
        return False

    invalid_characters = '<>:"/\\|?*'

    for character in invalid_characters:
        if character in filename:
            return False

    if any(
        ord(character) < 32
        for character in filename
    ):
        return False

    if filename.endswith(" ") or filename.endswith("."):
        return False

    return True


def is_valid_file_size(file_size):
    return file_size >= 0


def is_valid_sha256(file_hash):
    if not isinstance(file_hash, str):
        return False

    return re.fullmatch(
        r"[0-9a-fA-F]{64}",
        file_hash
    ) is not None


def display_progress(transferred, total):
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

    print(
        f"\r[{progress_bar}] "
        f"{percentage:6.2f}% "
        f"({transferred} / {total} bytes)",
        end="",
        flush=True
    )


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

    print(
        f"Transfer duration : {duration:.2f} seconds"
    )

    print(
        f"Transfer speed    : "
        f"{format_transfer_speed(speed)}"
    )


def display_menu():
    print()
    print("=" * 45)
    print("          FILE TRANSFER MENU")
    print("=" * 45)
    print("1. List Files")
    print("2. Upload File")
    print("3. Download File")
    print("4. Delete File")
    print("5. Exit")
    print("=" * 45)


def start_client():
    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    print("=" * 45)
    print("     RELIABLE FILE TRANSFER CLIENT")
    print("=" * 45)

    print(
        f"Connecting to "
        f"{SERVER_HOST}:{SERVER_PORT}..."
    )

    try:
        client_socket.connect(
            (SERVER_HOST, SERVER_PORT)
        )

        print(
            "Connected to server successfully."
        )

        send_message(
            client_socket,
            HELLO
        )

        response = receive_message(
            client_socket
        )

        if response != HELLO_ACK:
            print(
                "ERROR: Server handshake failed."
            )
            return

        print(
            "Server handshake successful."
        )

        while True:
            display_menu()

            choice = input(
                "Enter choice: "
            ).strip()

            if choice == "1":
                try:
                    send_message(
                        client_socket,
                        LIST
                    )

                    print(
                        "LIST request sent."
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == "FILE_LIST_EMPTY":
                        print()
                        print(
                            "No files available "
                            "on the server."
                        )

                    elif response.startswith(
                        "FILE_LIST\n"
                    ):
                        print()
                        print(
                            "========== AVAILABLE FILES =========="
                        )

                        file_data = response[
                            len("FILE_LIST\n"):
                        ]

                        for index, filename in enumerate(
                            file_data.split("\n"),
                            start=1
                        ):
                            print(
                                f"{index}. {filename}"
                            )

                        print(
                            "====================================="
                        )

                    else:
                        print(
                            "ERROR: Invalid response "
                            "received from server."
                        )

                except ConnectionError:
                    print(
                        "ERROR: Connection to server "
                        "was lost while listing files."
                    )
                    break

                except Exception as error:
                    print(
                        f"ERROR: Could not list files: "
                        f"{error}"
                    )

            elif choice == "2":
                file_path = input(
                    "Enter the path of the file "
                    "to upload: "
                ).strip()

                if not os.path.isfile(file_path):
                    print(
                        "ERROR: File does not exist."
                    )
                    continue

                filename = os.path.basename(
                    file_path
                )

                if not is_valid_filename(
                    filename
                ):
                    print(
                        "ERROR: Invalid filename."
                    )
                    continue

                file_size = os.path.getsize(
                    file_path
                )

                if not is_valid_file_size(
                    file_size
                ):
                    print(
                        "ERROR: Invalid file size."
                    )
                    continue

                try:
                    file_hash = calculate_sha256(
                        file_path
                    )

                except OSError as error:
                    print(
                        f"ERROR: Could not read the "
                        f"file: {error}"
                    )
                    continue

                if not is_valid_sha256(
                    file_hash
                ):
                    print(
                        "ERROR: Could not calculate "
                        "a valid SHA-256 hash."
                    )
                    continue

                try:
                    send_message(
                        client_socket,
                        UPLOAD
                    )

                    metadata = (
                        f"{filename}|{file_size}"
                    )

                    send_message(
                        client_socket,
                        metadata
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == UPLOAD_REJECTED:
                        print(
                            "ERROR: Server rejected "
                            "the upload."
                        )
                        continue

                    if response != UPLOAD_READY:
                        print(
                            "ERROR: Protocol error. "
                            "Unexpected server response "
                            "during upload preparation."
                        )
                        print(
                            "Connection will be closed "
                            "to prevent protocol desynchronization."
                        )
                        return

                    print()
                    print(
                        f"Uploading: {filename}"
                    )

                    print(
                        f"File size: {file_size} bytes"
                    )

                    print(
                        f"SHA-256: {file_hash}"
                    )

                    transfer_start_time = time.perf_counter()

                    send_file(
                        client_socket,
                        file_path,
                        file_size,
                        progress_callback=display_progress
                    )

                    transfer_end_time = time.perf_counter()

                    transfer_duration = (
                        transfer_end_time
                        - transfer_start_time
                    )

                    print()
                    print(
                        "File data sent successfully."
                    )

                    display_transfer_statistics(
                        file_size,
                        transfer_duration
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response != TRANSFER_COMPLETE:
                        print(
                            "ERROR: Protocol error. "
                            "Server did not confirm "
                            "file transfer."
                        )
                        print(
                            "Connection will be closed "
                            "to prevent protocol desynchronization."
                        )
                        return

                    send_message(
                        client_socket,
                        file_hash
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == INTEGRITY_OK:
                        print(
                            "SHA-256 verification: PASSED"
                        )

                        response = receive_message(
                            client_socket
                        )

                        if response == UPLOAD_SUCCESS:
                            print(
                                "Upload completed successfully."
                            )

                        else:
                            print(
                                "ERROR: Protocol error. "
                                "Server did not confirm "
                                "upload completion."
                            )
                            print(
                                "Connection will be closed."
                            )
                            return

                    elif response == INTEGRITY_FAILED:
                        print(
                            "SHA-256 verification: FAILED"
                        )

                        print(
                            "ERROR: Server rejected "
                            "the uploaded file."
                        )

                    else:
                        print(
                            "ERROR: Protocol error. "
                            "Unexpected integrity "
                            "response from server."
                        )
                        print(
                            "Connection will be closed."
                        )
                        return

                except ConnectionError:
                    print()
                    print(
                        "ERROR: Connection to server "
                        "was lost during upload."
                    )
                    print(
                        "The server will clean up "
                        "the temporary upload file."
                    )
                    break

                except OSError as error:
                    print()
                    print(
                        f"ERROR: File transfer failed: "
                        f"{error}"
                    )

                except Exception as error:
                    print()
                    print(
                        f"ERROR: Upload failed: "
                        f"{error}"
                    )

            elif choice == "3":
                filename = input(
                    "Enter the filename to download: "
                ).strip()

                if not filename:
                    print(
                        "ERROR: Filename cannot be empty."
                    )
                    continue

                if not is_valid_filename(
                    filename
                ):
                    print(
                        "ERROR: Invalid filename."
                    )
                    continue

                try:
                    send_message(
                        client_socket,
                        DOWNLOAD
                    )

                    send_message(
                        client_socket,
                        filename
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == DOWNLOAD_REJECTED:
                        print(
                            "ERROR: File not found or "
                            "download was rejected."
                        )
                        continue

                    if response != DOWNLOAD_READY:
                        print(
                            "ERROR: Protocol error. "
                            "Unexpected server response "
                            "during download preparation."
                        )
                        print(
                            "Connection will be closed "
                            "to prevent protocol desynchronization."
                        )
                        return

                    metadata = receive_message(
                        client_socket
                    )

                    parts = metadata.split("|")

                    if len(parts) != 2:
                        print(
                            "ERROR: Invalid download "
                            "metadata received."
                        )
                        print(
                            "Connection will be closed "
                            "to prevent protocol desynchronization."
                        )
                        return

                    try:
                        file_size = int(
                            parts[0]
                        )

                    except ValueError:
                        print(
                            "ERROR: Invalid file size "
                            "received from server."
                        )
                        print(
                            "Connection will be closed "
                            "to prevent protocol desynchronization."
                        )
                        return

                    expected_hash = parts[1]

                    if not is_valid_file_size(
                        file_size
                    ):
                        print(
                            "ERROR: Server sent an "
                            "invalid file size."
                        )
                        print(
                            "Connection will be closed."
                        )
                        return

                    if not is_valid_sha256(
                        expected_hash
                    ):
                        print(
                            "ERROR: Server sent an "
                            "invalid SHA-256 hash."
                        )
                        print(
                            "Connection will be closed."
                        )
                        return

                    download_dir = os.path.join(
                        os.path.dirname(
                            os.path.abspath(__file__)
                        ),
                        "downloads"
                    )

                    os.makedirs(
                        download_dir,
                        exist_ok=True
                    )

                    download_path = os.path.join(
                        download_dir,
                        filename
                    )

                    temp_download_path = (
                        download_path + ".tmp"
                    )

                    print()
                    print(
                        f"Downloading: {filename}"
                    )

                    print(
                        f"File size: {file_size} bytes"
                    )

                    print(
                        f"Server SHA-256: "
                        f"{expected_hash}"
                    )

                    download_completed = False

                    try:
                        transfer_start_time = (
                            time.perf_counter()
                        )

                        receive_file(
                            client_socket,
                            temp_download_path,
                            file_size,
                            progress_callback=display_progress
                        )

                        transfer_end_time = (
                            time.perf_counter()
                        )

                        transfer_duration = (
                            transfer_end_time
                            - transfer_start_time
                        )

                        print()
                        print(
                            "File data received successfully."
                        )

                        display_transfer_statistics(
                            file_size,
                            transfer_duration
                        )

                        response = receive_message(
                            client_socket
                        )

                        if response != DOWNLOAD_COMPLETE:
                            print(
                                "ERROR: Protocol error. "
                                "Server did not confirm "
                                "download completion."
                            )
                            print(
                                "Connection will be closed "
                                "to prevent protocol desynchronization."
                            )
                            return

                        received_hash = calculate_sha256(
                            temp_download_path
                        )

                        print(
                            f"Downloaded SHA-256: "
                            f"{received_hash}"
                        )

                        if not is_valid_sha256(
                            received_hash
                        ):
                            print(
                                "ERROR: Local SHA-256 "
                                "calculation failed."
                            )

                            send_message(
                                client_socket,
                                DOWNLOAD_INTEGRITY_FAILED
                            )

                            print(
                                "Connection will be closed."
                            )
                            return

                        if (
                            expected_hash.lower()
                            == received_hash.lower()
                        ):
                            send_message(
                                client_socket,
                                DOWNLOAD_INTEGRITY_OK
                            )

                            os.replace(
                                temp_download_path,
                                download_path
                            )

                            download_completed = True

                            print(
                                "SHA-256 verification: PASSED"
                            )

                            print(
                                "Download completed successfully."
                            )

                            print(
                                f"Saved to: {download_path}"
                            )

                        else:
                            send_message(
                                client_socket,
                                DOWNLOAD_INTEGRITY_FAILED
                            )

                            print(
                                "SHA-256 verification: FAILED"
                            )

                            print(
                                "ERROR: Downloaded file "
                                "is corrupted."
                            )

                            print(
                                "Temporary file will be "
                                "removed."
                            )

                    except ConnectionError:
                        print()
                        print(
                            "ERROR: Connection to server "
                            "was lost during download."
                        )

                        print(
                            "The incomplete temporary "
                            "download will be removed."
                        )

                        break

                    except OSError as error:
                        print()
                        print(
                            f"ERROR: Could not save "
                            f"downloaded file: {error}"
                        )

                    except Exception as error:
                        print()
                        print(
                            f"ERROR: Download failed: "
                            f"{error}"
                        )

                    finally:
                        if (
                            not download_completed
                            and os.path.exists(
                                temp_download_path
                            )
                        ):
                            try:
                                os.remove(
                                    temp_download_path
                                )

                                print(
                                    "Temporary download "
                                    "file cleaned up."
                                )

                            except OSError as cleanup_error:
                                print(
                                    f"WARNING: Could not remove "
                                    f"temporary download file: "
                                    f"{cleanup_error}"
                                )

                except ConnectionError:
                    print(
                        "ERROR: Connection to server "
                        "was lost."
                    )
                    break

                except Exception as error:
                    print(
                        f"ERROR: Download request failed: "
                        f"{error}"
                    )

            elif choice == "4":
                filename = input(
                    "Enter the filename to delete: "
                ).strip()

                if not filename:
                    print(
                        "ERROR: Filename cannot be empty."
                    )
                    continue

                if not is_valid_filename(
                    filename
                ):
                    print(
                        "ERROR: Invalid filename."
                    )
                    continue

                try:
                    send_message(
                        client_socket,
                        DELETE
                    )

                    send_message(
                        client_socket,
                        filename
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == DELETE_SUCCESS:
                        print(
                            f"File deleted successfully: "
                            f"{filename}"
                        )

                    elif response == DELETE_FAILED:
                        print(
                            f"File could not be deleted: "
                            f"{filename}"
                        )

                    else:
                        print(
                            "ERROR: Unexpected response "
                            "from server."
                        )

                except ConnectionError:
                    print(
                        "ERROR: Connection to server "
                        "was lost while deleting the file."
                    )
                    break

                except Exception as error:
                    print(
                        f"ERROR: Delete operation failed: "
                        f"{error}"
                    )

            elif choice == "5":
                try:
                    send_message(
                        client_socket,
                        EXIT
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == GOODBYE:
                        print(
                            "Server acknowledged disconnect."
                        )

                except ConnectionError:
                    print(
                        "Server connection was already lost."
                    )

                break

            else:
                print(
                    "Invalid choice. "
                    "Please select 1-5."
                )

    except ConnectionRefusedError:
        print(
            "ERROR: Connection failed."
        )

        print(
            "Make sure the server is running."
        )

    except ConnectionError as error:
        print(
            f"ERROR: Connection error: {error}"
        )

    except OSError as error:
        print(
            f"ERROR: Could not start client: {error}"
        )

    finally:
        client_socket.close()

        print(
            "Client connection closed."
        )


if __name__ == "__main__":
    start_client()


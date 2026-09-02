import hashlib
import os
import socket

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
    DOWNLOAD_INTEGRITY_FAILED
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
            print("Server handshake failed.")
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

            elif choice == "2":
                file_path = input(
                    "Enter the path of the file "
                    "to upload: "
                ).strip()

                if not os.path.isfile(file_path):
                    print(
                        "File does not exist."
                    )
                    continue

                filename = os.path.basename(
                    file_path
                )

                file_size = os.path.getsize(
                    file_path
                )

                file_hash = calculate_sha256(
                    file_path
                )

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
                        "Server rejected "
                        "the upload."
                    )
                    continue

                if response != UPLOAD_READY:
                    print(
                        "Unexpected server response."
                    )
                    continue

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

                send_file(
                    client_socket,
                    file_path,
                    file_size
                )

                response = receive_message(
                    client_socket
                )

                if response != TRANSFER_COMPLETE:
                    print(
                        "File transfer "
                        "was not completed."
                    )
                    continue

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

                elif response == INTEGRITY_FAILED:
                    print(
                        "SHA-256 verification: FAILED"
                    )

                    print(
                        "Server rejected the file."
                    )

                else:
                    print(
                        "Unexpected integrity response."
                    )

            elif choice == "3":
                filename = input(
                    "Enter the filename to download: "
                ).strip()

                if not filename:
                    print(
                        "Filename cannot be empty."
                    )
                    continue

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
                        "File not found or "
                        "download was rejected."
                    )
                    continue

                if response != DOWNLOAD_READY:
                    print(
                        "Unexpected server response."
                    )
                    continue

                metadata = receive_message(
                    client_socket
                )

                parts = metadata.split("|")

                if len(parts) != 2:
                    print(
                        "Invalid download metadata."
                    )
                    continue

                try:
                    file_size = int(parts[0])

                except ValueError:
                    print(
                        "Invalid file size received."
                    )
                    continue

                expected_hash = parts[1]

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

                print()
                print(
                    f"Downloading: {filename}"
                )

                print(
                    f"File size: {file_size} bytes"
                )

                print(
                    f"Server SHA-256: {expected_hash}"
                )

                receive_file(
                    client_socket,
                    download_path,
                    file_size
                )

                response = receive_message(
                    client_socket
                )

                if response != DOWNLOAD_COMPLETE:
                    print(
                        "Download was not completed."
                    )
                    continue

                received_hash = calculate_sha256(
                    download_path
                )

                print(
                    f"Downloaded SHA-256: "
                    f"{received_hash}"
                )

                if expected_hash == received_hash:
                    send_message(
                        client_socket,
                        DOWNLOAD_INTEGRITY_OK
                    )

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
                        "Downloaded file may be corrupted."
                    )

            elif choice == "4":
                send_message(
                    client_socket,
                    DELETE
                )

                print(
                    "DELETE request sent."
                )

                response = receive_message(
                    client_socket
                )

                if response == ERROR:
                    print(
                        "Server reported an error."
                    )

            elif choice == "5":
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

                break

            else:
                print(
                    "Invalid choice. "
                    "Please select 1-5."
                )

    except ConnectionRefusedError:
        print(
            "Connection failed."
        )

        print(
            "Make sure the server is running."
        )

    except ConnectionError as error:
        print(
            f"Connection error: {error}"
        )

    finally:
        client_socket.close()

        print(
            "Client connection closed."
        )


if __name__ == "__main__":
    start_client()
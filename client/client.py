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

                file_size = os.path.getsize(
                    file_path
                )

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
                            "ERROR: Unexpected response "
                            "from server."
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

                    print(
                        "File data sent successfully."
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response != TRANSFER_COMPLETE:
                        print(
                            "ERROR: Server did not "
                            "confirm file transfer."
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

                        else:
                            print(
                                "ERROR: Server did not "
                                "confirm upload completion."
                            )

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
                            "ERROR: Unexpected integrity "
                            "response from server."
                        )

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
                            "ERROR: Unexpected response "
                            "from server."
                        )
                        continue

                    metadata = receive_message(
                        client_socket
                    )

                    parts = metadata.split("|")

                    if len(parts) != 2:
                        print(
                            "ERROR: Invalid download "
                            "metadata received."
                        )
                        continue

                    try:
                        file_size = int(parts[0])

                    except ValueError:
                        print(
                            "ERROR: Invalid file size "
                            "received from server."
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
                        receive_file(
                            client_socket,
                            temp_download_path,
                            file_size
                        )

                        print(
                            "File data received successfully."
                        )

                        response = receive_message(
                            client_socket
                        )

                        if response != DOWNLOAD_COMPLETE:
                            print(
                                "ERROR: Server did not "
                                "confirm download completion."
                            )
                            continue

                        received_hash = calculate_sha256(
                            temp_download_path
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
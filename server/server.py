import os
import socket
import threading

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
    TRANSFER_COMPLETE,
    INTEGRITY_OK,
    INTEGRITY_FAILED,
    UPLOAD_SUCCESS
)

from server.file_manager import (
    list_files,
    get_storage_path,
    calculate_sha256,
    atomic_replace
)


file_locks = {}
file_locks_manager = threading.Lock()


def get_file_lock(filename):
    with file_locks_manager:
        if filename not in file_locks:
            file_locks[filename] = threading.Lock()

        return file_locks[filename]


def handle_client(client_socket, client_address):
    print(f"Client connected: {client_address}")

    try:
        message = receive_message(client_socket)

        print(f"Received: {message}")

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
            f"[{client_address}] Sent: HELLO_ACK"
        )

        while True:
            command = receive_message(client_socket)

            print(
                f"[{client_address}] Command: {command}"
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
                    file_list = "\n".join(files)

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
                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                filename = parts[0]

                try:
                    file_size = int(parts[1])

                except ValueError:
                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                if not filename:
                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                if file_size < 0:
                    send_message(
                        client_socket,
                        UPLOAD_REJECTED
                    )
                    continue

                if (
                    os.path.basename(filename)
                    != filename
                ):
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
                    f"Upload size: {file_size} bytes"
                )

                file_lock = get_file_lock(filename)

                print(
                    f"[{client_address}] "
                    f"Waiting for lock: {filename}"
                )

                with file_lock:
                    print(
                        f"[{client_address}] "
                        f"Lock acquired: {filename}"
                    )

                    send_message(
                        client_socket,
                        UPLOAD_READY
                    )

                    temp_path = get_storage_path(
                        filename + ".tmp"
                    )

                    final_path = get_storage_path(
                        filename
                    )

                    receive_file(
                        client_socket,
                        temp_path,
                        file_size
                    )

                    print(
                        f"[{client_address}] "
                        f"Temporary file received."
                    )

                    send_message(
                        client_socket,
                        TRANSFER_COMPLETE
                    )

                    expected_hash = receive_message(
                        client_socket
                    )

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

                    if expected_hash == received_hash:
                        send_message(
                            client_socket,
                            INTEGRITY_OK
                        )

                        atomic_replace(
                            temp_path,
                            final_path
                        )

                        send_message(
                            client_socket,
                            UPLOAD_SUCCESS
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

                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                        print(
                            f"[{client_address}] "
                            f"Integrity verification failed: "
                            f"{filename}"
                        )

                    print(
                        f"[{client_address}] "
                        f"Lock released: {filename}"
                    )

            elif command == DOWNLOAD:
                print(
                    f"[{client_address}] "
                    f"DOWNLOAD request received."
                )

                filename = receive_message(
                    client_socket
                )

                if not filename:
                    send_message(
                        client_socket,
                        DOWNLOAD_REJECTED
                    )
                    continue

                if (
                    os.path.basename(filename)
                    != filename
                ):
                    send_message(
                        client_socket,
                        DOWNLOAD_REJECTED
                    )
                    continue

                file_path = get_storage_path(
                    filename
                )

                if not os.path.isfile(file_path):
                    print(
                        f"[{client_address}] "
                        f"File not found: {filename}"
                    )

                    send_message(
                        client_socket,
                        DOWNLOAD_REJECTED
                    )
                    continue

                file_lock = get_file_lock(filename)

                print(
                    f"[{client_address}] "
                    f"Waiting for lock: {filename}"
                )

                with file_lock:
                    print(
                        f"[{client_address}] "
                        f"Download lock acquired: {filename}"
                    )

                    if not os.path.isfile(file_path):
                        send_message(
                            client_socket,
                            DOWNLOAD_REJECTED
                        )
                        continue

                    file_size = os.path.getsize(
                        file_path
                    )

                    file_hash = calculate_sha256(
                        file_path
                    )

                    metadata = (
                        f"{file_size}|{file_hash}"
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
                        f"Sending file: {filename}"
                    )

                    print(
                        f"[{client_address}] "
                        f"File size: {file_size} bytes"
                    )

                    print(
                        f"[{client_address}] "
                        f"SHA-256: {file_hash}"
                    )

                    send_file(
                        client_socket,
                        file_path,
                        file_size
                    )

                    send_message(
                        client_socket,
                        DOWNLOAD_COMPLETE
                    )

                    response = receive_message(
                        client_socket
                    )

                    if response == DOWNLOAD_INTEGRITY_OK:
                        print(
                            f"[{client_address}] "
                            f"Download integrity verified: "
                            f"{filename}"
                        )

                    else:
                        print(
                            f"[{client_address}] "
                            f"Download integrity verification "
                            f"failed: {filename}"
                        )

                    print(
                        f"[{client_address}] "
                        f"Download lock released: {filename}"
                    )

            elif command == DELETE:
                print(
                    f"[{client_address}] "
                    f"DELETE request received."
                )

                send_message(
                    client_socket,
                    "DELETE_ACK"
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
    print("       RELIABLE FILE TRANSFER SERVER")
    print("=" * 50)
    print(f"Server IP   : {SERVER_HOST}")
    print(f"Server Port : {SERVER_PORT}")
    print("Status      : Running")
    print("Mode        : Multi-Client")
    print("Locking     : Per-File")
    print("Waiting for clients...")
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
            f"Active client thread started for "
            f"{client_address}"
        )


if __name__ == "__main__":
    start_server()
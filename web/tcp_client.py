import hashlib
import os
import socket

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
    UPLOAD,
    UPLOAD_READY,
    TRANSFER_COMPLETE,
    INTEGRITY_OK,
    INTEGRITY_FAILED,
    UPLOAD_SUCCESS,
    DOWNLOAD,
    DOWNLOAD_READY,
    DOWNLOAD_REJECTED,
    DOWNLOAD_COMPLETE,
    DOWNLOAD_INTEGRITY_OK,
    DOWNLOAD_INTEGRITY_FAILED,
    DELETE,
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


def create_connection():
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.connect(
        (SERVER_HOST, SERVER_PORT)
    )

    send_message(
        sock,
        HELLO
    )

    response = receive_message(sock)

    if response != HELLO_ACK:
        sock.close()

        raise ConnectionError(
            "TCP server handshake failed."
        )

    return sock


def upload_file(file_path):
    filename = os.path.basename(file_path)

    file_size = os.path.getsize(
        file_path
    )

    file_hash = calculate_sha256(
        file_path
    )

    sock = create_connection()

    try:
        send_message(
            sock,
            UPLOAD
        )

        send_message(
            sock,
            f"{filename}|{file_size}"
        )

        response = receive_message(
            sock
        )

        if response != UPLOAD_READY:
            raise RuntimeError(
                "Server rejected upload."
            )

        send_file(
            sock,
            file_path,
            file_size
        )

        response = receive_message(
            sock
        )

        if response != TRANSFER_COMPLETE:
            raise RuntimeError(
                "Server did not confirm "
                "file transfer."
            )

        send_message(
            sock,
            file_hash
        )

        response = receive_message(
            sock
        )

        if response == INTEGRITY_OK:

            response = receive_message(
                sock
            )

            if response == UPLOAD_SUCCESS:
                return {
                    "success": True,
                    "filename": filename,
                    "size": file_size,
                    "sha256": file_hash,
                    "message":
                        "Upload completed successfully."
                }

            raise RuntimeError(
                "Server did not confirm upload."
            )

        if response == INTEGRITY_FAILED:
            return {
                "success": False,
                "filename": filename,
                "message":
                    "SHA-256 verification failed."
            }

        raise RuntimeError(
            "Unexpected integrity response."
        )

    finally:
        sock.close()


def download_file(filename):
    sock = create_connection()

    try:
        send_message(
            sock,
            DOWNLOAD
        )

        send_message(
            sock,
            filename
        )

        response = receive_message(
            sock
        )

        if response == DOWNLOAD_REJECTED:
            return {
                "success": False,
                "message":
                    "File not found on server."
            }

        if response != DOWNLOAD_READY:
            raise RuntimeError(
                "Unexpected download response."
            )

        metadata = receive_message(
            sock
        )

        parts = metadata.split("|")

        if len(parts) != 2:
            raise RuntimeError(
                "Invalid download metadata."
            )

        file_size = int(parts[0])
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

        temp_path = (
            download_path + ".tmp"
        )

        try:
            receive_file(
                sock,
                temp_path,
                file_size
            )

            response = receive_message(
                sock
            )

            if response != DOWNLOAD_COMPLETE:
                raise RuntimeError(
                    "Server did not confirm "
                    "download completion."
                )

            received_hash = calculate_sha256(
                temp_path
            )

            if (
                expected_hash.lower()
                != received_hash.lower()
            ):
                send_message(
                    sock,
                    DOWNLOAD_INTEGRITY_FAILED
                )

                return {
                    "success": False,
                    "message":
                        "Downloaded file failed "
                        "SHA-256 verification."
                }

            send_message(
                sock,
                DOWNLOAD_INTEGRITY_OK
            )

            os.replace(
                temp_path,
                download_path
            )

            return {
                "success": True,
                "filename": filename,
                "size": file_size,
                "sha256": received_hash,
                "path": download_path,
                "message":
                    "Download completed successfully."
            }

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    finally:
        sock.close()


def delete_file(filename):
    sock = create_connection()

    try:
        send_message(
            sock,
            DELETE
        )

        send_message(
            sock,
            filename
        )

        response = receive_message(
            sock
        )

        if response == DELETE_SUCCESS:
            return {
                "success": True,
                "filename": filename,
                "message":
                    "File deleted successfully."
            }

        if response == DELETE_FAILED:
            return {
                "success": False,
                "filename": filename,
                "message":
                    "File could not be deleted."
            }

        raise RuntimeError(
            "Unexpected delete response."
        )

    finally:
        sock.close()
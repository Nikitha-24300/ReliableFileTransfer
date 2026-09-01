import socket

from shared.config import SERVER_HOST, SERVER_PORT
from shared.network import send_message, receive_message
from shared.protocol import (
    HELLO,
    HELLO_ACK,
    LIST,
    UPLOAD,
    DOWNLOAD,
    DELETE,
    EXIT,
    GOODBYE,
    ERROR
)
from server.file_manager import list_files


def handle_client(client_socket, client_address):
    print(f"Client connected: {client_address}")

    try:
        message = receive_message(client_socket)

        print(f"Received: {message}")

        if message != HELLO:
            send_message(client_socket, ERROR)
            return

        send_message(client_socket, HELLO_ACK)
        print("Sent: HELLO_ACK")

        while True:
            command = receive_message(client_socket)

            print(f"[{client_address}] Command: {command}")

            if command == LIST:
                print("LIST request received.")

                files = list_files()

                if not files:
                    send_message(client_socket, "FILE_LIST_EMPTY")
                else:
                    file_list = "\n".join(files)
                    send_message(client_socket, f"FILE_LIST\n{file_list}")

            elif command == UPLOAD:
                print("UPLOAD request received.")
                send_message(client_socket, "UPLOAD_ACK")

            elif command == DOWNLOAD:
                print("DOWNLOAD request received.")
                send_message(client_socket, "DOWNLOAD_ACK")

            elif command == DELETE:
                print("DELETE request received.")
                send_message(client_socket, "DELETE_ACK")

            elif command == EXIT:
                send_message(client_socket, GOODBYE)
                print("Client requested disconnect.")
                break

            else:
                send_message(client_socket, ERROR)
                print(f"Unknown command: {command}")

    except ConnectionError as error:
        print(f"Connection error with {client_address}: {error}")

    finally:
        client_socket.close()
        print(f"Client disconnected: {client_address}")


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

    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen()

    print("=" * 45)
    print("     RELIABLE FILE TRANSFER SERVER")
    print("=" * 45)
    print(f"Server IP   : {SERVER_HOST}")
    print(f"Server Port : {SERVER_PORT}")
    print("Status      : Running")
    print("Waiting for clients...")
    print("=" * 45)

    while True:
        client_socket, client_address = server_socket.accept()

        handle_client(
            client_socket,
            client_address
        )


if __name__ == "__main__":
    start_server()
import socket

from shared.config import SERVER_HOST, SERVER_PORT
from shared.network import send_message, receive_message
from shared.protocol import HELLO, HELLO_ACK


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

        print(f"Client connected: {client_address}")

        try:
            message = receive_message(client_socket)

            print(f"Received: {message}")

            if message == HELLO:
                send_message(client_socket, HELLO_ACK)
                print("Sent: HELLO_ACK")

        except ConnectionError as error:
            print(f"Connection error: {error}")

        finally:
            client_socket.close()
            print(f"Client disconnected: {client_address}")


if __name__ == "__main__":
    start_server()
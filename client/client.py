import socket

from shared.config import SERVER_HOST, SERVER_PORT
from shared.network import send_message, receive_message
from shared.protocol import HELLO, HELLO_ACK


def start_client():
    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    print("=" * 45)
    print("     RELIABLE FILE TRANSFER CLIENT")
    print("=" * 45)

    print(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")

    try:
        client_socket.connect(
            (SERVER_HOST, SERVER_PORT)
        )

        print("Connected to server successfully.")

        send_message(client_socket, HELLO)
        print("Sent: HELLO")

        response = receive_message(client_socket)
        print(f"Received: {response}")

        if response == HELLO_ACK:
            print("Server handshake successful.")

    except ConnectionRefusedError:
        print("Connection failed.")
        print("Make sure the server is running.")

    except ConnectionError as error:
        print(f"Connection error: {error}")

    finally:
        client_socket.close()
        print("Client connection closed.")


if __name__ == "__main__":
    start_client()
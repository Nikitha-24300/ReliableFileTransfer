import socket

from shared.config import SERVER_HOST, SERVER_PORT


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
        client_socket.connect((SERVER_HOST, SERVER_PORT))

        print("Connected to server successfully.")
        print(f"Server address: {SERVER_HOST}:{SERVER_PORT}")

    except ConnectionRefusedError:
        print("Connection failed.")
        print("Make sure the server is running.")

    finally:
        client_socket.close()
        print("Client connection closed.")


if __name__ == "__main__":
    start_client()
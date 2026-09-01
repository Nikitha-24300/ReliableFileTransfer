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

    print(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")

    try:
        client_socket.connect(
            (SERVER_HOST, SERVER_PORT)
        )

        print("Connected to server successfully.")

        send_message(client_socket, HELLO)

        response = receive_message(client_socket)

        if response != HELLO_ACK:
            print("Server handshake failed.")
            return

        print("Server handshake successful.")

        while True:
            display_menu()

            choice = input("Enter choice: ").strip()

            if choice == "1":
                send_message(client_socket, LIST)
                print("LIST request sent.")

            elif choice == "2":
                send_message(client_socket, UPLOAD)
                print("UPLOAD request sent.")

            elif choice == "3":
                send_message(client_socket, DOWNLOAD)
                print("DOWNLOAD request sent.")

            elif choice == "4":
                send_message(client_socket, DELETE)
                print("DELETE request sent.")

            elif choice == "5":
                send_message(client_socket, EXIT)

                response = receive_message(client_socket)

                if response == GOODBYE:
                    print("Server acknowledged disconnect.")

                break

            else:
                print("Invalid choice. Please select 1-5.")

            response = receive_message(client_socket)

            if response == ERROR:
                print("Server reported an error.")

            elif response == "FILE_LIST_EMPTY":
                print()
                print("No files available on the server.")

            elif response.startswith("FILE_LIST\n"):
                print()
                print("========== AVAILABLE FILES ==========")

                file_data = response[len("FILE_LIST\n"):]

                for index, filename in enumerate(file_data.split("\n"), start=1):
                    print(f"{index}. {filename}")

                print("=====================================")

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
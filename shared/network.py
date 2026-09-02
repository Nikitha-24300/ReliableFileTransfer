import struct


HEADER_SIZE = 4
CHUNK_SIZE = 4096


def send_message(sock, message):
    data = message.encode("utf-8")
    header = struct.pack("!I", len(data))

    sock.sendall(header + data)


def receive_exact(sock, size):
    data = bytearray()

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk:
            raise ConnectionError("Connection closed by peer.")

        data.extend(chunk)

    return bytes(data)


def receive_message(sock):
    header = receive_exact(sock, HEADER_SIZE)

    message_length = struct.unpack("!I", header)[0]

    message_data = receive_exact(
        sock,
        message_length
    )

    return message_data.decode("utf-8")


def send_file(sock, file_path, file_size):
    with open(file_path, "rb") as file:
        remaining = file_size

        while remaining > 0:
            chunk = file.read(
                min(CHUNK_SIZE, remaining)
            )

            if not chunk:
                raise IOError(
                    "File ended before expected size."
                )

            sock.sendall(chunk)

            remaining -= len(chunk)


def receive_file(sock, file_path, file_size):
    remaining = file_size

    with open(file_path, "wb") as file:
        while remaining > 0:
            chunk_size = min(
                CHUNK_SIZE,
                remaining
            )

            chunk = receive_exact(
                sock,
                chunk_size
            )

            file.write(chunk)

            remaining -= len(chunk)
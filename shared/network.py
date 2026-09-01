import struct


HEADER_SIZE = 4


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

    message_data = receive_exact(sock, message_length)

    return message_data.decode("utf-8")
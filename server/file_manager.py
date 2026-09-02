import hashlib
import os

from shared.config import STORAGE_DIR


def list_files():
    if not os.path.exists(STORAGE_DIR):
        return []

    files = []

    for filename in os.listdir(STORAGE_DIR):
        file_path = os.path.join(
            STORAGE_DIR,
            filename
        )

        if os.path.isfile(file_path):
            if not filename.endswith(".tmp"):
                files.append(filename)

    return sorted(files)


def get_storage_path(filename):
    return os.path.join(
        STORAGE_DIR,
        filename
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


def atomic_replace(temp_path, final_path):
    os.replace(
        temp_path,
        final_path
    )
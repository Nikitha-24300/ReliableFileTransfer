import hashlib
import os
import re

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


def is_valid_filename(filename):
    if not filename:
        return False

    if len(filename) > 255:
        return False

    if os.path.basename(filename) != filename:
        return False

    if filename in (".", ".."):
        return False

    invalid_characters = '<>:"/\\|?*'

    for character in invalid_characters:
        if character in filename:
            return False

    if any(
        ord(character) < 32
        for character in filename
    ):
        return False

    if filename.endswith(" ") or filename.endswith("."):
        return False

    return True


def is_valid_file_size(file_size):
    return file_size >= 0


def is_valid_sha256(file_hash):
    if not isinstance(file_hash, str):
        return False

    return re.fullmatch(
        r"[0-9a-fA-F]{64}",
        file_hash
    ) is not None
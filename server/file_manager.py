import os

from shared.config import STORAGE_DIR


def list_files():
    if not os.path.exists(STORAGE_DIR):
        return []

    files = []

    for filename in os.listdir(STORAGE_DIR):
        file_path = os.path.join(STORAGE_DIR, filename)

        if os.path.isfile(file_path):
            files.append(filename)

    return sorted(files)
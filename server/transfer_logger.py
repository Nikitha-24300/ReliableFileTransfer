import os
from datetime import datetime


LOG_DIR = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "logs"
)

LOG_FILE = os.path.join(
    LOG_DIR,
    "transfer_history.log"
)


def initialize_logger():
    os.makedirs(
        LOG_DIR,
        exist_ok=True
    )

    if not os.path.exists(LOG_FILE):
        with open(
            LOG_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(
                "TIMESTAMP | CLIENT | OPERATION | "
                "FILENAME | SIZE | DURATION | "
                "SPEED | STATUS\n"
            )


def log_transfer(
    client_address,
    operation,
    filename,
    file_size,
    duration,
    speed,
    status
):
    initialize_logger()

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if isinstance(client_address, tuple):
        client = client_address[0]
    else:
        client = str(client_address)

    log_entry = (
        f"{timestamp} | "
        f"{client} | "
        f"{operation} | "
        f"{filename} | "
        f"{file_size} bytes | "
        f"{duration:.2f} sec | "
        f"{speed} | "
        f"{status}\n"
    )

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:
        file.write(
            log_entry
        )


def get_log_file():
    initialize_logger()

    return LOG_FILE
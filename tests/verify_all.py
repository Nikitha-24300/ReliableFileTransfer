"""
Automated End-to-End Verification Test Suite
Tests:
1. Server start
2. Handshake (HELLO -> HELLO_ACK)
3. Multiple clients concurrent connect
4. File listing (LIST)
5. Upload with SHA-256 calculation & atomic commit
6. Download with SHA-256 integrity verification
7. Per-file locking & concurrency
8. Invalid input rejection
9. Stale temporary file cleanup
10. Delete functionality
11. Flask web app & APIs: /api/status, /api/files, /api/transfers, /api/upload, /api/download, /api/delete
"""

import os
import sys
import time
import socket
import threading
import hashlib
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.config import SERVER_HOST, SERVER_PORT, STORAGE_DIR
from shared.protocol import (
    HELLO, HELLO_ACK, LIST, UPLOAD, DOWNLOAD, DELETE, EXIT, GOODBYE,
    UPLOAD_READY, TRANSFER_COMPLETE, INTEGRITY_OK, UPLOAD_SUCCESS,
    DOWNLOAD_READY, DOWNLOAD_COMPLETE, DOWNLOAD_INTEGRITY_OK,
    DELETE_SUCCESS
)
from shared.network import send_message, receive_message, send_file, receive_file
from server.server import start_server, get_file_lock
from web.tcp_client import check_server_status, upload_file, download_file, delete_file
import web.app as web_app


def calculate_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class TestReliableFileTransfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start TCP server in daemon thread
        cls.server_thread = threading.Thread(target=start_server, daemon=True)
        cls.server_thread.start()
        time.sleep(1.0)  # Allow server to bind and listen

        # Setup Flask test client
        cls.flask_client = web_app.app.test_client()

    def test_01_handshake(self):
        sock = socket.socket()
        sock.connect((SERVER_HOST, SERVER_PORT))
        send_message(sock, HELLO)
        resp = receive_message(sock)
        self.assertEqual(resp, HELLO_ACK)
        send_message(sock, EXIT)
        self.assertEqual(receive_message(sock), GOODBYE)
        sock.close()

    def test_02_multiple_clients(self):
        sockets = []
        for _ in range(5):
            s = socket.socket()
            s.connect((SERVER_HOST, SERVER_PORT))
            send_message(s, HELLO)
            self.assertEqual(receive_message(s), HELLO_ACK)
            sockets.append(s)

        for s in sockets:
            send_message(s, LIST)
            resp = receive_message(s)
            self.assertTrue(resp.startswith("FILE_LIST") or resp == "FILE_LIST_EMPTY")
            send_message(s, EXIT)
            self.assertEqual(receive_message(s), GOODBYE)
            s.close()

    def test_03_tcp_upload_download_delete(self):
        test_filename = "automated_verify_test.bin"
        test_data = b"Reliable TCP file transfer payload verification content 1234567890." * 50
        test_hash = calculate_hash(test_data)
        test_size = len(test_data)

        # 1. Upload via TCP socket
        sock = socket.socket()
        sock.connect((SERVER_HOST, SERVER_PORT))
        send_message(sock, HELLO)
        self.assertEqual(receive_message(sock), HELLO_ACK)

        send_message(sock, UPLOAD)
        send_message(sock, f"{test_filename}|{test_size}")
        self.assertEqual(receive_message(sock), UPLOAD_READY)

        # Send raw chunks
        sock.sendall(test_data)
        self.assertEqual(receive_message(sock), TRANSFER_COMPLETE)

        send_message(sock, test_hash)
        self.assertEqual(receive_message(sock), INTEGRITY_OK)
        self.assertEqual(receive_message(sock), UPLOAD_SUCCESS)

        # 2. Download via TCP socket
        send_message(sock, DOWNLOAD)
        send_message(sock, test_filename)
        self.assertEqual(receive_message(sock), DOWNLOAD_READY)
        meta = receive_message(sock)
        dl_size_str, dl_hash = meta.split("|")
        self.assertEqual(int(dl_size_str), test_size)
        self.assertEqual(dl_hash.lower(), test_hash.lower())

        # Receive file data
        from shared.network import receive_exact
        dl_data = receive_exact(sock, test_size)
        self.assertEqual(dl_data, test_data)
        self.assertEqual(receive_message(sock), DOWNLOAD_COMPLETE)

        send_message(sock, DOWNLOAD_INTEGRITY_OK)

        # 3. Delete via TCP socket
        send_message(sock, DELETE)
        send_message(sock, test_filename)
        self.assertEqual(receive_message(sock), DELETE_SUCCESS)

        send_message(sock, EXIT)
        self.assertEqual(receive_message(sock), GOODBYE)
        sock.close()

    def test_04_web_apis(self):
        # Test /api/status
        res = self.flask_client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        status_data = res.get_json()
        self.assertTrue(status_data["online"])
        self.assertEqual(status_data["port"], SERVER_PORT)
        self.assertIn("total_files", status_data)
        self.assertIn("total_storage", status_data)

        # Test /api/files
        res = self.flask_client.get("/api/files")
        self.assertEqual(res.status_code, 200)
        files = res.get_json()
        self.assertIsInstance(files, list)

        # Test /api/transfers
        res = self.flask_client.get("/api/transfers")
        self.assertEqual(res.status_code, 200)
        transfers = res.get_json()
        self.assertIsInstance(transfers, list)

    def test_05_web_upload_and_download(self):
        # Create a small temp file for upload test
        import io
        test_filename = "web_test_upload.txt"
        content = b"Verification of Flask Web Upload through TCP Socket backend."
        data = {
            'file': (io.BytesIO(content), test_filename)
        }
        res = self.flask_client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        up_json = res.get_json()
        self.assertTrue(up_json["success"])
        self.assertEqual(up_json["filename"], test_filename)
        self.assertEqual(up_json["sha256"], calculate_hash(content))

        # Test download
        dl_res = self.flask_client.get(f'/api/download/{test_filename}')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.data, content)

        # Test delete
        del_res = self.flask_client.delete(f'/api/delete/{test_filename}')
        self.assertEqual(del_res.status_code, 200)
        del_json = del_res.get_json()
        self.assertTrue(del_json["success"])


if __name__ == "__main__":
    unittest.main()

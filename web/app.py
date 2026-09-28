import os

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file
)

from server.file_manager import (
    list_files,
    get_storage_path,
    calculate_sha256
)

from server.transfer_logger import (
    get_log_file
)

from web.tcp_client import (
    upload_file,
    download_file,
    delete_file
)


app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template(
        "index.html"
    )


@app.route("/api/files")
def get_files():
    files = []

    for filename in list_files():
        file_path = get_storage_path(
            filename
        )

        try:
            file_size = os.path.getsize(
                file_path
            )

            file_hash = calculate_sha256(
                file_path
            )

            files.append({
                "filename": filename,
                "size": file_size,
                "sha256": file_hash
            })

        except OSError:
            continue

    return jsonify(files)


@app.route("/api/transfers")
def get_transfers():
    log_file = get_log_file()

    transfers = []

    if not os.path.exists(log_file):
        return jsonify(transfers)

    with open(
        log_file,
        "r",
        encoding="utf-8"
    ) as file:
        lines = file.readlines()

    for line in lines[1:]:
        line = line.strip()

        if not line:
            continue

        parts = [
            part.strip()
            for part in line.split("|")
        ]

        if len(parts) != 8:
            continue

        transfers.append({
            "timestamp": parts[0],
            "client": parts[1],
            "operation": parts[2],
            "filename": parts[3],
            "size": parts[4],
            "duration": parts[5],
            "speed": parts[6],
            "status": parts[7]
        })

    return jsonify(transfers)


@app.route(
    "/api/upload",
    methods=["POST"]
)
def web_upload():

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "No file selected."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "message": "Invalid filename."
        }), 400

    upload_dir = os.path.join(
        app.root_path,
        "temp_uploads"
    )

    os.makedirs(
        upload_dir,
        exist_ok=True
    )

    temp_path = os.path.join(
        upload_dir,
        uploaded_file.filename
    )

    try:
        uploaded_file.save(
            temp_path
        )

        result = upload_file(
            temp_path
        )

        return jsonify(result)

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.route(
    "/api/download/<filename>"
)
def web_download(filename):

    try:
        result = download_file(
            filename
        )

        if not result["success"]:
            return jsonify(result), 404

        download_path = result["path"]

        return send_file(
            download_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@app.route(
    "/api/delete/<filename>",
    methods=["DELETE"]
)
def web_delete(filename):

    try:
        result = delete_file(
            filename
        )

        status_code = (
            200
            if result["success"]
            else 404
        )

        return jsonify(result), status_code

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )
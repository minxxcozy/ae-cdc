from flask import Flask, jsonify, send_from_directory
import json, os

app = Flask(__name__)

# 절대경로로 고정
BASE_DIR = os.path.dirname(os.path.dirname(__file__))   # server/ 상위 폴더
CHUNK_DIR = os.path.join(BASE_DIR, "data", "chunks")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "manifest_ae.json")

@app.route("/firmware/list")
def list_files():
    files = sorted(os.listdir(CHUNK_DIR))
    return jsonify(files)

@app.route("/firmware/file/<filename>")
def get_file(filename):
    file_path = os.path.join(CHUNK_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"{filename} not found"}), 404
    return send_from_directory(CHUNK_DIR, filename, as_attachment=True)

@app.route("/firmware/manifest")
def get_manifest():
    with open(MANIFEST_PATH, "r") as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == "__main__":
    print(f"[+] Serving chunks from: {CHUNK_DIR}")
    app.run(host="0.0.0.0", port=8000)
import os

def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def write_file(path: str, data: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
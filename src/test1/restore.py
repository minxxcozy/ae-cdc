# restore.py
import os, time, json

RECEIVED_DIR = "data/received"
OUTPUT_FILE = "data/reconstructed.bin"
METRIC_PATH = "metrics/restore_result.json"

def restore_received():
    files = sorted([f for f in os.listdir(RECEIVED_DIR) if f.startswith("part-")])
    total_bytes = 0

    print(f"[*] Restoring {len(files)} chunks from {RECEIVED_DIR}...")
    t0 = time.time()

    with open(OUTPUT_FILE, "wb") as out_f:
        for fname in files:
            fpath = os.path.join(RECEIVED_DIR, fname)
            with open(fpath, "rb") as f:
                data = f.read()
                out_f.write(data)
                total_bytes += len(data)

    t1 = time.time()
    elapsed = t1 - t0

    print(f"[+] Restore completed in {elapsed:.4f} s ({total_bytes/1024/1024:.2f} MB total)")

    metrics = {
        "restored_chunks": len(files),
        "total_bytes": total_bytes,
        "restore_time": round(elapsed, 4)
    }

    os.makedirs("metrics", exist_ok=True)
    with open(METRIC_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    restore_received()
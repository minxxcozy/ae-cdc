import requests, time, os, random, json
from client.manifest import get_manifest
from utils.hasher import sha256_bytes
from metrics.evaluator import log_metrics

SERVER_URL = "http://127.0.0.1:8000"
OUT_DIR = "data/received"

# 네트워크 실패 / 인터럽트 시나리오
FAIL_PROB = 0.2                         # 20% 확률로 네트워크 실패 주입
INTERRUPT_BYTES = 128 * 1024            # 128 KiB 이상 수신 시 인터럽트 후보
INTERRUPT_RATE = 0.04                   # 약 4% 확률로 중간 인터럽트 발생
MIN_INTERRUPT_SIZE = 1 * 1024 * 1024    # 1 MiB 이상 파일만 인터럽트 대상

random.seed(42)
os.makedirs(OUT_DIR, exist_ok=True)


def download_file(meta):
    """
    서버로부터 개별 파일을 다운로드하며
    실패 및 인터럽트를 시뮬레이션
    """
    filename = meta["filename"]
    url = f"{SERVER_URL}/firmware/file/{filename}"
    out_path = os.path.join(OUT_DIR, filename)

    # 1단계: 인위적 네트워크 실패
    if random.random() < FAIL_PROB:
        raise ConnectionError("Simulated network failure")

    with requests.get(url, stream=True, timeout=10) as r:
        r.raise_for_status()

        total = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                total += len(chunk)

                # 2단계: 인터럽트 발생 조건 체크
                if total >= INTERRUPT_BYTES:
                    # 파일이 충분히 큰 경우만 후보로
                    if meta["size"] >= MIN_INTERRUPT_SIZE and random.random() < INTERRUPT_RATE:
                        raise ConnectionAbortedError("Intentional interrupt")

    # 3단계: 데이터 무결성 검증
    with open(out_path, "rb") as f:
        data = f.read()

    file_hash = sha256_bytes(data)
    if file_hash != meta["sha256"]:
        raise ValueError(f"Hash mismatch for {filename}")

    return len(data)


def main():
    manifest = get_manifest(SERVER_URL)
    total_bytes, attempts, errors = 0, 0, 0

    t0 = time.time()
    for meta in manifest:
        attempts += 1
        try:
            size = download_file(meta)
            total_bytes += size
            print(f"[+] {meta['filename']} OK ({size/1024/1024:.2f} MB)")
        except Exception as e:
            errors += 1
            print(f"[!] Error {meta['filename']}: {e}")
            path = os.path.join(OUT_DIR, meta["filename"])
            if os.path.exists(path):
                os.remove(path)
    t1 = time.time()

    log_metrics(len(manifest), total_bytes, t0, t1, attempts, errors)


if __name__ == "__main__":
    main()
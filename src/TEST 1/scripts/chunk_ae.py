import os, time, json, hashlib
from chunkers.ae_cdc import ae_cdc
from metrics.evaluator import log_chunk_metrics

INPUT_FILE = "data/rootfs.tar"              # 청킹할 원본 파일 경로
CHUNK_DIR = "data/chunks"                   # 청크 저장 폴더
MANIFEST_PATH = "data/manifest_ae.json"     # 매니페스트 출력 경로

os.makedirs(CHUNK_DIR, exist_ok=True)

# SHA-256 해시 계산 함수
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main():
    print("[*] Loading input file...")
    with open(INPUT_FILE, "rb") as f:
        data = f.read()

    print(f"[*] Starting AE-CDC chunking ({len(data)/1024/1024:.2f} MB)")
    t0 = time.time()
    chunks = ae_cdc(data)   # AE-CDC 청킹 수행
    t1 = time.time()

    print(f"[+] Chunking completed in {t1 - t0:.4f} s")
    print(f"[+] Total chunks: {len(chunks)}")

    # 청크 저장 + SHA256 해시 생성
    manifest = []
    for i, chunk in enumerate(chunks):
        fname = f"part-{i:05d}"
        path = os.path.join(CHUNK_DIR, fname)
        with open(path, "wb") as f:
            f.write(chunk)

        manifest.append({
            "filename": fname,
            "size": len(chunk),
            "sha256": sha256_bytes(chunk) 
        })

    # 매니페스트 저장
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    # 청킹 메트릭 로깅
    log_chunk_metrics(len(chunks), len(data), t0, t1)

if __name__ == "__main__":
    main()
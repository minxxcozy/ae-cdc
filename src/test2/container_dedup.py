#!/usr/bin/env python3
# OCI → AE-CDC chunk → Reassemble → Merge Layers(whiteout) → Import(podman)
# 최소 로그: 단계 배너만 출력, 마지막 run에만 명령 줄 출력

import os, sys, json, shutil, tarfile, mmap, subprocess, re, hashlib
import ae_cdc  

# --- 경로/설정 ---
HERE = os.path.dirname(__file__)
SOURCE_OCI_DIR    = os.path.join(HERE, 'data', 'ubuntu-oci')
CHUNKS_DIR        = os.path.join(HERE, 'chunks_storage')
MANIFESTS_DIR     = os.path.join(HERE, 'manifests')
REASSEMBLED_DIR   = os.path.join(HERE, 'reassembled_oci')
MERGED_ROOTFS_DIR = os.path.join(REASSEMBLED_DIR, '_merged_rootfs')
IMAGE_NAME = os.environ.get("IMAGE_NAME", "ubuntu-aecdc:latest")

AVG = 64 * 1024
MIN = AVG // 2
MAX = AVG * 2
WIN = 64  # AE-CDC 좌측 창

# ------------------------- 유틸 -------------------------
def ensure_dirs():
    for d in [MANIFESTS_DIR, REASSEMBLED_DIR, MERGED_ROOTFS_DIR]:
        if os.path.exists(d): shutil.rmtree(d)
    for d in [CHUNKS_DIR, MANIFESTS_DIR, REASSEMBLED_DIR, MERGED_ROOTFS_DIR]:
        os.makedirs(d, exist_ok=True)

def clean_path(name: str) -> str:
    name = name.replace('\\','/')
    name = re.sub(r'^\./','', name).lstrip('/')
    parts = [p for p in name.split('/') if p not in ('', '.', '..')]
    return '/'.join(parts)

def sha256_hex(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def write_chunk_if_absent(h: str, data: bytes):
    p = os.path.join(CHUNKS_DIR, h)
    if not os.path.exists(p):
        with open(p, 'wb') as w: w.write(data)

# ------------------------- 1) AE-CDC 분할 -------------------------
def chunk_file_aecdc(path: str, base_dir: str):
    rel = os.path.relpath(path, base_dir)
    mf_path = os.path.join(MANIFESTS_DIR, rel)
    os.makedirs(os.path.dirname(mf_path), exist_ok=True)

    hashes = []
    size = os.path.getsize(path)
    with open(path, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        if size < MIN:
            data = mm[:]
            h = sha256_hex(data); hashes.append(h)
            write_chunk_if_absent(h, data)
        else:
            for c in ae_cdc.iter_chunks(memoryview(mm), MIN, AVG, MAX, win_left=WIN, mode="max"):
                off, ln = c.offset, c.length
                if ln <= 0: continue
                data = mm[off:off+ln]
                h = sha256_hex(data); hashes.append(h)
                write_chunk_if_absent(h, data)

    with open(mf_path, 'w') as mf:
        json.dump(hashes, mf, indent=0)

def split_all():
    print('--- [1/6] AE-CDC 분할 ---')
    for root, _, files in os.walk(SOURCE_OCI_DIR):
        for n in files:
            chunk_file_aecdc(os.path.join(root, n), SOURCE_OCI_DIR)

# ------------------------- 2) 재조립 -------------------------
def reassemble_file(manifest_path: str, base_dir: str):
    rel = os.path.relpath(manifest_path, base_dir)
    outp = os.path.join(REASSEMBLED_DIR, rel)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with open(manifest_path, 'r') as mf:
        hashes = json.load(mf)
    with open(outp, 'wb') as w:
        for h in hashes:
            with open(os.path.join(CHUNKS_DIR, h), 'rb') as r:
                shutil.copyfileobj(r, w)

def join_all():
    print('--- [2/6] 파일 재조립 ---')
    for root, _, files in os.walk(MANIFESTS_DIR):
        for n in files:
            reassemble_file(os.path.join(root, n), MANIFESTS_DIR)

# ------------------------- 3) 매니페스트 로드(첫 항목 고정) -------------------------
def get_layers_first_manifest():
    print('--- [3/6] 매니페스트 로드(첫 항목) ---')
    idx = os.path.join(REASSEMBLED_DIR, 'index.json')
    mans = json.load(open(idx))['manifests']
    man_dig = mans[0]['digest'].split(':')[1]
    man_path = os.path.join(REASSEMBLED_DIR, 'blobs', 'sha256', man_dig)
    manifest = json.load(open(man_path))
    return [l['digest'].split(':')[1] for l in manifest['layers']]

# ------------------------- 4) 레이어 병합(화이트아웃) -------------------------
def apply_whiteout(base_dir: str, member_dir: str, base_name: str):
    tgt = os.path.join(base_dir, member_dir, base_name[4:])
    if os.path.isdir(tgt): shutil.rmtree(tgt, ignore_errors=True)
    else:
        try: os.remove(tgt)
        except FileNotFoundError: pass

def apply_opq(base_dir: str, member_dir: str):
    tdir = os.path.join(base_dir, member_dir)
    if os.path.isdir(tdir):
        for e in os.listdir(tdir):
            p = os.path.join(tdir, e)
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else (os.remove(p) if os.path.exists(p) else None)

def extract_member(tar: tarfile.TarFile, m: tarfile.TarInfo, dest_root: str):
    name = clean_path(m.name)
    if not name: return
    tar.extract(m, path=dest_root)  # 신뢰 입력 가정

def apply_layer(layer_tar_path: str, dest_root: str):
    with tarfile.open(layer_tar_path, 'r:*') as t:
        mem = t.getmembers()
        for m in mem:
            if os.path.basename(m.name) == '.wh..wh..opq':
                apply_opq(dest_root, clean_path(os.path.dirname(m.name)))
        for m in mem:
            name = clean_path(m.name)
            base = os.path.basename(name)
            if base.startswith('.wh.'):
                apply_whiteout(dest_root, os.path.dirname(name), base); continue
            if base == '.wh..wh..opq': continue
            extract_member(t, m, dest_root)

def merge_layers(layers):
    print('--- [4/6] 레이어 병합 ---')
    if os.path.exists(MERGED_ROOTFS_DIR): shutil.rmtree(MERGED_ROOTFS_DIR)
    os.makedirs(MERGED_ROOTFS_DIR, exist_ok=True)
    for dg in layers:
        lp = os.path.join(REASSEMBLED_DIR, 'blobs', 'sha256', dg)
        apply_layer(lp, MERGED_ROOTFS_DIR)

# ------------------------- 5) Import -------------------------
def import_image():
    print('--- [5/6] tar 스트림 → podman import ---')
    tar_p = subprocess.Popen(['tar','-C', MERGED_ROOTFS_DIR, '-cf','-','.'], stdout=subprocess.PIPE)
    try:
        subprocess.run(
            [
                'podman','import',
                '--change','ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                '--change','CMD ["/bin/sh","-lc","echo OK"]',
                '-', IMAGE_NAME
            ],
            check=True, stdin=tar_p.stdout
        )
    finally:
        if tar_p.stdout: tar_p.stdout.close()
        tar_p.wait()

# ------------------------- 6) 스모크 테스트 -------------------------
def run_container():
    print('--- [6/6] 컨테이너 실행 ---')
    print(f"> 실행: podman run --rm {IMAGE_NAME}")
    subprocess.run(['podman','run','--rm', IMAGE_NAME], check=True)

# ------------------------- 메인 -------------------------
def main():
    if not os.path.isdir(SOURCE_OCI_DIR):
        print(f"오류: '{SOURCE_OCI_DIR}' 없음", file=sys.stderr); sys.exit(1)
    print('=== AE-CDC 기반 OCI 재조립 파이프라인 시작 ===')
    ensure_dirs()
    split_all()
    join_all()
    layers = get_layers_first_manifest()
    merge_layers(layers)
    import_image()
    run_container()
    print('=== 완료 ===')

if __name__ == '__main__':
    main()

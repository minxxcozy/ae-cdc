# Asymmetric Extremum Content-Defined Chunking (AE-CDC)
> **AE-CDC** 알고리즘을 이용해 Ubuntu 컨테이너 이미지를 **가변 청크 단위로 분할 (Chunking)** 하고,  
> 네트워크 오류나 중단 상황을 가정하여 **전송 및 복원 (Download / Restore)** 과정을 실험하는 프로젝트입니다.



## ⚙️ 환경 세팅

### 🧱 레포지토리 클론
```bash
git clone https://github.com/minxxcozy/ae-cdc.git
cd ae-cdc
```

### 🌎 가상환경 생성 및 활성화
```bash
python -m venv .venv
source .venv/bin/activate
```
* 모든 작업은 **반드시 가상환경**에서 진행해 주세요.

### 📦 의존성 설치
```bash
pip install -r requirements.txt
```

## 🗂️ Ubuntu 이미지 준비
* **Podman**을 사용해 Ubuntu 22.04 이미지를 다운로드한 뒤,
* 이를 **tar 파일로 추출**하여 AE-CDC의 입력으로 사용합니다.

### 1️⃣ Ubuntu 22.04 이미지 pull
```bash
podman pull ubuntu:22.04
```

### 2️⃣ oci-archive 포맷으로 저장
```bash
podman save --format oci-archive -o ubuntu.tar ubuntu:22.04
```

### 3️⃣ 압축 해제
```bash
mkdir -p data/ubuntu-oci
tar -xf ubuntu.tar -C data/ubuntu-oci
```

## 📚 Chunk 대상 파일 지정 
* 아래 명령으로 실제 chunking을 수행할 tar 파일 (`rootfs.tar`)을 지정합니다.
* 보통 `data/ubuntu-oci/blobs/sha256/...` 안의 가장 큰 파일이 `rootfs`입니다.

### ❗ 예시
```bash
mv data/ubuntu-oci/blobs/sha256/392fa14dddd09da29a5c3d26948ff81c494424035b755d01b84ab12d92127433 data/rootfs.tar
```

## 🔨 AE-CDC 청킹 실행
```bash
python3 -m scripts.chunk_ae
```

### ✅ 실행 결과 예시
```html
[*] Loading input file...
[*] Starting AE-CDC chunking (30.05 MB)
[+] Chunking completed in 15.6 s
[+] Total chunks: 61
{
  "chunk_count": 61,
  "total_bytes": 31508480,
  "chunking_time": 15.6188,
  "chunking_speed_MBps": 1.92
}
```
* `chunk_count` : 생성된 청크 수
* `chunking_speed_MBps` : 평균 청킹 속도 (MB/s)
* `data/chunks/` 디렉토리에 part-00000, part-00001 … 형태로 저장
* `data/manifest_ae.json` 에 매니페스트 기록

## 🌐 OTA 서버 실행 (터미널 1)
```bash
python3 -m server.server
```
* `Running on http://127.0.0.1:8000`이 출력되면, 클라이언트가 해당 서버로부터 청크 파일을 다운로드할 수 있습니다.

## 📡 클라이언트 다운로드 & 네트워크 실패 실험 (터미널 2)
```bash
python3 -m client.run_bench
```

### ✅ 실행 결과 예시
```html
[+] part-00000 OK (0.50 MB)
[!] Error part-00007: Simulated network failure
[+] part-00008 OK (0.50 MB)
...
{
  "chunk_count": 61,
  "total_bytes": 24165263,
  "avg_chunk_size": 396151.85,
  "elapsed_time": 0.65,
  "attempts_total": 61,
  "errors_total": 14,
  "chunking_speed": 93.48
}
```

## 🔁 청크 복원 테스트 (터미널 3)
다운로드가 종료되면, 아래 명령으로 복원할 수 있습니다.
```bash
python3 restore.py
```

### ✅ 실행 결과 예시
```bash
[*] Restoring 47 chunks from data/received...
[+] Restore completed in 0.0534 s (23.05 MB total)
```
* `data/reconstructed_*.bin` 파일이 생성되며, 원본 rootfs.tar와 동일한 내용으로 복원됩니다.  

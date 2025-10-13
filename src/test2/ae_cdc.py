from collections import deque
from typing import Iterable, NamedTuple

class Chunk(NamedTuple):
    offset: int
    length: int

# 256-entry gear 테이블(예시)
GEAR = [
    0x3f84d5b5,0xd56c3b2f,0x175f9e8b,0xa1c3b1d7,0x9e3779b1,0x7feb352d,0x85ebca6b,0xc2b2ae35,
    0x27d4eb2f,0x165667b1,0x9e3779b9,0x94d049bb,0x3c6ef372,0xbb67ae85,0xa54ff53a,0x510e527f,
] * 16  # 길이 256 맞춤

def iter_chunks(buf: memoryview,
                min_size: int, avg_size: int, max_size: int,
                win_left: int = 256,       # ← FastCDC와 비슷한 평균을 위해 256 권장
                mode: str = "max"          # "max" 또는 "min"
                ) -> Iterable[Chunk]:
    """
    AE-CDC (Asymmetric-Extremum) chunking:
      - strong cut: size >= MAX
      - normal cut: size >= AVG AND current hash is the left-window extremum
    """
    n = len(buf)
    if n == 0:
        return
    dq = deque()  # (index, hash), 모노톤 큐

    def dq_push(i, h, greater=True):
        if greater:  # 최대 큐
            while dq and dq[-1][1] <= h:
                dq.pop()
        else:        # 최소 큐
            while dq and dq[-1][1] >= h:
                dq.pop()
        dq.append((i, h))

    def dq_prune(left_idx):
        while dq and dq[0][0] < left_idx:
            dq.popleft()

    h = 0
    off = 0
    i = 0
    greater = (mode == "max")
    MIN, AVG, MAX = min_size, avg_size, max_size

    while i < n:
        b = buf[i]
        h = ((h << 1) & 0xFFFFFFFF) ^ GEAR[b]
        dq_push(i, h, greater)
        clen = i - off + 1

        # strong cut: 최대 사이즈 도달 시 즉시 컷
        if clen >= MAX:
            yield Chunk(off, clen)
            off = i + 1
            dq.clear(); h = 0
            i += 1
            continue

        # normal cut: AVG 이상이고, 현재가 좌측창 극값이면 컷
        if clen >= AVG:
            left = i - win_left + 1
            if left < off:
                left = off
            dq_prune(left)
            if dq and dq[0][0] == i:
                yield Chunk(off, clen)
                off = i + 1
                dq.clear(); h = 0

        i += 1

    # 잔여
    if off < n:
        yield Chunk(off, n - off)
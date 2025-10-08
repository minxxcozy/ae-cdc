from collections import deque
from typing import List, Tuple

def ae_cdc(
    stream: bytes,
    left_win: int = 256,
    right_win: int = 512,
    min_chunk: int = 512 * 1024,        # 0.5 MB
    max_chunk: int = 8 * 1024 * 1024    # 8 MB
) -> List[Tuple[int, int]]:
    n = len(stream)
    chunks, start = [], 0
    left, right = deque(), deque()

    for i in range(1, right_win + 1):
        if i < n:
            while right and stream[i] > stream[right[-1]]:
                right.pop()
            right.append(i)

    i = 0
    while i < n:
        if i - left_win >= 0:
            while left and left[0] <= i - left_win:
                left.popleft()
        while left and stream[i] > stream[left[-1]]:
            left.pop()
        left.append(i)

        if i + right_win < n:
            while right and right[0] <= i:
                right.popleft()
            j = i + right_win
            if j < n:
                while right and stream[j] > stream[right[-1]]:
                    right.pop()
                right.append(j)

        if stream[i] >= stream[left[0]] and (not right or stream[i] >= stream[right[0]]):
            if (i - start) >= min_chunk:
                chunks.append(stream[start:i])
                start = i + 1
                left.clear()
                right.clear()
                for j in range(1, right_win + 1):
                    if start + j < n:
                        while right and stream[start + j] > stream[right[-1]]:
                            right.pop()
                        right.append(start + j)

        if (i - start) >= max_chunk:
            chunks.append(stream[start:i])  
            start = i + 1
            left.clear()
            right.clear()
        i += 1

    if start < n:
        chunks.append(stream[start:n])    
    return chunks
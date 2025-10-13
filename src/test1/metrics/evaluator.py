import os, json, statistics

# 전체 메트릭 저장
def log_metrics(chunk_count, total_bytes, start_time, end_time, attempts, errors):
    metrics = {
        "chunk_count": chunk_count,
        "total_bytes": total_bytes,
        "avg_chunk_size": total_bytes / chunk_count,
        "elapsed_time": end_time - start_time,
        "attempts_total": attempts,
        "errors_total": errors,
        "chunking_speed": round(chunk_count / (end_time - start_time + 1e-9), 2)
    }
    with open("metrics/result.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))


# 청킹 결과 저장
def log_chunk_metrics(count, total_bytes, start_time, end_time):
    metrics = {
        "chunk_count": count,
        "total_bytes": total_bytes,
        "chunking_time": round(end_time - start_time, 4),
        "chunking_speed_MBps": round((total_bytes / 1024 / 1024) / (end_time - start_time), 2)
    }
    os.makedirs("metrics", exist_ok=True)
    with open("metrics/chunking_result.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))


# 복원 결과 저장
def log_restore_metrics(count, total_bytes, start_time, end_time):
    metrics = {
        "restored_chunks": count,
        "total_bytes": total_bytes,
        "restore_time": round(end_time - start_time, 4),
        "restore_speed_MBps": round((total_bytes / 1024 / 1024) / (end_time - start_time), 2)
    }
    os.makedirs("metrics", exist_ok=True)
    with open("metrics/restore_result.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))

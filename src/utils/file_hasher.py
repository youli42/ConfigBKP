from pathlib import Path
import hashlib


def sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def file_info(filepath: Path) -> dict:
    stat = filepath.stat()
    return {
        "sha256": sha256(filepath),
        "size": stat.st_size,
        "mtime": str(stat.st_mtime),
    }

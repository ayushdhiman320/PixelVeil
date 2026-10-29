
import hashlib
from pathlib import Path


def calculate_sha256(input_path: str) -> str:
    sha256 = hashlib.sha256()

    with Path(input_path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(block)

    return sha256.hexdigest()

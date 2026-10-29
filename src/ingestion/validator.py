
from pathlib import Path

from PIL import Image, UnidentifiedImageError


MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MiB


def validate_image(input_path: str) -> dict:
    path = Path(input_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if not path.is_file():
        raise ValueError("Input path must point to a file.")

    size = path.stat().st_size

    if size == 0:
        raise ValueError("Input file is empty.")

    if size > MAX_FILE_SIZE:
        raise ValueError("Input exceeds the 100 MiB size limit.")

    with path.open("rb") as file:
        signature = file.read(3)

    if len(signature) < 3 or signature[:2] != b"\xff\xd8":
        raise ValueError(
            "Input does not have a JPEG start-of-image signature."
        )

    try:
        with Image.open(path) as image:
            detected_format = image.format
            dimensions = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(
            f"Pillow could not verify the image: {exc}"
        ) from exc

    if detected_format != "JPEG":
        raise ValueError(
            f"Expected JPEG content; detected {detected_format!r}."
        )

    return {
        "path": str(path),
        "filename": path.name,
        "size_bytes": size,
        "detected_format": detected_format,
        "dimensions": {
            "width": dimensions[0],
            "height": dimensions[1],
        },
        "validation_status": "passed",
    }


import hashlib
import subprocess
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def extract_thumbnail(input_path: str, output_dir: str = "outputs/thumbnails") -> dict:
    source = Path(input_path).resolve()
    destination_dir = Path(output_dir).resolve()

    try:
        result = subprocess.run(
            ["exiftool", "-b", "-ThumbnailImage", str(source)],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return {"status": "error", "error": "ExifTool was not found."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Thumbnail extraction timed out."}

    if result.returncode != 0:
        return {
            "status": "error",
            "error": result.stderr.decode("utf-8", errors="replace").strip()
            or f"ExifTool exited with code {result.returncode}.",
        }

    thumbnail_bytes = result.stdout

    if not thumbnail_bytes:
        return {
            "status": "not_found",
            "message": "No extractable embedded thumbnail was returned.",
        }

    try:
        from io import BytesIO

        with Image.open(BytesIO(thumbnail_bytes)) as image:
            if image.format != "JPEG":
                return {
                    "status": "invalid",
                    "error": f"Thumbnail is {image.format}, not JPEG.",
                }

            dimensions = {
                "width": image.width,
                "height": image.height,
            }
            image.verify()

    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return {
            "status": "invalid",
            "error": f"Extracted thumbnail could not be verified: {exc}",
        }

    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / f"{source.stem}_thumbnail.jpg"
    output_path.write_bytes(thumbnail_bytes)

    return {
        "status": "success",
        "path": str(output_path),
        "size_bytes": len(thumbnail_bytes),
        "sha256": hashlib.sha256(thumbnail_bytes).hexdigest(),
        "dimensions": dimensions,
        "format": "JPEG",
    }

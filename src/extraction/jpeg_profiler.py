
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def profile_jpeg(input_path: str) -> dict:
    path = Path(input_path).resolve()

    try:
        with Image.open(path) as image:
            if image.format != "JPEG":
                raise ValueError("Input content is not a JPEG.")

            icc_profile = image.info.get("icc_profile")
            exif_bytes = image.info.get("exif")

            quantization = getattr(image, "quantization", None)
            quantization_summary = {}

            if quantization:
                for table_id, values in quantization.items():
                    quantization_summary[str(table_id)] = {
                        "coefficient_count": len(values),
                        "minimum": min(values),
                        "maximum": max(values),
                    }

            return {
                "status": "success",
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "progressive": bool(
                    image.info.get("progressive")
                    or image.info.get("progression")
                ),
                "has_icc_profile": icc_profile is not None,
                "icc_profile_bytes": (
                    len(icc_profile) if icc_profile is not None else 0
                ),
                "has_exif_block": exif_bytes is not None,
                "exif_block_bytes": (
                    len(exif_bytes) if exif_bytes is not None else 0
                ),
                "quantization_tables": quantization_summary,
            }

    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return {
            "status": "error",
            "error": str(exc),
        }

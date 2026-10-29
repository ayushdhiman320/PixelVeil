
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.ingestion.validator import validate_image
from src.ingestion.hashing import calculate_sha256
from src.extraction.metadata_extractor import (
    extract_metadata,
    get_exiftool_version,
)
from src.extraction.jpeg_profiler import profile_jpeg
from src.extraction.thumbnail_extractor import extract_thumbnail
from src.extraction.jpeg_marker_analyzer import analyze_jpeg_markers


def build_report(input_path: str) -> dict:
    validation = validate_image(input_path)
    resolved_path = validation["path"]

    report = {
        "project": "PixelVeil",
        "phase": 1,
        "report_created_utc": datetime.now(timezone.utc).isoformat(),
        "input": validation,
        "integrity": {
            "hash_algorithm": "SHA-256",
            "original_sha256": calculate_sha256(resolved_path),
        },
        "tools": {
            "python": sys.version.split()[0],
            "pillow": None,
            "exiftool": None,
        },
        "metadata_extraction": {},
        "jpeg_profile": {},
        "warnings": [],
    }

    try:
        import PIL
        report["tools"]["pillow"] = PIL.__version__
    except ImportError:
        report["warnings"].append("Pillow version could not be determined.")

    try:
        report["tools"]["exiftool"] = get_exiftool_version()
    except (OSError, subprocess.SubprocessError) as exc:
        report["warnings"].append(
            f"Could not determine ExifTool version: {exc}"
        )

    report["metadata_extraction"] = extract_metadata(resolved_path)
    report["jpeg_profile"] = profile_jpeg(resolved_path)
    report["thumbnail_extraction"] = extract_thumbnail(resolved_path)
    report["jpeg_structure"] = analyze_jpeg_markers(resolved_path)

    if report["metadata_extraction"]["status"] != "success":
        report["warnings"].append("Metadata extraction did not complete.")

    if report["jpeg_profile"]["status"] != "success":
        report["warnings"].append("JPEG profiling did not complete.")

    if report["thumbnail_extraction"]["status"] == "error":
        report["warnings"].append("Thumbnail extraction encountered an error.")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PixelVeil Phase 1: JPEG inspection and reporting."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the JPEG image to inspect.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the JSON report.",
    )
    args = parser.parse_args()

    try:
        report = build_report(args.input)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_dir = Path("outputs/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        source_name = Path(args.input).stem
        output_path = output_dir / f"{source_name}_report.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[OK] PixelVeil Phase 1 inspection completed.")
    print(f"Input:  {report['input']['filename']}")
    print(f"SHA256: {report['integrity']['original_sha256']}")
    print(f"Metadata status: {report['metadata_extraction']['status']}")
    print(f"JPEG profile status: {report['jpeg_profile']['status']}")
    print(f"Report: {output_path}")

    if report["warnings"]:
        print(f"Warnings: {len(report['warnings'])}")
        for warning in report["warnings"]:
            print(f"  - {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


import json
import subprocess
from pathlib import Path


def get_exiftool_version() -> str:
    result = subprocess.run(
        ["exiftool", "-ver"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return result.stdout.strip()


def extract_metadata(input_path: str) -> dict:
    path = str(Path(input_path).resolve())

    try:
        result = subprocess.run(
            [
                "exiftool",
                "-json",
                "-G1",
                "-a",
                "-s",
                "-struct",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "tags": {},
            "error": "ExifTool executable was not found.",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "tags": {},
            "error": "ExifTool timed out after 30 seconds.",
        }

    if result.returncode != 0:
        return {
            "status": "error",
            "tags": {},
            "error": result.stderr.strip()
            or f"ExifTool exited with code {result.returncode}.",
        }

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "tags": {},
            "error": f"Could not parse ExifTool JSON: {exc}",
        }

    if not parsed or not isinstance(parsed[0], dict):
        return {
            "status": "error",
            "tags": {},
            "error": "ExifTool returned no metadata record.",
        }

    tags = dict(parsed[0])
    tags.pop("SourceFile", None)

    return {
        "status": "success",
        "tag_count": len(tags),
        "tags": tags,
        "stderr": result.stderr.strip() or None,
    }

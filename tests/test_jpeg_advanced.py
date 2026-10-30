
import json
import subprocess

import pytest
from PIL import Image

from src.extraction.jpeg_marker_analyzer import analyze_jpeg_markers
from src.extraction.jpeg_profiler import profile_jpeg


@pytest.fixture
def progressive_jpeg(tmp_path):
    path = tmp_path / "progressive.jpg"

    image = Image.new("RGB", (640, 480), (100, 150, 200))
    image.save(path, format="JPEG", quality=90, progressive=True)

    return path


def test_progressive_jpeg_has_multiple_scans(progressive_jpeg):
    result = analyze_jpeg_markers(str(progressive_jpeg))

    assert result["status"] == "success"
    assert result["scan_count"] > 1
    assert result["end_of_image_found"] is True


def test_progressive_jpeg_dimensions(progressive_jpeg):
    result = analyze_jpeg_markers(str(progressive_jpeg))

    assert result["dimensions"] == {
        "width": 640,
        "height": 480,
    }


def test_progressive_jpeg_marker_inventory(progressive_jpeg):
    result = analyze_jpeg_markers(str(progressive_jpeg))

    names = [marker["name"] for marker in result["markers"]]

    assert names[0] == "SOI"
    assert names[-1] == "EOI"
    assert names.count("SOS") > 1


def test_pillow_and_marker_dimensions_match(progressive_jpeg):
    marker_result = analyze_jpeg_markers(str(progressive_jpeg))
    pillow_result = profile_jpeg(str(progressive_jpeg))

    assert marker_result["dimensions"]["width"] == pillow_result["width"]
    assert marker_result["dimensions"]["height"] == pillow_result["height"]


def test_exiftool_and_marker_dimensions_match(progressive_jpeg):
    result = subprocess.run(
        [
            "exiftool",
            "-json",
            "-ImageWidth",
            "-ImageHeight",
            str(progressive_jpeg),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )

    metadata = json.loads(result.stdout)[0]
    marker_result = analyze_jpeg_markers(str(progressive_jpeg))

    assert marker_result["dimensions"]["width"] == metadata["ImageWidth"]
    assert marker_result["dimensions"]["height"] == metadata["ImageHeight"]

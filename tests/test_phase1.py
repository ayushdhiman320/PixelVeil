
import hashlib

import pytest
from PIL import Image

from src.ingestion.validator import validate_image
from src.ingestion.hashing import calculate_sha256
from src.extraction.jpeg_profiler import profile_jpeg
from src.extraction.jpeg_marker_analyzer import analyze_jpeg_markers


@pytest.fixture
def valid_jpeg(tmp_path):
    path = tmp_path / "test_image.jpg"
    image = Image.new("RGB", (320, 240), (100, 150, 200))
    image.save(path, format="JPEG", quality=90)
    return path


def test_validate_valid_jpeg(valid_jpeg):
    result = validate_image(str(valid_jpeg))

    assert result["validation_status"] == "passed"
    assert result["detected_format"] == "JPEG"
    assert result["dimensions"] == {"width": 320, "height": 240}


def test_validate_missing_file(tmp_path):
    missing = tmp_path / "missing.jpg"

    with pytest.raises(FileNotFoundError):
        validate_image(str(missing))


def test_reject_non_jpeg(valid_jpeg, tmp_path):
    png_path = tmp_path / "not_a_jpeg.jpg"
    Image.new("RGB", (32, 32)).save(png_path, format="PNG")

    with pytest.raises(ValueError):
        validate_image(str(png_path))


def test_sha256_matches_standard_library(valid_jpeg):
    expected = hashlib.sha256(valid_jpeg.read_bytes()).hexdigest()

    assert calculate_sha256(str(valid_jpeg)) == expected


def test_jpeg_profile(valid_jpeg):
    result = profile_jpeg(str(valid_jpeg))

    assert result["status"] == "success"
    assert result["format"] == "JPEG"
    assert result["width"] == 320
    assert result["height"] == 240


def test_marker_analysis(valid_jpeg):
    result = analyze_jpeg_markers(str(valid_jpeg))

    assert result["status"] == "success"
    assert result["dimensions"] == {"width": 320, "height": 240}
    assert result["component_count"] == 3
    assert result["scan_count"] >= 1
    assert result["end_of_image_found"] is True
    assert any(
        marker["name"] == "SOI" for marker in result["markers"]
    )
    assert any(
        marker["name"] == "EOI" for marker in result["markers"]
    )


def test_marker_analyzer_rejects_invalid_signature(tmp_path):
    invalid_path = tmp_path / "invalid.jpg"
    invalid_path.write_bytes(b"not a jpeg file")

    result = analyze_jpeg_markers(str(invalid_path))

    assert result["status"] == "invalid"


def test_missing_eoi_marker(valid_jpeg):
    data = valid_jpeg.read_bytes()

    # Remove the final JPEG End of Image marker.
    assert data.endswith(b"\xff\xd9")
    valid_jpeg.write_bytes(data[:-2])

    result = analyze_jpeg_markers(str(valid_jpeg))

    assert result["status"] == "incomplete"
    assert result["end_of_image_found"] is False
    assert any("End of Image" in warning for warning in result["warnings"])


def test_truncated_jpeg_segment(tmp_path):
    path = tmp_path / "truncated.jpg"

    # SOI followed by an APP0 segment claiming 16 bytes,
    # but only 4 bytes are available.
    path.write_bytes(
        b"\xff\xd8"
        b"\xff\xe0"
        b"\x00\x10"
        b"\x4a\x46"
    )

    result = analyze_jpeg_markers(str(path))

    assert result["status"] == "incomplete"
    assert any("Truncated segment" in warning for warning in result["warnings"])


def test_invalid_segment_length(tmp_path):
    path = tmp_path / "invalid_length.jpg"

    # APP0 segment with an invalid length of 1.
    path.write_bytes(
        b"\xff\xd8"
        b"\xff\xe0"
        b"\x00\x01"
    )

    result = analyze_jpeg_markers(str(path))

    assert result["status"] == "incomplete"
    assert any("Invalid segment length" in warning for warning in result["warnings"])


def test_missing_scan_data(valid_jpeg):
    data = valid_jpeg.read_bytes()

    # Keep SOI but remove all remaining JPEG content.
    valid_jpeg.write_bytes(data[:2])

    result = analyze_jpeg_markers(str(valid_jpeg))

    assert result["status"] == "incomplete"
    assert result["scan_count"] == 0
    assert result["end_of_image_found"] is False


def test_marker_offsets_are_valid(valid_jpeg):
    data = valid_jpeg.read_bytes()

    result = analyze_jpeg_markers(str(valid_jpeg))

    for marker in result["markers"]:
        assert 0 <= marker["offset"] < len(data)

    assert result["markers"][0]["name"] == "SOI"
    assert result["markers"][-1]["name"] == "EOI"

from src.extraction.jpeg_marker_analyzer import analyze_jpeg_markers


def build_jpeg_with_restart_markers():
    """
    Creates a minimal JPEG-like byte stream containing:
    SOI, DQT, SOF0, SOS, RST0, RST1 and EOI.
    """

    return bytes.fromhex(
        """
        FFD8

        FFC0 000B
        08 0010 0010 01 01 11 00

        FFDA 0008
        01 01 00 00 3F 00

        11 22 33
        FFD0
        44 55 66
        FFD1
        77 88 99

        FFD9
        """
    )


def test_restart_markers_are_detected(tmp_path):
    path = tmp_path / "restart.jpg"
    path.write_bytes(build_jpeg_with_restart_markers())

    result = analyze_jpeg_markers(str(path))

    names = [marker["name"] for marker in result["markers"]]

    assert "RST0" in names
    assert "RST1" in names


def test_restart_markers_do_not_increase_scan_count(tmp_path):
    path = tmp_path / "restart.jpg"
    path.write_bytes(build_jpeg_with_restart_markers())

    result = analyze_jpeg_markers(str(path))

    assert result["scan_count"] == 1


def test_restart_markers_preserve_eoi_detection(tmp_path):
    path = tmp_path / "restart.jpg"
    path.write_bytes(build_jpeg_with_restart_markers())

    result = analyze_jpeg_markers(str(path))

    assert result["end_of_image_found"] is True
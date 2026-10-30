
from src.extraction.consistency_analyzer import analyze_consistency


def test_matching_metadata():
    metadata = {
        "status": "success",
        "tags": {
            "IFD0:Make": "Canon",
            "IFD0:Model": "Canon EOS 600D",
            "File:ImageWidth": 5184,
            "IFD0:ImageWidth": 5184,
        },
    }

    result = analyze_consistency(metadata)

    assert result["comparisons"]["camera_make"]["status"] == "not_comparable"
    assert result["comparisons"]["image_width"]["status"] == "consistent"


def test_metadata_mismatch():
    metadata = {
        "status": "success",
        "tags": {
            "File:ImageWidth": 5184,
            "IFD0:ImageWidth": 4000,
        },
    }

    result = analyze_consistency(metadata)

    assert result["comparisons"]["image_width"]["status"] == "mismatch"


def test_missing_metadata():
    metadata = {
        "status": "success",
        "tags": {},
    }

    result = analyze_consistency(metadata)

    assert result["comparisons"]["camera_make"]["status"] == "missing"


def test_unavailable_metadata():
    metadata = {"status": "error"}

    result = analyze_consistency(metadata)

    assert result["status"] == "unavailable"


def test_capture_date_precision_compatibility():
    metadata = {
        "status": "success",
        "tags": {
            "ExifIFD:DateTimeOriginal": "2025:04:02 01:35:54",
            "ExifIFD:CreateDate": "2025:04:02 01:35:54",
            "XMP-xmp:CreateDate": "2025:04:02 01:35:54",
            "IPTC:DateCreated": "2025:04:02",
        },
    }

    result = analyze_consistency(metadata)

    assert (
        result["comparisons"]["capture_datetime"]["status"]
        == "consistent"
    )


def test_modification_timezone_suffix():
    metadata = {
        "status": "success",
        "tags": {
            "IFD0:ModifyDate": "2025:04:09 22:55:43",
            "XMP-xmp:ModifyDate": "2025:04:09 22:55:43+05:30",
            "XMP-xmp:MetadataDate": "2025:04:09 22:55:43+05:30",
        },
    }

    result = analyze_consistency(metadata)

    assert (
        result["comparisons"]["modification_datetime"]["status"]
        == "consistent"
    )

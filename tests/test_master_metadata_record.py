
from src.metadata.master_metadata_record import (
    build_master_metadata_record,
)


def test_mmr_preserves_multiple_lens_sources():
    metadata = {
        "status": "success",
        "tags": {
            "IFD0:Make": "Canon",
            "IFD0:Model": "Canon EOS 600D",
            "ExifIFD:LensModel": "EF-S55-250mm f/4-5.6 IS II",
            "XMP-aux:Lens": "EF-S55-250mm f/4-5.6 IS II",
        },
    }

    consistency = {
        "comparisons": {
            "lens_model": {"status": "consistent"},
        },
        "summary": {
            "consistent": 1,
            "mismatches": 0,
            "missing": 0,
            "not_comparable": 0,
        },
    }

    record = build_master_metadata_record(
        metadata,
        consistency,
    )

    assert record["camera"]["make"] == "Canon"
    assert record["camera"]["model"] == "Canon EOS 600D"

    assert (
        record["lens"]["model"]
        == "EF-S55-250mm f/4-5.6 IS II"
    )

    assert (
        record["fields"]["lens_model"]["source_count"]
        == 2
    )

    assert (
        record["fields"]["lens_model"]["consistency"]
        == "consistent"
    )


def test_mmr_handles_missing_metadata():
    metadata = {
        "status": "success",
        "tags": {},
    }

    consistency = {
        "comparisons": {},
        "summary": {},
    }

    record = build_master_metadata_record(
        metadata,
        consistency,
    )

    assert record["camera"]["make"] is None
    assert record["camera"]["model"] is None
    assert record["fields"]["camera_make"]["source_count"] == 0


def test_mmr_preserves_conflicting_values():
    metadata = {
        "status": "success",
        "tags": {
            "ExifIFD:LensModel": "Lens A",
            "XMP-aux:Lens": "Lens B",
        },
    }

    consistency = {
        "comparisons": {
            "lens_model": {"status": "mismatch"},
        },
        "summary": {},
    }

    record = build_master_metadata_record(
        metadata,
        consistency,
    )

    lens = record["fields"]["lens_model"]

    assert lens["value"] == "Lens A"
    assert lens["source_count"] == 2
    assert lens["consistency"] == "mismatch"
    assert lens["sources"][1]["raw_value"] == "Lens B"

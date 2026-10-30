
from datetime import datetime, timezone


# Each field has a preferred source followed by alternative sources.
FIELD_MAPPING = {
    "camera_make": {
        "category": "camera",
        "field": "make",
        "sources": ["IFD0:Make"],
        "consistency_group": "camera_make",
    },
    "camera_model": {
        "category": "camera",
        "field": "model",
        "sources": ["IFD0:Model"],
        "consistency_group": "camera_model",
    },
    "lens_model": {
        "category": "lens",
        "field": "model",
        "sources": [
            "ExifIFD:LensModel",
            "XMP-aux:Lens",
            "XMP-exifEX:LensModel",
        ],
        "consistency_group": "lens_model",
    },
    "capture_datetime": {
        "category": "capture",
        "field": "datetime",
        "sources": [
            "ExifIFD:DateTimeOriginal",
            "ExifIFD:CreateDate",
            "XMP-xmp:CreateDate",
            "IPTC:DateCreated",
        ],
        "consistency_group": "capture_datetime",
    },
    "modification_datetime": {
        "category": "modification",
        "field": "datetime",
        "sources": [
            "IFD0:ModifyDate",
            "XMP-xmp:ModifyDate",
            "XMP-xmp:MetadataDate",
        ],
        "consistency_group": "modification_datetime",
    },
    "image_width": {
        "category": "image",
        "field": "width",
        "sources": [
            "IFD0:ImageWidth",
            "File:ImageWidth",
            "ExifIFD:ExifImageWidth",
        ],
        "consistency_group": "image_width",
    },
    "image_height": {
        "category": "image",
        "field": "height",
        "sources": [
            "IFD0:ImageHeight",
            "File:ImageHeight",
            "ExifIFD:ExifImageHeight",
        ],
        "consistency_group": "image_height",
    },
    "icc_profile": {
        "category": "color_profile",
        "field": "description",
        "sources": [
            "ICC_Profile:ProfileDescription",
            "XMP-photoshop:ICCProfileName",
        ],
        "consistency_group": "icc_profile_description",
    },
}


def build_field_record(
    tags,
    field_definition,
    consistency_comparisons,
):
    observed_sources = []

    for tag in field_definition["sources"]:
        if tag not in tags:
            continue

        raw_value = tags[tag]

        if raw_value is None or raw_value == "":
            continue

        observed_sources.append({
            "source_tag": tag,
            "raw_value": raw_value,
        })

    preferred_value = (
        observed_sources[0]["raw_value"]
        if observed_sources else None
    )

    group_name = field_definition["consistency_group"]

    consistency = consistency_comparisons.get(
        group_name, {}
    ).get("status", "unavailable")

    return {
        "value": preferred_value,
        "preferred_source": (
            observed_sources[0]["source_tag"]
            if observed_sources else None
        ),
        "sources": observed_sources,
        "source_count": len(observed_sources),
        "consistency": consistency,
    }


def build_master_metadata_record(
    metadata_result,
    consistency_result,
    input_info=None,
    jpeg_profile=None,
):
    tags = metadata_result.get("tags", {})
    comparisons = consistency_result.get(
        "comparisons", {}
    )

    record = {
        "schema_version": "1.0",
        "record_type": "PixelVeil Master Metadata Record",
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "image": {
            "filename": (
                input_info.get("filename")
                if input_info else None
            ),
            "sha256": (
                input_info.get("sha256")
                if input_info else None
            ),
            "format": (
                input_info.get("detected_format")
                if input_info else None
            ),
            "width": None,
            "height": None,
        },

        "camera": {
            "make": None,
            "model": None,
        },

        "lens": {
            "model": None,
        },

        "capture": {
            "datetime": None,
        },

        "modification": {
            "datetime": None,
        },

        "color_profile": {
            "description": None,
        },

        "jpeg": {
            "progressive": (
                jpeg_profile.get("progressive")
                if jpeg_profile else None
            ),
            "mode": (
                jpeg_profile.get("mode")
                if jpeg_profile else None
            ),
            "has_icc_profile": (
                jpeg_profile.get("has_icc_profile")
                if jpeg_profile else None
            ),
        },

        "metadata_status": metadata_result.get(
            "status", "unknown"
        ),

        "consistency_summary": consistency_result.get(
            "summary", {}
        ),

        "fields": {},
    }

    for field_name, definition in FIELD_MAPPING.items():
        field_record = build_field_record(
            tags,
            definition,
            comparisons,
        )

        category = definition["category"]
        field = definition["field"]

        record[category][field] = field_record["value"]

        record["fields"][field_name] = field_record

    return record

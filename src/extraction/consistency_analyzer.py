
from datetime import datetime



COMPARISON_GROUPS = {
    "camera_make": {
        "IFD0:Make": "exact",
    },
    "camera_model": {
        "IFD0:Model": "exact",
    },
    "capture_datetime": {
        "ExifIFD:DateTimeOriginal": "datetime",
        "ExifIFD:CreateDate": "datetime",
        "XMP-xmp:CreateDate": "datetime",
        "IPTC:DateCreated": "date",
    },
    "modification_datetime": {
        "IFD0:ModifyDate": "datetime",
        "XMP-xmp:ModifyDate": "datetime",
        "XMP-xmp:MetadataDate": "datetime",
    },
    "lens_model": {
        "ExifIFD:LensModel": "exact",
        "XMP-aux:Lens": "exact",
        "XMP-exifEX:LensModel": "exact",
    },
    "image_width": {
        "File:ImageWidth": "numeric",
        "IFD0:ImageWidth": "numeric",
        "ExifIFD:ExifImageWidth": "numeric",
    },
    "image_height": {
        "File:ImageHeight": "numeric",
        "IFD0:ImageHeight": "numeric",
        "ExifIFD:ExifImageHeight": "numeric",
    },
    "icc_profile_description": {
        "ICC_Profile:ProfileDescription": "exact",
        "XMP-photoshop:ICCProfileName": "exact",
    },
}


def normalize_value(value, value_type):
    if value is None or value == "":
        return None

    if value_type == "exact":
        return str(value).strip().casefold()

    if value_type == "numeric":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    if value_type == "date":
        text = str(value).strip()

        try:
            return datetime.strptime(
                text[:10], "%Y:%m:%d"
            ).date().isoformat()
        except ValueError:
            return None

    if value_type == "datetime":
        text = str(value).strip()

        # ExifTool commonly represents dates using colons.
        # Convert the date portion to ISO format.
        if len(text) >= 19:
            text = (
                text[:4] + "-" + text[5:7] + "-"
                + text[8:10] + "T" + text[11:]
            )

        try:
            parsed = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )

            # Compare local clock time consistently.
            # Preserve original timezone in raw_value.
            return parsed.replace(
                tzinfo=None
            ).isoformat(timespec="seconds")

        except ValueError:
            return None

    return str(value).strip()



def analyze_consistency(metadata_result):
    if metadata_result.get("status") != "success":
        return {
            "status": "unavailable",
            "reason": "Metadata extraction was unsuccessful.",
            "comparisons": {},
            "summary": {
                "consistent": 0,
                "mismatches": 0,
                "missing": 0,
                "not_comparable": 0,
            },
        }

    tags = metadata_result.get("tags", {})

    comparisons = {}
    summary = {
        "consistent": 0,
        "mismatches": 0,
        "missing": 0,
        "not_comparable": 0,
    }

    for group_name, fields in COMPARISON_GROUPS.items():
        observed = {}

        for tag, value_type in fields.items():
            if tag not in tags:
                continue

            normalized = normalize_value(tags[tag], value_type)

            if normalized is not None:
                observed[tag] = {
                    "raw_value": tags[tag],
                    "normalized_value": normalized,
                }

        if len(observed) == 0:
            status = "missing"

        elif len(observed) == 1:
            status = "not_comparable"

        else:
            values = [
                item["normalized_value"]
                for item in observed.values()
            ]

            if group_name == "capture_datetime":
                # Compare only the calendar date because IPTC DateCreated
                # does not contain a time component.
                dates = [value[:10] for value in values]

                if all(value == dates[0] for value in dates):
                    status = "consistent"
                else:
                    status = "mismatch"

            elif all(value == values[0] for value in values):
                status = "consistent"

            else:
                status = "mismatch"

        summary_key = {
            "consistent": "consistent",
            "mismatch": "mismatches",
            "missing": "missing",
            "not_comparable": "not_comparable",
        }[status]

        summary[summary_key] += 1

        comparisons[group_name] = {
            "status": status,
            "observed_sources": observed,
            "available_source_count": len(observed),
            "expected_source_count": len(fields),
        }

    return {
        "status": "success",
        "method": "cross-source metadata comparison",
        "comparisons": comparisons,
        "summary": summary,
        "interpretation": (
            "A mismatch indicates disagreement between available "
            "metadata values. It does not independently establish "
            "image manipulation or authenticity."
        ),
    }

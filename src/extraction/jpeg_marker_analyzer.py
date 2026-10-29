
from pathlib import Path


STANDALONE_MARKERS = {
    0x01,  # TEM
    *range(0xD0, 0xD8),  # Restart markers
}

SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}

MARKER_NAMES = {
    0xD8: "SOI",
    0xD9: "EOI",
    0xDA: "SOS",
    0xDB: "DQT",
    0xC4: "DHT",
    0xDD: "DRI",
    0xFE: "COM",
    0xCC: "DAC",
}


def analyze_jpeg_markers(input_path: str) -> dict:
    path = Path(input_path)
    data = path.read_bytes()

    if len(data) < 4 or data[:2] != b"\xFF\xD8":
        return {
            "status": "invalid",
            "error": "Missing JPEG Start of Image marker.",
        }

    markers = []
    warnings = []
    position = 2
    reached_eoi = False
    in_scan = False
    width = None
    height = None
    component_count = None
    quantization_tables = []
    scan_count = 0

    while position < len(data):
        # Outside entropy-coded data, expect a marker prefix.
        if not in_scan:
            if data[position] != 0xFF:
                warnings.append(
                    f"Unexpected byte outside scan at offset {position}."
                )
                break

            while position < len(data) and data[position] == 0xFF:
                position += 1

            if position >= len(data):
                warnings.append("Truncated marker at end of file.")
                break

            marker = data[position]
            position += 1
        else:
            # Inside scan data, ordinary bytes are compressed image data.
            while position < len(data):
                if data[position] != 0xFF:
                    position += 1
                    continue

                if position + 1 >= len(data):
                    warnings.append("Truncated marker in scan data.")
                    position = len(data)
                    break

                next_byte = data[position + 1]

                # FF00 is byte-stuffing; it represents data, not a marker.
                if next_byte == 0x00:
                    position += 2
                    continue

                # Restart markers are embedded in scan data.
                if 0xD0 <= next_byte <= 0xD7:
                    markers.append({
                        "marker": f"FF{next_byte:02X}",
                        "name": f"RST{next_byte - 0xD0}",
                        "offset": position,
                        "segment_length": 0,
                    })
                    position += 2
                    continue

                # A non-stuffed, non-restart marker ends the scan data.
                in_scan = False
                break

            if position >= len(data):
                break

            continue

        marker_offset = position - 2
        marker_name = MARKER_NAMES.get(
            marker, f"MARKER_FF{marker:02X}"
        )

        if marker == 0xD9:
            markers.append({
                "marker": "FFD9",
                "name": "EOI",
                "offset": marker_offset,
                "segment_length": 0,
            })
            reached_eoi = True
            break

        if marker == 0xD8:
            warnings.append(
                f"Unexpected additional SOI marker at offset {marker_offset}."
            )
            markers.append({
                "marker": "FFD8",
                "name": "SOI",
                "offset": marker_offset,
                "segment_length": 0,
            })
            continue

        if marker in STANDALONE_MARKERS:
            markers.append({
                "marker": f"FF{marker:02X}",
                "name": marker_name,
                "offset": marker_offset,
                "segment_length": 0,
            })
            continue

        if position + 2 > len(data):
            warnings.append(
                f"Missing segment length for marker FF{marker:02X}."
            )
            break

        segment_length = int.from_bytes(
            data[position:position + 2], "big"
        )

        if segment_length < 2:
            warnings.append(
                f"Invalid segment length for marker FF{marker:02X}."
            )
            break

        segment_end = position + segment_length

        if segment_end > len(data):
            warnings.append(
                f"Truncated segment for marker FF{marker:02X}."
            )
            break

        payload = data[position + 2:segment_end]

        markers.append({
            "marker": f"FF{marker:02X}",
            "name": marker_name,
            "offset": marker_offset,
            "segment_length": segment_length,
        })

        if marker == 0xDB:  # DQT: Define Quantization Table
            table_position = 0
            while table_position < len(payload):
                info = payload[table_position]
                table_position += 1

                precision = info >> 4
                table_id = info & 0x0F
                value_size = 2 if precision == 1 else 1

                if precision not in (0, 1):
                    warnings.append("Invalid DQT precision.")
                    break

                table_bytes = 64 * value_size
                if table_position + table_bytes > len(payload):
                    warnings.append("Truncated DQT table.")
                    break

                quantization_tables.append({
                    "table_id": table_id,
                    "precision_bits": 16 if precision == 1 else 8,
                    "coefficient_count": 64,
                })
                table_position += table_bytes

        if marker in SOF_MARKERS:
            if len(payload) < 6:
                warnings.append("Truncated JPEG frame header.")
            else:
                height = int.from_bytes(payload[1:3], "big")
                width = int.from_bytes(payload[3:5], "big")
                component_count = payload[5]

        if marker == 0xDA:  # SOS: Start of Scan
            scan_count += 1
            in_scan = True

        position = segment_end

    if not reached_eoi:
        warnings.append("JPEG End of Image marker was not found.")

    if scan_count == 0:
        warnings.append("No Start of Scan marker was found.")

    if width is None or height is None:
        warnings.append("No valid JPEG frame dimensions were found.")

    return {
        "status": "success" if reached_eoi and scan_count > 0 else "incomplete",
        "file_size_bytes": len(data),
        "dimensions": {
            "width": width,
            "height": height,
        },
        "component_count": component_count,
        "scan_count": scan_count,
        "marker_count": len(markers),
        "quantization_tables": quantization_tables,
        "markers": markers,
        "end_of_image_found": reached_eoi,
        "warnings": warnings,
    }

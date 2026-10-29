"""Complete physical source partition; handles never grant evidence authority."""

from hashlib import sha256
import json
import re

POLICY = "blank_line_units_v1"
CONTRACT = "qualified_source_handles_v2"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def catalog(body, source_identity):
    raw = body.encode("utf-8")
    if not raw.strip(b" \t\r\n"):
        raise ValueError("Nonblank source required")
    # Only CR, LF and CRLF terminate physical lines. Unicode separators are text.
    lines = re.findall(rb"[^\r\n]*(?:\r\n|\r|\n|$)", raw)
    starts, cursor, seen, previous_blank = [0], 0, False, False
    for line in filter(None, lines):
        blank = not line.rstrip(b"\r\n").strip(b" \t")
        if not blank and seen and previous_blank:
            starts.append(cursor)
        seen = seen or not blank
        previous_blank = blank
        cursor += len(line)
    units = []
    for ordinal, (start, end) in enumerate(zip(starts, starts[1:] + [len(raw)]), 1):
        selected = raw[start:end]
        units.append(
            {
                "unit_id": f"u{ordinal}",
                "start_byte": start,
                "end_byte": end,
                "sha256": sha256(selected).hexdigest(),
                "text": selected.decode("utf-8"),
            }
        )
    result = {
        "selector_policy": POLICY,
        "source_identity": source_identity,
        "body_sha256": sha256(raw).hexdigest(),
        "units": units,
    }
    return result | {"catalog_sha256": digest(result)}


def validate_catalog(value):
    try:
        body = "".join(unit["text"] for unit in value["units"])
        if catalog(body, value["source_identity"]) != value:
            raise ValueError("Source catalog differs from its committed partition")
        return body
    except (KeyError, TypeError, UnicodeError) as exc:
        raise ValueError("Invalid source catalog") from exc

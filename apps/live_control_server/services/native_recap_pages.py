"""Page an exact native source span after Core reauthorizes the selection."""

from hashlib import sha256
import json

from apps.live_control_server.services.native_graph_inspection import (
    InspectionUnavailable,
    SESSION_RECAP_SOURCE,
    inspect,
)


def read_native_recap_page(request, principal, *, max_chars, continuation=None):
    """Recheck the pinned source and bind continuation to its verified bytes."""
    if max_chars < 1:
        raise ValueError("invalid recap page size")
    if request.selection.kind != "source":
        raise ValueError("recap pagination requires an exact source selection")

    packet = inspect(
        request, principal, include_source_span=True,
        source_classification=SESSION_RECAP_SOURCE,
    )
    source = packet.get("source")
    if not source:
        raise InspectionUnavailable("native_inspection_source_unavailable")

    text = source["text"]

    def cursor(offset):
        payload = json.dumps({
            "selection": request.model_dump(mode="json"),
            "source_revision_id": source["source_revision_id"],
            "span_sha256": source["span_sha256"],
            "offset": offset,
        }, sort_keys=True, separators=(",", ":"))
        return f"{offset}:{sha256(payload.encode()).hexdigest()}"

    start = 0
    if continuation is not None:
        offset, separator, _ = continuation.partition(":")
        if not separator or not offset.isascii() or not offset.isdecimal() or len(offset) > len(str(len(text))):
            raise ValueError("invalid recap continuation")
        start = int(offset)
        if not 0 < start < len(text) or continuation != cursor(start):
            raise ValueError("invalid recap continuation")

    end = min(start + max_chars, len(text))
    return {
        **packet,
        "source": {**source, "text": text[start:end]},
        "next_continuation": cursor(end) if end < len(text) else None,
    }

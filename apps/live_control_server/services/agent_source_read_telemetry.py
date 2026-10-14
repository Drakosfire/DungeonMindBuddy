"""Bounded source-read receipts, excluding returned source bodies."""

import hashlib
from collections.abc import Mapping
from typing import Any

BATCH_V1 = "dmb_read_graph_source_batch_v1"
BATCH_V2 = "dmb_internal_read_graph_source_batch_v2"
READ_SCHEMA = "dmb_world_graph_source_anchor_read_v1"
MAX_READS = 8


def summarize_batch_source_reads(packet: Mapping[str, Any]):
    schema = packet.get("schema")
    reads = packet.get("reads")
    if (
        not isinstance(schema, str)
        or schema not in {BATCH_V1, BATCH_V2}
        or not isinstance(reads, list)
    ):
        return {}, []
    metadata: dict[str, Any] = {
        "sourceReadCount": len(reads),
        "sourceReadTelemetryTruncated": len(reads) > MAX_READS,
    }
    anchors = []
    for index, item in enumerate(reads[:MAX_READS]):
        if not isinstance(item, Mapping):
            metadata[f"sourceRead{index}"] = {"malformed": "true"}
            continue
        result = item.get("result") if schema == BATCH_V2 else item
        if not isinstance(result, Mapping):
            metadata[f"sourceRead{index}"] = {"malformed": "true"}
            continue
        receipt = item.get("receipt") if schema == BATCH_V2 else None
        receipt = receipt if isinstance(receipt, Mapping) else {}
        record = {}
        for key in (
            "anchorId",
            "evidenceRefId",
            "sourceArtifactId",
            "sourceSpanRefId",
            "outcome",
            "code",
        ):
            if isinstance(result.get(key), str):
                record[key] = result[key][:256]
        for key in (
            "source_read_id",
            "source_revision_id",
            "source_revision_sha256",
            "graph_revision",
        ):
            if isinstance(receipt.get(key), str):
                record[key] = receipt[key][:256]
        if isinstance(result.get("contentSha256"), str):
            record["reportedContentSha256"] = result["contentSha256"][:256]
        snapshot = result.get("snapshot")
        if isinstance(snapshot, Mapping) and isinstance(
            snapshot.get("revisionId"), str
        ):
            record.setdefault("graph_revision", snapshot["revisionId"][:256])
        content = result.get("content")
        known_schema = result.get("schema") == READ_SCHEMA
        anchor = result.get("anchorId")
        outcome = result.get("outcome")
        record["knownSourceReadSchema"] = "true" if known_schema else "false"
        record["opened"] = (
            "true"
            if (
                known_schema
                and isinstance(anchor, str)
                and anchor
                and isinstance(content, str)
                and content
                and isinstance(outcome, str)
                and outcome in {"enough", "partial", "truncated"}
            )
            else "false"
        )
        if isinstance(content, str):
            record["returnedChars"] = str(len(content))
            try:
                record["returnedContentSha256"] = hashlib.sha256(
                    content.encode()
                ).hexdigest()
            except UnicodeEncodeError:
                record["opened"] = "false"
                record["malformedContentEncoding"] = "true"
        if isinstance(result.get("truncated"), bool):
            record["truncated"] = "true" if result["truncated"] else "false"
        anchor = result.get("anchorId")
        if isinstance(anchor, str) and anchor:
            anchors.append(anchor)
        metadata[f"sourceRead{index}"] = record
    return metadata, list(dict.fromkeys(anchors))

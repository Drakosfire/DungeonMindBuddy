"""Bounded source-read receipts, excluding returned source bodies."""

import hashlib
from collections.abc import Mapping
from typing import Any

BATCH_V1 = "dmb_read_graph_source_batch_v1"
BATCH_V2 = "dmb_internal_read_graph_source_batch_v2"
READ_SCHEMA = "dmb_world_graph_source_anchor_read_v1"
MAX_READS = 8
MAX_ID_CHARS = 256


def _usable_identity(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > MAX_ID_CHARS:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _store_field(record, key, value, omitted):
    if not isinstance(value, str):
        return
    if not _usable_identity(value):
        omitted.append(key)
        record[key + "Sha256"] = hashlib.sha256(
            value.encode("utf-8", errors="surrogatepass")
        ).hexdigest()
        return
    record[key] = value


def summarize_requested_anchor_ids(values: list[Any]) -> dict[str, Any]:
    ids, omitted = [], []
    malformed = False
    for value in values[:MAX_READS]:
        if _usable_identity(value):
            ids.append(value)
        elif isinstance(value, str):
            omitted.append(
                hashlib.sha256(
                    value.encode("utf-8", errors="surrogatepass")
                ).hexdigest()
            )
        else:
            malformed = True
    result = {"anchorIds": ids}
    if omitted:
        result["anchorIdsOmittedSha256"] = omitted
    if len(values) > MAX_READS or omitted or malformed:
        result["anchorIdsTruncated"] = True
    return result


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
        omitted = []
        for key in (
            "anchorId",
            "evidenceRefId",
            "sourceArtifactId",
            "sourceSpanRefId",
            "outcome",
            "code",
        ):
            _store_field(record, key, result.get(key), omitted)
        for key in (
            "source_read_id",
            "source_revision_id",
            "source_revision_sha256",
            "graph_revision",
        ):
            _store_field(record, key, receipt.get(key), omitted)
        _store_field(
            record, "reportedContentSha256", result.get("contentSha256"), omitted
        )
        snapshot = result.get("snapshot")
        if isinstance(snapshot, Mapping) and isinstance(
            snapshot.get("revisionId"), str
        ):
            if "graph_revision" not in record and "graph_revisionSha256" not in record:
                _store_field(record, "graph_revision", snapshot["revisionId"], omitted)
        content = result.get("content")
        known_schema = result.get("schema") == READ_SCHEMA
        anchor = result.get("anchorId")
        outcome = result.get("outcome")
        record["knownSourceReadSchema"] = "true" if known_schema else "false"
        record["opened"] = (
            "true"
            if (
                known_schema
                and _usable_identity(anchor)
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
        if _usable_identity(anchor):
            anchors.append(anchor)
        if omitted:
            record["identityFieldsOmitted"] = ",".join(omitted)
        metadata[f"sourceRead{index}"] = record
    return metadata, list(dict.fromkeys(anchors))

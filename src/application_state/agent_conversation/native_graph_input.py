"""Exact transient Graph record proof for a native producing request.

Original packets are checked against durable operation digests. Only complete
records present in the actual final tool outputs can supply target evidence.
Nothing here retrieves, persists, or grants authority to historical tool text.
"""
import json
from hashlib import sha256
from uuid import UUID

from .rules_authority_types import canonical_bytes
from .source_writer_output import strict_json
from .types import ValidatedGraphOperationEventV1

MAX_PACKET_PROOF_BYTES = 1050000
_RUNTIME_FIELDS = {"retrievalSessionId", "addedClaimIds", "claimLedger"}
_HOST_METADATA = {"reviewId", "contributionId", "publicationRevisionId",
                  "sourceArtifactId", "sourceRevisionId", "evidenceRefIds"}
_TARGETS = (("attributes", "assertion", "assertionId"),
            ("reviewedSourceObservations", "assertion", "assertionId"),
            ("relationships", "relationship", "edgeId"))


def _tool_outputs(body, *, tool_name="expand_graph_retrieval"):
    calls, outputs = {}, {}
    if isinstance(body.get("input"), list) and "messages" not in body:
        for item in body["input"]:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call":
                identity = item.get("call_id")
                if not isinstance(identity, str) or identity in calls:
                    raise ValueError("Graph proof has ambiguous tool calls")
                calls[identity] = item.get("name")
            elif item.get("type") == "function_call_output":
                identity = item.get("call_id")
                if identity not in calls or identity in outputs:
                    raise ValueError("Graph proof has unmatched tool output")
                outputs[identity] = item.get("output")
    elif isinstance(body.get("messages"), list) and "input" not in body:
        for item in body["messages"]:
            if not isinstance(item, dict):
                continue
            if item.get("role") == "assistant":
                for call in item.get("tool_calls") or []:
                    identity = call.get("id")
                    if not isinstance(identity, str) or identity in calls:
                        raise ValueError("Graph proof has ambiguous tool calls")
                    calls[identity] = call.get("function", {}).get("name")
            elif item.get("role") == "tool":
                identity = item.get("tool_call_id")
                if identity not in calls or identity in outputs:
                    raise ValueError("Graph proof has unmatched tool output")
                outputs[identity] = item.get("content")
    else:
        raise ValueError("Graph proof has an unknown provider shape")
    return [strict_json(raw) for identity, raw in outputs.items()
            if calls[identity] == tool_name]


def _complete_page_records(pages):
    records, fragments = {}, {}
    for page in pages:
        for record in page.get("records", []):
            path = tuple(record.get("path", ()))
            if "value" in record:
                value = record["value"]
                if path in records and records[path] != value:
                    raise ValueError("Graph proof has conflicting complete records")
                records[path] = value
            elif record.get("requiresReassembly"):
                parts = fragments.setdefault(path, {})
                offset = record["start"]
                if offset in parts and parts[offset] != record:
                    raise ValueError("Graph proof has conflicting fragments")
                parts[offset] = record
    for path, parts in fragments.items():
        parts = sorted(parts.values(), key=lambda part: part["start"])
        offset, chunks = 0, []
        for part in parts:
            if part["start"] != offset:
                break
            chunks.append(part["fragment"])
            offset = part["end"]
        else:
            text = "".join(chunks)
            if (parts and offset == parts[0]["length"]
                    and sha256(text.encode()).hexdigest() == parts[0]["sha256"]):
                value = text if parts[0]["fragmentEncoding"] == "text" else strict_json(text)
                if path in records and records[path] != value:
                    raise ValueError("Graph proof has conflicting reassembled records")
                records[path] = value
    return records


def _initial_closures(turn, authorization, body):
    assembled = turn.graph_context_receipt.assembled_input
    expected = assembled.dispatched_packet_sha256
    if expected is None:
        return ()
    marker = "Turn capability policy (runtime-enforced; also required on tool calls):"
    packets = []
    for message in body.get("input", body.get("messages", [])):
        if not isinstance(message, dict) or message.get("role") != "system":
            continue
        content = message.get("content")
        texts = [content] if isinstance(content, str) else [part.get("text")
            for part in content or [] if isinstance(part, dict)]
        for text in texts:
            if not isinstance(text, str) or marker not in text:
                continue
            start = text.index(marker) + len(marker)
            raw = text[start:].lstrip()
            _, end = json.JSONDecoder().raw_decode(raw)
            policy = strict_json(raw[:end])
            packet = policy.get("initialClaimPacket")
            if isinstance(packet, dict):
                packets.append(packet)
    if not packets:
        return ()
    if len(packets) != 1 or sha256(canonical_bytes(packets[0])).hexdigest() != expected:
        raise ValueError("Native initial Graph packet differs from its frozen receipt")
    closures = []
    for row in packets[0].get("claimLedger", []):
        target, refs = row.get("claim_id"), row.get("evidence_ref_ids")
        kind = ("assertion" if target in assembled.dispatched_assertion_ids
                and target in authorization.included_assertion_ids else
                "relationship" if target in assembled.dispatched_relationship_ids
                and target in authorization.included_relationship_ids else None)
        if (kind is not None and isinstance(refs, list) and refs
                and all(isinstance(ref, str) and ref for ref in refs)
                and row.get("revision_id") == turn.graph_context_receipt.graph_authority.graph_revision
                and set(refs) <= set(assembled.dispatched_evidence_ref_ids)
                and set(refs) <= set(authorization.included_evidence_ref_ids)):
            closures.append((kind, target, tuple(sorted(set(refs)))))
    return tuple(closures)


def producing_graph_closures(turn, authorization, proof):
    """Join exact original records, final presentation, and admitted membership."""
    packets = proof.graph_packets
    if len(packets) > 64 or sum(len(raw.encode()) for raw in packets.values()) > MAX_PACKET_PROOF_BYTES:
        raise ValueError("Native Graph packet proof exceeds its bound")
    from .types import PlanJevWriterAuthorizedV1
    if isinstance(authorization, PlanJevWriterAuthorizedV1):
        from .plan_jev_graph_packet import producing_closures
        return producing_closures(turn, authorization, proof)
    events = {event.event_id: event for event in turn.graph_context_execution.events
              if isinstance(event, ValidatedGraphOperationEventV1)}
    included = set(authorization.included_graph_event_ids)
    if not set(packets) <= included:
        raise ValueError("Native Graph proof includes an unexposed operation")
    body = strict_json(proof.prepared_request_json)
    payloads = _tool_outputs(body)
    page_groups = {}
    for row in payloads:
        if (isinstance(row, dict) and row.get("schema") in
                {"dmb_graph_tool_page_v1", "dmb_graph_tool_overview_v1"}):
            result_id = row.get("resultId")
            if not isinstance(result_id, str):
                raise ValueError("Native Graph page has no result identity")
            page_groups.setdefault(result_id, []).append(row)
    records = [_complete_page_records(pages) for pages in page_groups.values()]
    closures = set(_initial_closures(turn, authorization, body))
    for identity, raw in packets.items():
        if not isinstance(identity, UUID):
            raise ValueError("Native Graph proof has a noncanonical operation identity")
        event = events.get(identity)
        original = strict_json(raw)
        if (event is None or sha256(canonical_bytes(original)).hexdigest() != event.result_packet_sha256
                or event.graph_revision != turn.graph_context_receipt.graph_authority.graph_revision):
            raise ValueError("Native Graph proof differs from its durable operation")
        full = any(isinstance(payload, dict)
            and {key: value for key, value in payload.items() if key not in _RUNTIME_FIELDS} == original
            for payload in payloads)
        bundles = [payload for payload in payloads if isinstance(payload, dict)
            and payload.get("schema") == "dmb_graph_evidence_packet_v1"
            and payload.get("bundleId") == str(identity)]
        refs = sorted({anchor["evidenceRefId"] for anchor in original.get("sourceAnchors", [])})
        handles = {ref: f"e{i}" for i, ref in enumerate(refs, 1)}
        for key, kind, id_key in _TARGETS:
            for index, row in enumerate(original.get(key, [])):
                target, evidence = row.get(id_key), row.get("evidenceRefIds")
                if (not isinstance(target, str) or not isinstance(evidence, list) or not evidence
                        or not all(isinstance(ref, str) and ref for ref in evidence)):
                    continue
                expected = {k: v for k, v in row.items() if k not in _HOST_METADATA}
                expected["evidence"] = [handles.get(ref) for ref in evidence]
                bundled = any(item.get("kind") == key and
                    {k: v for k, v in item.get("record", {}).items() if k != "evidenceRefIds"} == expected
                    and item.get("record", {}).get("evidenceRefIds", evidence) == evidence
                    for bundle in bundles for item in bundle.get("records", []))
                present = full or any(group.get((key, index)) == row for group in records) or bundled
                targets = event.assertion_ids if kind == "assertion" else event.relationship_ids
                if (present and target in targets and target in (
                        authorization.included_assertion_ids if kind == "assertion"
                        else authorization.included_relationship_ids)
                        and set(evidence) <= set(event.evidence_ref_ids)
                        and set(evidence) <= set(authorization.included_evidence_ref_ids)):
                    closures.add((kind, target, tuple(sorted(set(evidence)))))
    return tuple(sorted(closures))

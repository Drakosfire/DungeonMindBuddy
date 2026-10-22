"""Plan tool-free writer projection; host proof stays outside model context.

Exact Graph packets are matched to durable operation digests. Opened source text
comes once from protected current-attempt capture, never another corpus request.
IDs/hashes/revisions bind host authority; compact evidence handles link the model
records and passages. Display source labels grant no factual claim authority.
"""
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from .plan_jev_decision import _owner
from .source_writer_output import strict_json
from .rules_authority_types import canonical_bytes, canonical_sha256
from .context_trace import TraceSourcePassage, TraceSourceReuse, TraceFailure

SCHEMA = "dmb_plan_jev_writer_frame_v1"
_METADATA = {"reviewId", "contributionId", "publicationRevisionId", "sourceArtifactId", "sourceRevisionId", "evidenceRefIds"}
_TARGETS = (("attributes", "assertion", "assertionId"), ("reviewedSourceObservations", "assertion", "assertionId"),
            ("relationships", "relationship", "edgeId"))


@dataclass(frozen=True)
class PlanWriterProjection:
    frame: dict
    closures: tuple
    graph_event_ids: tuple
    source_event_ids: tuple
    assertion_ids: tuple
    relationship_ids: tuple
    evidence_ref_ids: tuple


def _source_trace(turn, trace):
    if (not isinstance(trace, dict) or trace.get("world_id") != turn.world_id
            or trace.get("conversation_id") != str(turn.conversation_id) or trace.get("turn_id") != str(turn.turn_id)
            or type(trace.get("attempt")) is not int or trace["attempt"] != turn.attempt
            or trace.get("capture_status") != "recording"):
        raise ValueError("Plan writer requires its complete current-attempt capture")
    return [(TraceSourceReuse if row.get("kind") == "source_passage_reuse" else TraceSourcePassage).model_validate(row)
            for row in trace.get("observations", []) if row.get("kind") in {"source_passage", "source_passage_reuse"}]


def project(turn, proof, trace):
    from . import types as t
    receipt, execution = _owner(turn)
    if (not isinstance(proof, dict) or set(proof) != {
            "graph_packets", "source_names", "plan_markdown", "session_evidence", "dialogue"}):
        raise ValueError("Plan writer requires its complete host evidence proof")
    markdown, sessions, dialogue = proof["plan_markdown"], proof["session_evidence"], proof["dialogue"]
    if not isinstance(markdown, str) or sha256(markdown.encode()).hexdigest() != receipt.plan_basis.content_sha256:
        raise ValueError("Plan writer text differs from its exact committed Plan")
    if (not isinstance(dialogue, list) or any(not isinstance(row, dict) or set(row) != {"role", "content"}
            or row["role"] not in {"user", "assistant"} or not isinstance(row["content"], str) for row in dialogue)):
        raise ValueError("Plan writer dialogue must be reference-only conversation messages")
    if not isinstance(sessions, list):
        raise ValueError("Plan writer session evidence must be explicit")
    frozen_sessions = {(ref.object_id, ref.revision): ref.content_sha256 for ref in turn.provenance.supporting_work
                       if ref.kind == "session_evidence_v1"}
    supplied = {}
    for session in sessions:
        if not isinstance(session, dict) or session.get("world_id") != turn.world_id:
            raise ValueError("Plan writer session evidence has a foreign owner")
        key = (session.get("run_id"), str(session.get("review_revision")))
        body = {k: v for k, v in session.items() if k != "sha256"}
        if key in supplied or session.get("sha256") != canonical_sha256(body):
            raise ValueError("Plan writer session evidence is changed or repeated")
        supplied[key] = session["sha256"]
    if supplied != frozen_sessions:
        raise ValueError("Plan writer session notes/reflections differ from frozen provenance")
    packets = proof["graph_packets"]
    if not isinstance(packets, dict):
        raise ValueError("Plan writer requires exact Graph packet bytes")
    operations = {e.event_id: e for e in execution.events if isinstance(e, t.ValidatedGraphOperationEventV3)}
    originals = []
    seen_operations = set()
    refs = set()
    for identity, raw in packets.items():
        event_id = UUID(identity) if isinstance(identity, str) else identity
        if event_id in seen_operations or not isinstance(raw, str):
            raise ValueError("Plan writer repeats or changes a Graph packet identity")
        seen_operations.add(event_id)
        event = operations.get(event_id)
        original = strict_json(raw)
        snapshot = original.get("snapshot", {}) if isinstance(original, dict) else {}
        if (event is None or not isinstance(original, dict) or canonical_sha256(original) != event.result_packet_sha256
                or event.graph_revision != receipt.graph_authority.graph_revision
                or snapshot.get("revisionId") != receipt.graph_authority.graph_revision
                or snapshot.get("worldId") != receipt.graph_authority.native_world_id):
            raise ValueError("Plan writer Graph bytes differ from their durable operation/snapshot")
        originals.append((event_id, event, original))
        refs.update(event.evidence_ref_ids)
    originals.sort(key=lambda item: str(item[0]))
    handles = {ref: f"e{index}" for index, ref in enumerate(sorted(refs))}
    records, closures, assertions, relationships, entities = [], set(), set(), set(), []
    record_indexes = {}
    incomplete_closure = False
    for _, event, original in originals:
        indexes = set()
        for node in original.get("nodes", []):
            label = {key: node[key] for key in ("nodeId", "label", "kind") if key in node}
            if label and label not in entities:
                entities.append(label)
        anchors = {row.get("evidenceRefId") for row in original.get("sourceAnchors", [])}
        for key, kind, id_key in _TARGETS:
            for row in original.get(key, []):
                target, evidence = row.get(id_key), row.get("evidenceRefIds")
                allowed = event.assertion_ids if kind == "assertion" else event.relationship_ids
                if (not isinstance(target, str) or target not in allowed or not isinstance(evidence, list)
                        or not evidence or any(not isinstance(ref, str) for ref in evidence)):
                    raise ValueError("Plan Graph record lacks its exact admitted evidence closure")
                if not set(evidence) <= set(event.evidence_ref_ids) & anchors:
                    # A bounded search may return a relationship whose source
                    # lies outside its evidence page. It is navigation only:
                    # never expose it as a citable record or abort other facts.
                    if not event.truncated and event.coverage_status == "complete":
                        raise ValueError("Plan Graph record lacks its exact admitted evidence closure")
                    incomplete_closure = True
                    continue
                qualified = {k: v for k, v in row.items() if k not in _METADATA | {id_key}}
                record = {"kind": kind, "target_id": target, "record": qualified,
                          "evidence": [handles[ref] for ref in evidence]}
                if record not in records:
                    records.append(record)
                indexes.add(records.index(record))
                closures.add((kind, target, tuple(sorted(set(evidence)))))
                (assertions if kind == "assertion" else relationships).add(target)
        record_indexes[event.event_id] = sorted(indexes)
    # Qualify each read with compact indexes into the one record table. Exact
    # assertion/relationship selectors remain there once, and in the host proof.
    retrievals = [{
        "records": record_indexes[event.event_id],
        "evidence": [handles[ref] for ref in event.evidence_ref_ids],
        "coverage": event.coverage_status, "truncated": event.truncated,
        "evidence_sufficiency": event.evidence_sufficiency_status,
    } for _, event, _ in originals]
    names = proof["source_names"]
    if not isinstance(names, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in names.items()):
        raise ValueError("Plan source labels must be host display metadata")
    sources = {e.event_id: e for e in execution.events if isinstance(e, t.SOURCE_PASSAGE_EVENTS)}
    passages, source_events, present, seen = [], set(), set(), set()
    for passage in _source_trace(turn, trace):
        if passage.evidence_ref_id not in handles:
            continue
        source = sources.get(passage.source_read_event_id)
        matches = [row for row in source.receipts if row.source_read_id == passage.source_read_id] if source else []
        if (len(matches) != 1 or passage.source_read_id in seen
                or (passage.world_id, passage.graph_revision) != (turn.world_id, receipt.graph_authority.graph_revision)):
            raise ValueError("Plan source capture differs from its actual receipt")
        read = matches[0]
        for field in ("anchor_id", "evidence_ref_id", "source_artifact_id", "source_revision_id", "content_sha256", "returned_chars", "outcome", "line_start", "line_end"):
            if getattr(read, field) != getattr(passage, field):
                raise ValueError("Plan captured passage changed its exact source identity")
        if sha256(passage.text.encode()).hexdigest() != read.content_sha256 or len(passage.text) != read.returned_chars:
            raise ValueError("Plan captured passage changed its source bytes")
        seen.add(passage.source_read_id)
        source_events.add(source.event_id)
        present.add(passage.evidence_ref_id)
        from .surface_source_answer import eligible, passage_handle
        passages.append({**({"passage_handle": passage_handle(read)} if eligible(read) else {}), "evidence": handles[passage.evidence_ref_id], "source_name": names.get(passage.source_read_id, "Opened source"),
            "text": passage.text, "line_start": passage.line_start, "line_end": passage.line_end, "outcome": passage.outcome, "truncated": read.truncated,
            "evidence_sufficiency": read.evidence_sufficiency_status})
    if not set(names) <= seen:
        raise ValueError("Plan source display label has no included captured passage")
    gaps = sorted({(failure.phase, failure.code)
        for row in trace.get("observations", []) if row.get("kind") == "failure"
        for failure in (TraceFailure.model_validate(row),)
        if failure.phase in {"graph_retrieval", "source_read"}})
    if incomplete_closure:
        gaps = sorted(set(gaps) | {("graph_retrieval", "incomplete_evidence_closure")})
    from .surface_evidence_answer import POLICY, plan_authored_sources, authored_frame_rows
    frame = {"schema": SCHEMA, "answer_policy": POLICY,
        "authored_sources": authored_frame_rows(plan_authored_sources(turn, markdown, sessions), sessions),
        "user_question": turn.user_text, "committed_plan_markdown": markdown,
        "session_evidence": [{key: session[key] for key in ("title", "run_id", "review_revision", "ended_at") if key in session}
            | {"sources": [{key: source[key] for key in ("kind", "element_id", "text") if key in source}
                for source in session.get("sources", [])]} for session in sessions],
        "dialogue_reference": dialogue, "retrieval_gaps": [{"operation": phase, "reason": code} for phase, code in gaps],
        "entity_index": entities, "retrieval_results": retrievals, "graph_records": records, "opened_passages": passages,
        "unopened_evidence": [handles[ref] for ref in sorted(refs - present)]}
    return PlanWriterProjection(frame, tuple(sorted(closures)), tuple(item[0] for item in originals),
        tuple(sorted(source_events, key=str)), tuple(sorted(assertions)), tuple(sorted(relationships)), tuple(sorted(refs)))


def frame_in_request(raw):
    body = strict_json(raw)
    if (not isinstance(body, dict) or "messages" in body or not isinstance(body.get("input"), list)
            or body.get("tools", []) != [] or body.get("tool_choice") not in (None, "none")):
        raise ValueError("Plan writer requires a tool-free Responses request")
    frames = []
    for item in body["input"]:
        if (not isinstance(item, dict) or set(item) - {"type", "role", "content"}
                or item.get("type") not in (None, "message") or item.get("role") not in {"system", "developer", "user", "assistant"}):
            raise ValueError("Plan writer request contains an unexpected transcript item")
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError("Plan writer frame requires exact text messages")
        if item["role"] != "user":
            continue
        try:
            value = strict_json(content)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and value.get("schema") == SCHEMA:
            frames.append(value)
    if len(frames) != 1:
        raise ValueError("Plan writer requires one exact evidence frame")
    return frames[0]


def verify_writer_input(turn, authorization, raw, proof, trace):
    from .types import PlanJevWriterAuthorizedV1
    from . import types as t
    projected = project(turn, proof, trace)
    body = strict_json(raw)
    if (not isinstance(authorization, PlanJevWriterAuthorizedV1)
            or body.get("model") != authorization.model
            or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
            or canonical_bytes(frame_in_request(raw)) != canonical_bytes(projected.frame)
            or authorization.frame_sha256 != canonical_sha256(projected.frame)
            or set(authorization.included_graph_event_ids) != set(projected.graph_event_ids)
            or set(t.included_passage_event_ids(authorization)) != set(projected.source_event_ids)
            or tuple(authorization.included_assertion_ids) != projected.assertion_ids
            or tuple(authorization.included_relationship_ids) != projected.relationship_ids
            or tuple(authorization.included_evidence_ref_ids) != projected.evidence_ref_ids):
        raise ValueError("Plan writer actual input differs from its exact opened evidence projection")
    return projected


def producing_closures(turn, authorization, proof):
    """Recheck admitted record bytes in the actual tool-free producing frame."""
    from . import types as t
    receipt, execution = _owner(turn)
    if not isinstance(authorization, t.PlanJevWriterAuthorizedV1):
        raise ValueError("Plan direct Graph support requires its own writer authorization")
    frame = frame_in_request(proof.prepared_request_json)
    if (sha256(proof.prepared_request_json.encode()).hexdigest() != authorization.envelope_sha256
            or canonical_sha256(frame) != authorization.frame_sha256):
        raise ValueError("Plan producing frame changed after exact admission")
    events = {e.event_id: e for e in execution.events if isinstance(e, t.ValidatedGraphOperationEventV3)}
    if not set(proof.graph_packets) <= set(authorization.included_graph_event_ids):
        raise ValueError("Plan producing Graph proof includes an unexposed operation")
    refs = set(authorization.included_evidence_ref_ids)
    handles = {ref: f"e{index}" for index, ref in enumerate(sorted(refs))}
    closures = set()
    for identity, raw in proof.graph_packets.items():
        event = events.get(identity)
        original = strict_json(raw)
        if event is None or canonical_sha256(original) != event.result_packet_sha256:
            raise ValueError("Plan producing record differs from its actual Graph operation")
        anchors = {row.get("evidenceRefId") for row in original.get("sourceAnchors", [])}
        for key, kind, id_key in _TARGETS:
            for row in original.get(key, []):
                target, evidence = row.get(id_key), row.get("evidenceRefIds")
                admitted = authorization.included_assertion_ids if kind == "assertion" else authorization.included_relationship_ids
                if (target not in admitted or not isinstance(evidence, list) or not evidence
                        or not set(evidence) <= refs & set(event.evidence_ref_ids) & anchors):
                    continue
                qualified = {k: v for k, v in row.items() if k not in _METADATA | {id_key}}
                record = {"kind": kind, "target_id": target, "record": qualified,
                    "evidence": [handles[ref] for ref in evidence]}
                if record not in frame.get("graph_records", []):
                    raise ValueError("Plan Graph target has no exact complete producing-frame record")
                closures.add((kind, target, tuple(sorted(set(evidence)))))
    return tuple(sorted(closures))

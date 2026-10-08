"""Bounded, immutable semantic correction of one exact recap candidate."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequest,
    RecapCandidateCorrectionRequestV2,
    RecapCandidateCorrectionRequestV3,
    RecapCandidateCorrectionRequestV4,
    RecapCandidateCorrectionRequestV5,
    RecapCandidateCorrectionRequestV6,
    RecapEvidenceRefSplit,
    RecapCandidateCorrectionResponse,
    RecapCandidateCorrectionResponseV2,
    RecapCandidateCorrectionResponseV3,
    RecapCandidateCorrectionResponseV4,
    RecapCandidateCorrectionResponseV5,
    RecapCandidateCorrectionResponseV6,
    RecapCandidateEdgeTuple,
    ExtractPromoteDiagnostic,
)
from apps.live_control_server.services.exact_run_evidence_correction import (
    _LIFECYCLE,
    _canonical_bytes,
    _reject,
    _sha,
    _write_child_candidate,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _assert_and_project_candidate_evidence,
    _assert_candidate_scope_matches_run,
    _load_frozen_span_index_for_resolved_run,
)
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
    get_extraction_run,
    update_extraction_run_status,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from apps.live_control_server.services.candidate_graph_admission import validate_candidate_document_integrity
from apps.live_control_server.models.candidate_graph_admission import CandidateAdmissionIntegrityError
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    kernel_kind_for_node_type,
    load_typed_candidate_graph,
)
from graph_memory.predicate_catalog import validate_edge_predicate
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET,
    edge_endpoint_kind_admission_reason,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)

DERIVATION = "operator_recap_semantic_candidate_correction_v1"
MANIFEST_SCHEMA = "dmb_recap_semantic_candidate_manifest_v1"
DERIVATION_V2 = "operator_recap_semantic_candidate_correction_v2"
MANIFEST_SCHEMA_V2 = "dmb_recap_semantic_candidate_manifest_v2"
DERIVATION_V3 = "operator_recap_semantic_candidate_correction_v3"
MANIFEST_SCHEMA_V3 = "dmb_recap_semantic_candidate_manifest_v3"
DERIVATION_V4 = "operator_recap_semantic_candidate_correction_v4"
MANIFEST_SCHEMA_V4 = "dmb_recap_semantic_candidate_manifest_v4"
DERIVATION_V5 = "operator_recap_semantic_candidate_correction_v5"
MANIFEST_SCHEMA_V5 = "dmb_recap_semantic_candidate_manifest_v5"
DERIVATION_V6 = "operator_recap_semantic_candidate_correction_v6"
MANIFEST_SCHEMA_V6 = "dmb_recap_semantic_candidate_manifest_v6"
PROFILE = "recap_category_v1@1.0"
MAX_EDGE_TUPLE_REPLACEMENTS = 7
EDGE_TUPLE_FIELDS = ("from_node_id", "relationship_type", "to_node_id", "label")


def _contains(value: object, target: str) -> bool:
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, list):
        return any(_contains(item, target) for item in value)
    return value == target


def _tuple_replacement_rejected(
    issues: list[tuple[int, str]],
) -> None:
    messages = {
        "malformed_operation": "operation shape is malformed",
        "malformed_tuple": "expected and replacement tuples must contain exactly four bounded string fields",
        "duplicate_edge_id": "edge ID is repeated in this request",
        "duplicate_target": "replacement creates a duplicate edge tuple",
        "unchanged_tuple": "replacement tuple is unchanged",
        "edge_missing_or_ambiguous": "edge ID is missing or ambiguous in the frozen candidate",
        "stale_preimage": "expected tuple does not match the frozen candidate",
        "endpoint_missing_or_ambiguous": "replacement endpoint must name one existing candidate node",
        "unknown_predicate": "relationship type is outside the candidate predicate catalog",
        "unmapped_predicate": "relationship type has no admitted native mapping",
        "predicate_vocabulary_missing": "relationship type is absent from the native vocabulary",
        "endpoint_kind_not_admitted": "native predicate does not admit these endpoint kinds",
        "native_vocabulary_unavailable": "native predicate vocabulary could not be verified",
    }
    stale_codes = {
        "duplicate_edge_id", "duplicate_target", "edge_missing_or_ambiguous", "stale_preimage",
    }
    status_code = 409 if any(code in stale_codes for _, code in issues) else 422
    diagnostics = [
        ExtractPromoteDiagnostic(
            code=f"edge_tuple_{code}",
            message=f"edgeTupleReplacements[{index}] {messages.get(code, 'operation is invalid')}",
            severity="error",
        )
        for index, code in issues
    ]
    raise ExtractPromoteError(
        "one or more edge tuple replacements were rejected; no child was created",
        code="recap_candidate_tuple_conflict" if status_code == 409 else "recap_candidate_tuple_invalid",
        status_code=status_code,
        diagnostics=diagnostics,
    )


def _plan_edge_tuple_replacements(parent: dict, replacements: object) -> dict[str, dict[str, str]]:
    """Validate a complete tuple batch before returning any candidate edits."""
    if (
        not isinstance(replacements, list)
        or not 1 <= len(replacements) <= MAX_EDGE_TUPLE_REPLACEMENTS
    ):
        raise _reject("edge tuple replacement batch exceeds bounded scope")
    edges = parent.get("edges")
    nodes = parent.get("nodes")
    if (
        not isinstance(edges, list)
        or any(not isinstance(edge, dict) for edge in edges)
        or not isinstance(nodes, list)
        or any(not isinstance(node, dict) for node in nodes)
    ):
        raise _reject("candidate edge tuple records are malformed")

    node_matches: dict[str, list[dict]] = {}
    for node in nodes:
        node_id = node.get("node_id")
        if isinstance(node_id, str):
            node_matches.setdefault(node_id, []).append(node)
    edge_matches: dict[str, list[dict]] = {}
    for edge in edges:
        edge_id = edge.get("edge_id")
        if isinstance(edge_id, str):
            edge_matches.setdefault(edge_id, []).append(edge)

    operation_indexes: dict[str, list[int]] = {}
    for index, operation in enumerate(replacements):
        if isinstance(operation, dict) and isinstance(operation.get("edge_id"), str):
            operation_indexes.setdefault(operation["edge_id"], []).append(index)
    duplicate_indexes = {
        index
        for indexes in operation_indexes.values()
        if len(indexes) > 1
        for index in indexes
    }

    try:
        vocabulary = CURRENT_V5_TARGET.world_object_loader()
    except Exception:
        vocabulary = None

    issues: list[tuple[int, str]] = []
    plans: dict[str, dict[str, str]] = {}
    plan_indexes: dict[str, int] = {}
    for index, operation in enumerate(replacements):
        if (
            not isinstance(operation, dict)
            or set(operation) != {"edge_id", "expected_tuple", "replacement_tuple"}
            or not isinstance(operation.get("edge_id"), str)
            or not operation["edge_id"].strip()
            or operation["edge_id"] != operation["edge_id"].strip()
        ):
            issues.append((index, "malformed_operation"))
            continue
        edge_id = operation["edge_id"]
        if index in duplicate_indexes:
            issues.append((index, "duplicate_edge_id"))

        try:
            expected = RecapCandidateEdgeTuple.model_validate(operation["expected_tuple"]).model_dump()
            target = RecapCandidateEdgeTuple.model_validate(operation["replacement_tuple"]).model_dump()
        except (TypeError, ValueError):
            issues.append((index, "malformed_tuple"))
            continue
        if expected == target:
            issues.append((index, "unchanged_tuple"))
            continue
        edge_records = edge_matches.get(edge_id, [])
        if len(edge_records) != 1:
            issues.append((index, "edge_missing_or_ambiguous"))
            continue
        edge = edge_records[0]
        if {field: edge.get(field) for field in EDGE_TUPLE_FIELDS} != expected:
            issues.append((index, "stale_preimage"))

        endpoint_nodes: list[dict] = []
        for field in ("from_node_id", "to_node_id"):
            matches = node_matches.get(target[field], [])
            if len(matches) != 1:
                issues.append((index, "endpoint_missing_or_ambiguous"))
                endpoint_nodes = []
                break
            endpoint_nodes.append(matches[0])

        predicate_issues = validate_edge_predicate(target["relationship_type"], None)
        if predicate_issues:
            issues.append((index, "unknown_predicate"))
        elif vocabulary is None:
            issues.append((index, "native_vocabulary_unavailable"))
        elif endpoint_nodes:
            reason = edge_endpoint_kind_admission_reason(
                buddy_predicate=target["relationship_type"],
                from_buddy_kind=kernel_kind_for_node_type(endpoint_nodes[0].get("node_type")),
                to_buddy_kind=kernel_kind_for_node_type(endpoint_nodes[1].get("node_type")),
                vocabulary=vocabulary,
            )
            reason_to_code = {
                "unmapped_predicate": "unmapped_predicate",
                "vocabulary_missing_predicate": "predicate_vocabulary_missing",
                "endpoint_kind_not_admitted": "endpoint_kind_not_admitted",
            }
            if reason is not None:
                issues.append((index, reason_to_code.get(reason, "endpoint_kind_not_admitted")))

        if index not in duplicate_indexes:
            plans[edge_id] = target
            plan_indexes[edge_id] = index

    # A rewrite batch may not create duplicate full tuples, including against
    # an unchanged edge in the same frozen candidate.
    final_tuples: dict[tuple[str, str, str, str], list[str]] = {}
    for edge in edges:
        edge_id = edge.get("edge_id")
        values = plans.get(edge_id, {field: edge.get(field) for field in EDGE_TUPLE_FIELDS})
        if all(isinstance(values.get(field), str) for field in EDGE_TUPLE_FIELDS):
            key = tuple(values[field] for field in EDGE_TUPLE_FIELDS)
            final_tuples.setdefault(key, []).append(edge_id if isinstance(edge_id, str) else "")
    for edge_ids in final_tuples.values():
        changed = [edge_id for edge_id in edge_ids if edge_id in plans]
        if len(edge_ids) > 1:
            for edge_id in changed:
                issues.append((plan_indexes[edge_id], "duplicate_target"))

    if issues:
        _tuple_replacement_rejected(issues)
    return plans


def _plan_evidence_span_replacements(
    parent: dict,
    replacements: object,
    *,
    max_operations: int = 1,
    allow_quote_only: bool = False,
) -> list[dict[str, Any]]:
    """Validate every exact evidence preimage before changing candidate bytes."""
    if (
        not isinstance(replacements, list)
        or not 1 <= len(replacements) <= max_operations
    ):
        raise _reject("evidence replacement batch exceeds bounded scope")
    expected_keys = {
        "record_kind", "record_id", "evidence_index", "expected_source_ref_id", "expected_source_artifact_id",
        "expected_source_span_ref_id", "replacement_source_span_ref_id",
        "expected_anchor_quotes", "replacement_anchor_quotes",
    }
    plans: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for operation in replacements:
        if not isinstance(operation, dict) or set(operation) != expected_keys:
            raise _reject("evidence replacement is malformed")
        record_kind = operation.get("record_kind")
        record_id = operation.get("record_id")
        evidence_index = operation.get("evidence_index")
        expected_source_ref_id = operation.get("expected_source_ref_id")
        expected_artifact = operation.get("expected_source_artifact_id")
        expected_span = operation.get("expected_source_span_ref_id")
        replacement_span = operation.get("replacement_source_span_ref_id")
        expected_quotes = operation.get("expected_anchor_quotes")
        replacement_quotes = operation.get("replacement_anchor_quotes")
        string_values = (record_id, expected_source_ref_id, expected_artifact, expected_span, replacement_span)
        if (
            not isinstance(record_kind, str) or record_kind not in {"node", "edge"}
            or type(evidence_index) is not int or evidence_index < 0
            or any(not isinstance(value, str) or not value or value != value.strip() or len(value) > 256 for value in string_values)
            or (expected_span == replacement_span and not allow_quote_only)
            or not isinstance(expected_quotes, list) or not 1 <= len(expected_quotes) <= 16
            or not isinstance(replacement_quotes, list) or not 1 <= len(replacement_quotes) <= 16
            or any(not isinstance(quote, str) or not quote or quote != quote.strip() or len(quote) > 4096 for quote in [*expected_quotes, *replacement_quotes])
            or (expected_span == replacement_span and expected_quotes == replacement_quotes)
        ):
            raise _reject("evidence replacement is malformed or unchanged")
        key = (record_kind, record_id, evidence_index)
        if key in seen:
            raise _reject("duplicate evidence replacement target")
        seen.add(key)
        collection_key, id_key = ("nodes", "node_id") if record_kind == "node" else ("edges", "edge_id")
        records = parent.get(collection_key)
        if not isinstance(records, list):
            raise _reject("candidate evidence holder collection is malformed")
        holders = [record for record in records if isinstance(record, dict) and record.get(id_key) == record_id]
        if len(holders) != 1:
            raise _reject("evidence holder is missing or ambiguous", status_code=409)
        refs = holders[0].get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, dict) for ref in refs):
            raise _reject("candidate evidence refs are malformed")
        if evidence_index >= len(refs):
            raise _reject("evidence ref is missing", status_code=409)
        evidence = refs[evidence_index]
        if (
            evidence.get("source_ref_id") != expected_source_ref_id
            or evidence.get("source_artifact_id") != expected_artifact
            or evidence.get("source_span_ref_id") != expected_span
            or evidence.get("anchor_quotes") != expected_quotes
        ):
            raise _reject("evidence preimage is stale", status_code=409)
        plans.append({
            "record_kind": record_kind,
            "record_id": record_id,
            "evidence_index": evidence_index,
            "replacement_source_span_ref_id": replacement_span,
            "replacement_anchor_quotes": replacement_quotes,
        })
    return plans


def _replay_evidence_ref_split(parent: dict, manifest: dict, source_bytes: bytes | None, span_bytes: bytes | None) -> dict:
    """Re-prove source pins, full-ref preimage, and each quote occurrence."""
    from graph_memory.anchor_quotes import find_anchor_quote_matches

    if set(manifest) != {"schema", "source_revision_sha256", "span_index_sha256", "evidence_ref_splits"}:
        raise _reject("evidence ref split manifest is malformed")
    operations = manifest["evidence_ref_splits"]
    if not isinstance(operations, list) or len(operations) != 1:
        raise _reject("evidence ref split exceeds bounded scope")
    operation = operations[0]
    if not isinstance(operation, dict) or set(operation) != {"record_kind", "record_id", "evidence_index", "expected_evidence_ref_sha256", "parts"}:
        raise _reject("evidence ref split operation is malformed")
    if not isinstance(operation["parts"], list) or any(not isinstance(part, dict) or set(part) != {"source_span_ref_id", "quote_indices"} for part in operation["parts"]):
        raise _reject("evidence ref split parts are malformed")
    try:
        split = RecapEvidenceRefSplit.model_validate(operation)
    except (TypeError, ValueError) as exc:
        raise _reject("evidence ref split operation is malformed") from exc
    if (
        not isinstance(source_bytes, bytes) or not isinstance(span_bytes, bytes)
        or _sha(source_bytes) != manifest["source_revision_sha256"]
        or _sha(span_bytes) != manifest["span_index_sha256"]
    ):
        raise _reject("evidence ref split source/index pin changed", status_code=409)
    try:
        index = json.loads(span_bytes)
        source_lines = source_bytes.decode("utf-8").splitlines()
    except (ValueError, UnicodeError) as exc:
        raise _reject("evidence ref split source/index is unreadable") from exc
    collection_key, id_key = ("nodes", "node_id") if split.record_kind == "node" else ("edges", "edge_id")
    records = parent.get(collection_key)
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise _reject("evidence ref split holder collection is malformed")
    matches = [record for record in records if record.get(id_key) == split.record_id]
    if len(matches) != 1:
        raise _reject("evidence ref split holder is missing or ambiguous", status_code=409)
    refs = matches[0].get("evidence_refs")
    if not isinstance(refs, list) or split.evidence_index >= len(refs) or not isinstance(refs[split.evidence_index], dict):
        raise _reject("evidence ref split preimage is missing", status_code=409)
    original = refs[split.evidence_index]
    if _sha(_canonical_bytes(original)) != split.expected_evidence_ref_sha256:
        raise _reject("evidence ref split preimage is stale", status_code=409)
    quotes = original.get("anchor_quotes")
    if not isinstance(quotes, list) or any(not isinstance(quote, str) or not quote.strip() for quote in quotes):
        raise _reject("evidence ref split original quotes are malformed")
    if [i for part in split.parts for i in part.quote_indices] != list(range(len(quotes))):
        raise _reject("evidence ref split must partition every quote occurrence")
    if (
        not isinstance(index, dict) or index.get("schema") != "dmb_source_span_index_v1"
        or index.get("content_sha256") != manifest["source_revision_sha256"]
        or not isinstance(original.get("source_span_ref_id"), str) or not original["source_span_ref_id"].strip()
        or any(not isinstance(index.get(key), str) or not index[key].strip() for key in ("source_artifact_id", "source_ref_id"))
        or index.get("source_artifact_id") != original.get("source_artifact_id")
        or index.get("source_ref_id") != original.get("source_ref_id")
        or not isinstance(index.get("spans"), list)
        or any(not isinstance(span, dict) for span in index["spans"])
    ):
        raise _reject("evidence ref split index authority changed", status_code=409)
    outputs = []
    # The original ref and both output spans must resolve uniquely in the same index.
    for span_id in [original.get("source_span_ref_id"), *(part.source_span_ref_id for part in split.parts)]:
        spans = [span for span in index["spans"] if span.get("source_span_id") == span_id]
        if len(spans) != 1:
            raise _reject("evidence ref split span is missing or ambiguous", status_code=409)
        span = spans[0]
        if any(span.get(key) != index.get(key) for key in ("content_sha256", "source_artifact_id", "source_ref_id")):
            raise _reject("evidence ref split span has foreign authority", status_code=409)
        start, end = span.get("start_line"), span.get("end_line")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(source_lines):
            raise _reject("evidence ref split span bounds are invalid")
    for part in split.parts:
        span = next(span for span in index["spans"] if span.get("source_span_id") == part.source_span_ref_id)
        paragraph = "\n".join(source_lines[span["start_line"] - 1:span["end_line"]])
        selected = [quotes[i] for i in part.quote_indices]
        if any(not find_anchor_quote_matches(paragraph, [quote]) for quote in selected):
            raise _reject("evidence ref split quote is not literal in its assigned span")
        output = copy.deepcopy(original)
        output["source_span_ref_id"] = part.source_span_ref_id
        output["anchor_quotes"] = selected
        if "source_anchor_id" in output:
            output["source_anchor_id"] = f"anchor:{part.source_span_ref_id}"
        if "label" in output:
            output["label"] = part.source_span_ref_id
        outputs.append(output)
    child = copy.deepcopy(parent)
    holder = next(record for record in child[collection_key] if record[id_key] == split.record_id)
    holder["evidence_refs"][split.evidence_index:split.evidence_index + 1] = outputs
    return child


def replay_candidate(parent: dict, manifest: dict, *, source_bytes: bytes | None = None, span_bytes: bytes | None = None) -> dict:
    """Reconstruct one bounded correction request; never patch arbitrary JSON."""
    if not isinstance(parent, dict) or not isinstance(manifest, dict):
        raise _reject("semantic candidate replay input is malformed")
    if manifest.get("schema") == MANIFEST_SCHEMA_V6:
        return _replay_evidence_ref_split(parent, manifest, source_bytes, span_bytes)
    v3 = manifest.get("schema") == MANIFEST_SCHEMA_V3
    v5 = manifest.get("schema") == MANIFEST_SCHEMA_V5
    v4 = manifest.get("schema") == MANIFEST_SCHEMA_V4
    v2 = manifest.get("schema") == MANIFEST_SCHEMA_V2
    expected_keys = (
        {"schema", "evidence_span_replacements"}
        if v4 or v5
        else {"schema", "edge_tuple_replacements"}
        if v3
        else {"schema", "node_description_replacements", "omitted_edge_ids"}
    )
    if v2:
        expected_keys.add("session_action_replacements")
    if set(manifest) != expected_keys or manifest.get("schema") not in {
        MANIFEST_SCHEMA, MANIFEST_SCHEMA_V2, MANIFEST_SCHEMA_V3, MANIFEST_SCHEMA_V4,
        MANIFEST_SCHEMA_V5,
    }:
        raise _reject("semantic candidate manifest is malformed")
    replacements = manifest.get("node_description_replacements", [])
    omitted = manifest.get("omitted_edge_ids", [])
    actions = manifest.get("session_action_replacements", [])
    edge_tuple_replacements = manifest.get("edge_tuple_replacements", [])
    evidence_span_replacements = manifest.get("evidence_span_replacements", [])
    if (
        not isinstance(replacements, list) or (not v3 and len(replacements) > 1)
        or not isinstance(omitted, list) or (not v3 and len(omitted) > 1)
        or not isinstance(actions, list) or (len(actions) != 1 if v2 else bool(actions))
        or (v3 and (not isinstance(edge_tuple_replacements, list) or not 1 <= len(edge_tuple_replacements) <= MAX_EDGE_TUPLE_REPLACEMENTS))
        or (v4 and (not isinstance(evidence_span_replacements, list) or len(evidence_span_replacements) != 1))
        or (v5 and (not isinstance(evidence_span_replacements, list) or not 1 <= len(evidence_span_replacements) <= 7))
        or (not (v3 or v4 or v5) and not replacements and not omitted and not actions)
    ):
        raise _reject("semantic candidate manifest exceeds bounded scope")
    child = copy.deepcopy(parent)
    for key in ("nodes", "edges"):
        records = child.get(key, [])
        if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
            raise _reject(f"candidate {key} records are malformed")
    if v4 or v5:
        plans = _plan_evidence_span_replacements(
            parent, evidence_span_replacements,
            max_operations=7 if v5 else 1,
            allow_quote_only=v5,
        )
        collection_by_kind = {"node": "nodes", "edge": "edges"}
        id_key_by_kind = {"node": "node_id", "edge": "edge_id"}
        for plan in plans:
            collection = child[collection_by_kind[plan["record_kind"]]]
            holder = next(record for record in collection if record.get(id_key_by_kind[plan["record_kind"]]) == plan["record_id"])
            ref = holder["evidence_refs"][plan["evidence_index"]]
            ref["source_span_ref_id"] = plan["replacement_source_span_ref_id"]
            ref["anchor_quotes"] = plan["replacement_anchor_quotes"]
        return child
    if v3:
        plans = _plan_edge_tuple_replacements(parent, edge_tuple_replacements)
        for edge in child["edges"]:
            replacement = plans.get(edge.get("edge_id"))
            if replacement is not None:
                for field in EDGE_TUPLE_FIELDS:
                    edge[field] = replacement[field]
        return child
    for item in replacements:
        if not isinstance(item, dict) or set(item) != {"node_id", "original_description", "replacement_description"}:
            raise _reject("node replacement manifest is malformed")
        if (
            not isinstance(item["node_id"], str) or not item["node_id"].strip()
            or item["node_id"] != item["node_id"].strip()
            or not isinstance(item["original_description"], str)
            or not isinstance(item["replacement_description"], str)
            or len(item["replacement_description"]) > 4096
            or item["replacement_description"] != item["replacement_description"].strip()
        ):
            raise _reject("node replacement manifest is malformed")
        matches = [node for node in child.get("nodes", []) if node.get("node_id") == item["node_id"]]
        if len(matches) != 1 or matches[0].get("description") != item["original_description"]:
            raise _reject("node description target is missing or stale", status_code=409)
        if not isinstance(item["replacement_description"], str) or not item["replacement_description"].strip() or item["replacement_description"] == item["original_description"]:
            raise _reject("node description replacement is empty or unchanged")
        matches[0]["description"] = item["replacement_description"]
    for item in actions:
        if not isinstance(item, dict) or set(item) != {"node_id", "action_index", "expected_old_text", "replacement_text"}:
            raise _reject("session action manifest is malformed")
        node_id = item["node_id"]
        index = item["action_index"]
        old = item["expected_old_text"]
        replacement = item["replacement_text"]
        if (
            not isinstance(node_id, str) or not node_id.strip() or node_id != node_id.strip()
            or type(index) is not int or index < 0
            or not isinstance(old, str) or not old.strip() or old != old.strip()
            or not isinstance(replacement, str) or not replacement.strip()
            or replacement != replacement.strip() or len(replacement) > 4096
            or replacement == old
        ):
            raise _reject("session action manifest is malformed")
        if replacements and replacements[0].get("node_id") != node_id:
            raise _reject("session action and description must target the same node")
        matches = [node for node in child.get("nodes", []) if node.get("node_id") == node_id]
        if len(matches) != 1 or not isinstance(matches[0].get("session_actions"), list):
            raise _reject("session action target is missing or ambiguous", status_code=409)
        entries = matches[0]["session_actions"]
        if index >= len(entries) or entries[index] != old:
            raise _reject("session action target is missing or stale", status_code=409)
        entries[index] = replacement
    for edge_id in omitted:
        if not isinstance(edge_id, str) or not edge_id.strip() or edge_id != edge_id.strip():
            raise _reject("omitted edge ID is invalid")
        matches = [edge for edge in child.get("edges", []) if edge.get("edge_id") == edge_id]
        if len(matches) != 1:
            raise _reject("omitted edge is missing or ambiguous", status_code=409)
        # A dependent record requires a separate design decision; never cascade.
        for key in ("beats", "proposed_writes", "ignored_items", "deferred_items"):
            if _contains(child.get(key, []), edge_id):
                raise _reject("omitted edge has a dependent candidate record", status_code=409)
        child["edges"] = [edge for edge in child["edges"] if edge.get("edge_id") != edge_id]
    return child


def verify_child_replay(run, parent, root: Path) -> bool:
    """Re-prove sealed manifest and child bytes before decision/prepare/confirm."""
    try:
        manifest = run.lineage["semantic_candidate_manifest"]
        if _sha(_canonical_bytes(manifest)) != run.lineage.get("manifest_sha256"):
            return False
        material: dict[str, bytes] = {}
        for key in ("candidate_graph", "source_artifact", "source_span_index"):
            parent_ref = parent.components[key]
            child_ref = run.components[key]
            if key != "candidate_graph" and parent_ref != child_ref:
                return False
            for owner, ref in (("parent", parent_ref), ("child", child_ref)):
                raw_path = root / ref.uri.removeprefix("repo://")
                path = raw_path.resolve()
                if not path.is_relative_to(root.resolve()) or raw_path.is_symlink():
                    return False
                value = path.read_bytes()
                if _sha(value) != ref.sha256.removeprefix("sha256:"):
                    return False
                material[f"{owner}:{key}"] = value
        parent_bytes = material["parent:candidate_graph"]
        child_bytes = material["child:candidate_graph"]
        expected = replay_candidate(json.loads(parent_bytes), manifest, source_bytes=material["parent:source_artifact"], span_bytes=material["parent:source_span_index"])
        return child_bytes == _canonical_bytes(expected)
    except (AttributeError, KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def correct_recap_candidate(
    request: RecapCandidateCorrectionRequest | RecapCandidateCorrectionRequestV2 | RecapCandidateCorrectionRequestV3 | RecapCandidateCorrectionRequestV4 | RecapCandidateCorrectionRequestV5 | RecapCandidateCorrectionRequestV6,
) -> RecapCandidateCorrectionResponse | RecapCandidateCorrectionResponseV2 | RecapCandidateCorrectionResponseV3 | RecapCandidateCorrectionResponseV4 | RecapCandidateCorrectionResponseV5 | RecapCandidateCorrectionResponseV6:
    """Create one held reviewable child without altering parent or WorldGraph."""
    from application_state.ingest.service import (
        RecapSemanticBasisV2,
        RecapSemanticBasisV3,
        RecapSemanticBasisV4,
        RecapSemanticBasisV5,
        RecapSemanticBasisV6,
        RecapSemanticBasisV7,
    )

    root = repo_root()
    try:
        resolved = resolve_promotable_ingest_run(request.parent_run_id, root=root)
        parent = get_extraction_run(root, request.parent_run_id)
    except (PromotableIngestRunError, GraphRunRegistryError) as exc:
        raise _reject(f"parent run is not reviewable: {exc}") from exc
    if (
        resolved.source_domain != "recap" or parent.source_domain != "recap"
        or resolved.extraction_profile != PROFILE or parent.profile_id != PROFILE
        or parent.status != ExtractionRunStatus.REVIEWABLE
        or not parent.has_required_review_components()
        or not parent.campaign_id or not parent.session_id
        or resolved.campaign_id != parent.campaign_id
        or resolved.session_id != parent.session_id
        or resolved.source_artifact_id != parent.source_artifact_id
        or getattr(resolved, "source_span_index_path", None) is None
    ):
        raise _reject("correction requires an exact frozen recap review bundle")
    parent_bytes = resolved.candidate_graph_path.read_bytes()
    parent_sha = _sha(parent_bytes)
    source_ref = parent.components["source_artifact"]
    span_ref = parent.components["source_span_index"]
    source_bytes = resolved.normalized_recap_path.read_bytes()
    span_bytes = resolved.source_span_index_path.read_bytes()
    source_sha = _sha(source_bytes)
    span_sha = _sha(span_bytes)
    if (
        parent_sha != request.parent_candidate_sha256
        or parent_sha != parent.components["candidate_graph"].sha256.removeprefix("sha256:")
        or source_sha != source_ref.sha256.removeprefix("sha256:")
        or span_sha != span_ref.sha256.removeprefix("sha256:")
        or source_sha != resolved.source_revision_id.removeprefix("sha256:")
    ):
        raise _reject("parent candidate/source/span digest changed", status_code=409)
    try:
        parent_payload = json.loads(parent_bytes)
    except json.JSONDecodeError as exc:
        raise _reject("parent candidate is unreadable") from exc
    if not isinstance(parent_payload, dict):
        raise _reject("parent candidate root must be an object")
    v6 = isinstance(request, RecapCandidateCorrectionRequestV6)
    v5 = isinstance(request, RecapCandidateCorrectionRequestV5)
    v3 = isinstance(request, RecapCandidateCorrectionRequestV3)
    v4 = isinstance(request, RecapCandidateCorrectionRequestV4)
    v2 = isinstance(request, RecapCandidateCorrectionRequestV2)
    derivation = DERIVATION_V6 if v6 else DERIVATION_V5 if v5 else DERIVATION_V4 if v4 else DERIVATION_V3 if v3 else DERIVATION_V2 if v2 else DERIVATION
    if v6:
        manifest = {
            "schema": MANIFEST_SCHEMA_V6,
            "source_revision_sha256": request.source_revision_sha256,
            "span_index_sha256": request.span_index_sha256,
            "evidence_ref_splits": [item.model_dump(mode="json") for item in request.evidence_ref_splits],
        }
    elif v5:
        manifest = {
            "schema": MANIFEST_SCHEMA_V5,
            "evidence_span_replacements": [
                item.model_dump(mode="json") for item in request.evidence_replacements
            ],
        }
    elif v4:
        manifest = {
            "schema": MANIFEST_SCHEMA_V4,
            "evidence_span_replacements": [
                {
                    **item.model_dump(mode="json"),
                    "replacement_anchor_quotes": item.replacement_anchor_quotes or item.expected_anchor_quotes,
                }
                for item in request.evidence_span_replacements
            ],
        }
    elif v3:
        manifest = {
            "schema": MANIFEST_SCHEMA_V3,
            "edge_tuple_replacements": [
                item.model_dump(mode="json") for item in request.edge_tuple_replacements
            ],
        }
    else:
        manifest = {
            "schema": MANIFEST_SCHEMA_V2 if v2 else MANIFEST_SCHEMA,
            "node_description_replacements": [
                item.model_dump(mode="json") for item in sorted(request.node_description_replacements, key=lambda value: value.node_id)
            ],
            "omitted_edge_ids": sorted(request.omitted_edge_ids),
        }
    if v2:
        manifest["session_action_replacements"] = [
            item.model_dump(mode="json") for item in request.session_action_replacements
        ]
    payload = replay_candidate(parent_payload, manifest, source_bytes=source_bytes, span_bytes=span_bytes)
    _assert_candidate_scope_matches_run(payload, campaign_id=parent.campaign_id, session_id=parent.session_id)
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=resolved.normalized_recap_path.read_text(encoding="utf-8"),
        source_artifact_id=parent.source_artifact_id,
        span_index=_load_frozen_span_index_for_resolved_run(resolved),
    )
    try:
        validate_candidate_document_integrity(payload)
    except CandidateAdmissionIntegrityError as exc:
        raise _reject("corrected candidate failed document integrity") from exc
    try:
        load_typed_candidate_graph(payload)
    except CandidateGraphMappingError as exc:
        raise _reject("corrected candidate failed typed validation") from exc
    manifest_sha = _sha(_canonical_bytes(manifest))
    child_id = str(uuid5(NAMESPACE_URL, f"dmb:{derivation}:{parent.run_id}:{parent_sha}:{manifest_sha}"))
    child_bytes = _canonical_bytes(payload)
    child_sha = _sha(child_bytes)
    child_path = root / "out" / "graph_memory" / "derived_candidates" / child_id / "candidate_graph.json"
    child_uri = child_path.relative_to(root).as_posix()
    basis_fields = dict(
        parent_run_id=parent.run_id, parent_candidate_sha256=parent_sha,
        manifest_sha256=manifest_sha, child_run_id=child_id,
        candidate_uri=child_uri, candidate_sha256=child_sha,
        source_artifact_id=parent.source_artifact_id,
        source_uri=source_ref.uri, source_revision_sha256=source_sha,
        span_index_uri=span_ref.uri, span_index_sha256=span_sha,
        profile_id=parent.profile_id, profile_version="1.0",
        campaign_id=parent.campaign_id, session_id=parent.session_id,
    )
    basis = (
        RecapSemanticBasisV7(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V6)
        if v6 else
        RecapSemanticBasisV6(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V5)
        if v5 else
        RecapSemanticBasisV5(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V4)
        if v4 else RecapSemanticBasisV4(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V3)
        if v3 else RecapSemanticBasisV3(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V2)
        if v2 else RecapSemanticBasisV2(**basis_fields)
    )
    lineage = {
        "derivation": derivation,
        "parent_run_id": parent.run_id,
        "parent_candidate_sha256": parent_sha,
        "manifest_sha256": manifest_sha,
        "semantic_candidate_manifest": manifest,
        "semantic_disposition": {"version": 1, "state": "held", "basis_sha256": basis.digest()},
    }
    components = dict(parent.components)
    components[ExtractionRunComponentKind.CANDIDATE_GRAPH.value] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH, uri=child_uri,
        sha256=child_sha, exists=True,
    )
    try:
        child = get_extraction_run(root, child_id)
    except GraphRunRegistryError as exc:
        if exc.status_code != 404:
            raise _reject(f"derived run lookup failed: {exc}") from exc
        # Validate and write complete bytes before the lifecycle can reach REVIEWABLE.
        _write_child_candidate(child_path, child_bytes, repo=root)
        try:
            child = create_extraction_run(
                root, run_id=child_id, source_artifact_id=parent.source_artifact_id,
                source_domain="recap", campaign_id=parent.campaign_id,
                session_id=parent.session_id, profile_id=parent.profile_id,
                components=components, status=ExtractionRunStatus.DRAFT, lineage=lineage,
            )
        except GraphRunRegistryError:
            # An identical concurrent request may have won the canonical create.
            child = get_extraction_run(root, child_id)
    if (
        child.components != components or child.source_artifact_id != parent.source_artifact_id
        or child.source_domain != "recap" or child.profile_id != parent.profile_id
        or child.campaign_id != parent.campaign_id or child.session_id != parent.session_id
        or set(child.lineage) != set(lineage)
        or {key: child.lineage.get(key) for key in lineage if key != "semantic_disposition"}
        != {key: value for key, value in lineage.items() if key != "semantic_disposition"}
        or child_path.is_symlink() or not child_path.is_file() or child_path.read_bytes() != child_bytes
    ):
        raise _reject("derived run identity or candidate conflicts", status_code=409)
    for _ in range(8):
        if child.status == ExtractionRunStatus.REVIEWABLE:
            break
        if child.status not in _LIFECYCLE:
            raise _reject("derived run lifecycle is invalid", status_code=409)
        next_status = _LIFECYCLE[_LIFECYCLE.index(child.status) + 1]
        try:
            child = update_extraction_run_status(
                root, child_id, status=next_status, expected_revision=child.revision
            )
        except GraphRunRegistryError as exc:
            if exc.status_code != 409:
                raise _reject(f"derived run seal failed: {exc}") from exc
            child = get_extraction_run(root, child_id)
    if child.status != ExtractionRunStatus.REVIEWABLE or not verify_child_replay(child, parent, root):
        raise _reject("derived recap child could not be replayed and sealed", status_code=409)
    resolved_child = resolve_promotable_ingest_run(child_id, root=root)
    if resolved_child.run_id != child_id:
        raise _reject("derived recap child could not be resolved", status_code=409)
    raw = child.lineage.get("semantic_disposition") or {}
    semantic_state = raw.get("state")
    if semantic_state not in {"held", "accepted", "rejected"} or raw.get("basis_sha256") != basis.digest():
        raise _reject("derived run semantic basis conflicts", status_code=409)
    if semantic_state == "held" and raw != lineage["semantic_disposition"]:
        raise _reject("derived run semantic hold conflicts", status_code=409)
    if semantic_state in {"accepted", "rejected"}:
        from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics

        assessment = assess_recap_semantics(
            child, parent=parent, source_revision_id=source_sha, root=root
        )
        if assessment.disposition is None or assessment.disposition.get("state") != semantic_state:
            raise _reject("derived run semantic decision conflicts", status_code=409)
    response_type = (
        RecapCandidateCorrectionResponseV6 if v6
        else RecapCandidateCorrectionResponseV5 if v5
        else RecapCandidateCorrectionResponseV4 if v4
        else RecapCandidateCorrectionResponseV3 if v3
        else RecapCandidateCorrectionResponseV2 if v2
        else RecapCandidateCorrectionResponse
    )
    return response_type(
        run_id=child_id, parent_run_id=parent.run_id,
        parent_candidate_sha256=parent_sha, candidate_sha256=child_sha,
        manifest_sha256=manifest_sha, semantic_basis_sha256=basis.digest(),
        semantic_state=semantic_state,
    )

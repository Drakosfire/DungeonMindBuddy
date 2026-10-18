"""Bounded, immutable semantic correction of one exact recap candidate."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from apps.live_control_server.config import artifact_data_root, repo_root
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequest,
    RecapCandidateCorrectionRequestV2,
    RecapCandidateCorrectionRequestV3,
    RecapCandidateCorrectionRequestV4,
    RecapCandidateCorrectionRequestV5,
    RecapCandidateCorrectionRequestV6,
    RecapCandidateCorrectionRequestV7,
    RecapCandidateCorrectionRequestV8,
    RecapCandidateCorrectionResponseV8,
    RecapCandidateCorrectionRequestV9,
    RecapCandidateCorrectionRequestV10,
    RecapCandidateCorrectionResponseV10,
    RecapCandidateCorrectionResponseV9,
    RecapCandidateCorrectionResponseV7,
    RecapEvidenceRefSplit,
    RecapCandidateCorrectionResponse,
    RecapCandidateCorrectionResponseV2,
    RecapCandidateCorrectionResponseV3,
    RecapCandidateCorrectionResponseV4,
    RecapCandidateCorrectionResponseV5,
    RecapCandidateCorrectionResponseV6,
    RecapCandidateEdgeTuple,
    RecapCandidateNodeOmission,
    ExtractPromoteDiagnostic,
)
from apps.live_control_server.services.exact_run_evidence_correction import (
    _LIFECYCLE,
    _canonical_bytes,
    _frozen_recap_world_lineage,
    _reject,
    _sha,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _candidate_quote_occurrences,
    _assert_candidate_scope_matches_run,
    _load_frozen_span_index_for_resolved_run,
)
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
    get_extraction_run,
    update_extraction_run_status,
    validate_recap_source_run_world_binding,
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
from graph_memory.candidate_graph_preview import NODE_TYPES
from graph_memory.predicate_catalog import validate_edge_predicate
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET,
    edge_endpoint_kind_admission_reason,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
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
DERIVATION_V7 = "operator_recap_semantic_candidate_correction_v7"
MANIFEST_SCHEMA_V7 = "dmb_recap_semantic_candidate_manifest_v7"

DERIVATION_V8 = "operator_recap_semantic_candidate_correction_v8"
MANIFEST_SCHEMA_V8 = "dmb_recap_semantic_candidate_manifest_v8"
DERIVATION_V9 = "operator_recap_semantic_candidate_correction_v9"
MANIFEST_SCHEMA_V9 = "dmb_recap_semantic_candidate_manifest_v9"
DERIVATION_V10 = "operator_recap_semantic_candidate_correction_v10"
MANIFEST_SCHEMA_V10 = "dmb_recap_semantic_candidate_manifest_v10"
SOURCE_BINDING_DERIVATION_V11 = "operator_recap_semantic_source_binding_v11"

PROFILE = "recap_category_v1@1.0"
MAX_EDGE_TUPLE_REPLACEMENTS = 7
EDGE_TUPLE_FIELDS = ("from_node_id", "relationship_type", "to_node_id", "label")


def _open_secure_directory(root: Path, parts: tuple[str, ...], *, create: bool) -> int | None:
    """Open a root-contained directory chain without following symlinks."""
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
    if not directory_flag or not nofollow_flag:
        raise _reject("safe source-binding directory operations are unavailable", status_code=503)
    root_path = root.resolve(strict=True)
    fd = os.open(root_path, os.O_RDONLY | directory_flag | nofollow_flag)
    try:
        for part in parts:
            if not part or part in {".", ".."} or "/" in part or "\\" in part:
                raise _reject("unsafe source-binding directory path", status_code=409)
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            try:
                child_fd = os.open(
                    part, os.O_RDONLY | directory_flag | nofollow_flag, dir_fd=fd,
                )
            except FileNotFoundError:
                os.close(fd)
                return None
            except OSError as exc:
                raise _reject(
                    f"source-binding directory is unsafe: {exc}", status_code=409,
                ) from exc
            os.close(fd)
            fd = child_fd
        return fd
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


@contextmanager
def _source_binding_child_lock(root: Path, child_id: str):
    lock_dir_fd = _open_secure_directory(
        root, ("out", "graph_memory", "derived_candidates", ".locks"), create=True,
    )
    if lock_dir_fd is None:
        raise _reject("source-binding lock directory is unavailable", status_code=409)
    lock_fd = None
    try:
        lock_fd = os.open(
            f"{child_id}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=lock_dir_fd,
        )
        details = os.fstat(lock_fd)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise _reject("source-binding lock file is not private and regular", status_code=409)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)
        os.close(lock_dir_fd)


def _read_child_file(directory_fd: int, name: str) -> bytes | None:
    nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
    nonblocking_flag = getattr(os, "O_NONBLOCK", 0)
    if not nofollow_flag or not nonblocking_flag:
        raise _reject("safe source-binding file reads are unavailable", status_code=503)
    try:
        fd = os.open(
            name, os.O_RDONLY | nofollow_flag | nonblocking_flag, dir_fd=directory_fd,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _reject(f"source-binding package file is unsafe: {exc}", status_code=409) from exc
    try:
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode):
            raise _reject("source-binding package component is not a regular file", status_code=409)
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _publish_child_package_files(
    root: Path, child_id: str, *, source_bytes: bytes, candidate_bytes: bytes,
    allow_existing: bool,
) -> None:
    """Atomically link verified staged files into the locked child package."""
    relative = ("out", "graph_memory", "derived_candidates")
    staging_fd = _open_secure_directory(root, (*relative, ".staging"), create=True)
    package_fd = _open_secure_directory(root, (*relative, child_id), create=True)
    if staging_fd is None or package_fd is None:
        if staging_fd is not None:
            os.close(staging_fd)
        if package_fd is not None:
            os.close(package_fd)
        raise _reject(f"child {child_id} package could not be opened", status_code=409)
    staged: list[str] = []
    try:
        expected = {"source.md": source_bytes, "candidate_graph.json": candidate_bytes}
        names = set(os.listdir(package_fd))
        if names - expected.keys():
            raise _reject(f"child {child_id} package contains unexpected files", status_code=409)
        for name, content in expected.items():
            current = _read_child_file(package_fd, name)
            if current is not None:
                if not allow_existing or current != content:
                    raise _reject(f"child {child_id} package conflicts at {name}", status_code=409)
                continue
            stage_name = f"{child_id}.{uuid4().hex}.tmp"
            stage_fd = os.open(
                stage_name,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=staging_fd,
            )
            staged.append(stage_name)
            try:
                view = memoryview(content)
                while view:
                    written = os.write(stage_fd, view)
                    view = view[written:]
                os.fsync(stage_fd)
            finally:
                os.close(stage_fd)
            try:
                os.link(
                    stage_name, name, src_dir_fd=staging_fd,
                    dst_dir_fd=package_fd, follow_symlinks=False,
                )
            except FileExistsError:
                if _read_child_file(package_fd, name) != content:
                    raise _reject(f"child {child_id} package conflicts at {name}", status_code=409)
            os.fsync(package_fd)
    finally:
        for stage_name in staged:
            try:
                os.unlink(stage_name, dir_fd=staging_fd)
            except FileNotFoundError:
                pass
        os.close(package_fd)
        os.close(staging_fd)


def _source_binding_package_state(root: Path, child_id: str) -> tuple[bool, dict[str, bytes]]:
    """Return whether a package exists and its present regular file contents."""
    package_fd = _open_secure_directory(
        root, ("out", "graph_memory", "derived_candidates", child_id), create=False,
    )
    if package_fd is None:
        return False, {}
    try:
        names = set(os.listdir(package_fd))
        if names - {"source.md", "candidate_graph.json"}:
            raise _reject(f"child {child_id} package contains unexpected files", status_code=409)
        return True, {
            name: value
            for name in ("source.md", "candidate_graph.json")
            if (value := _read_child_file(package_fd, name)) is not None
        }
    finally:
        os.close(package_fd)


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


def _plan_node_type_replacements(parent: dict, replacements: object) -> dict[str, str]:
    if not isinstance(replacements, list) or len(replacements) != 1:
        raise _reject("node type replacement batch exceeds bounded scope")
    nodes = parent.get("nodes")
    if not isinstance(nodes, list) or any(not isinstance(node, dict) for node in nodes):
        raise _reject("candidate node type records are malformed")
    operation = replacements[0]
    expected_keys = {"node_id", "expected_node_type", "replacement_node_type"}
    if (
        not isinstance(operation, dict)
        or set(operation) != expected_keys
        or not isinstance(operation.get("node_id"), str)
        or not operation["node_id"].strip()
        or operation["node_id"] != operation["node_id"].strip()
        or len(operation["node_id"]) > 256
        or any(ch in operation["node_id"] for ch in ("\r", "\n", "\t"))
        or any(
            not isinstance(operation.get(key), str)
            or operation[key] not in NODE_TYPES
            or operation[key] != operation[key].strip()
            or operation[key] != operation[key].lower()
            or len(operation[key]) > 64
            or any(ch in operation[key] for ch in ("\r", "\n", "\t"))
            for key in ("expected_node_type", "replacement_node_type")
        )
        or operation["expected_node_type"] == operation["replacement_node_type"]
    ):
        raise _reject("node type replacement manifest is malformed")
    matches = [node for node in nodes if node.get("node_id") == operation["node_id"]]
    if len(matches) != 1:
        raise _reject("node type target is missing or ambiguous", status_code=409)
    if matches[0].get("node_type") != operation["expected_node_type"]:
        raise _reject("node type preimage is stale", status_code=409)
    return {operation["node_id"]: operation["replacement_node_type"]}


def _plan_edge_tuple_replacements(
    parent: dict,
    replacements: object,
    *,
    projected_node_types: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
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
                from_buddy_kind=kernel_kind_for_node_type(
                    (projected_node_types or {}).get(
                        target["from_node_id"], endpoint_nodes[0].get("node_type")
                    )
                ),
                to_buddy_kind=kernel_kind_for_node_type(
                    (projected_node_types or {}).get(
                        target["to_node_id"], endpoint_nodes[1].get("node_type")
                    )
                ),
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

    projected_node_types = projected_node_types or {}
    for edge in edges:
        edge_id = edge.get("edge_id")
        values = plans.get(edge_id, {field: edge.get(field) for field in EDGE_TUPLE_FIELDS})
        incident_to_changed_node = any(
            isinstance(values.get(endpoint), str)
            and values[endpoint] in projected_node_types
            for endpoint in ("from_node_id", "to_node_id")
        )
        if not incident_to_changed_node or (isinstance(edge_id, str) and edge_id in plans):
            continue
        try:
            final_tuple = RecapCandidateEdgeTuple.model_validate(values).model_dump()
        except (TypeError, ValueError) as exc:
            raise _reject("an unchanged edge incident to a corrected node has a malformed final tuple") from exc
        endpoint_nodes = []
        for field in ("from_node_id", "to_node_id"):
            matches = node_matches.get(final_tuple[field], [])
            if len(matches) != 1:
                raise _reject("an unchanged edge incident to a corrected node has a missing or ambiguous endpoint")
            endpoint_nodes.append(matches[0])
        if validate_edge_predicate(final_tuple["relationship_type"], None):
            raise _reject("an unchanged edge incident to a corrected node has an unknown predicate")
        if vocabulary is None:
            raise _reject("native predicate vocabulary could not be verified for an unchanged incident edge")
        reason = edge_endpoint_kind_admission_reason(
            buddy_predicate=final_tuple["relationship_type"],
            from_buddy_kind=kernel_kind_for_node_type(
                projected_node_types.get(
                    final_tuple["from_node_id"], endpoint_nodes[0].get("node_type")
                )
            ),
            to_buddy_kind=kernel_kind_for_node_type(
                projected_node_types.get(
                    final_tuple["to_node_id"], endpoint_nodes[1].get("node_type")
                )
            ),
            vocabulary=vocabulary,
        )
        if reason is not None:
            raise _reject(
                "node type correction makes an unchanged incident edge inadmissible to its native predicate"
            )

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


def _plan_node_omission(parent: dict, operations: object) -> str:
    """Validate the full preimage and every dependency before any child write."""
    if not isinstance(operations, list) or len(operations) != 1:
        raise _reject("node omission exceeds bounded scope")
    if not isinstance(operations[0], dict) or set(operations[0]) != {"node_id", "expected_node_sha256"}:
        raise _reject("node omission is malformed")
    try:
        operation = RecapCandidateNodeOmission.model_validate(operations[0])
    except (TypeError, ValueError) as exc:
        raise _reject("node omission is malformed") from exc
    nodes = parent.get("nodes")
    edges = parent.get("edges")
    if not isinstance(nodes, list) or any(not isinstance(node, dict) for node in nodes):
        raise _reject("candidate nodes records are malformed")
    if not isinstance(edges, list) or any(not isinstance(edge, dict) for edge in edges):
        raise _reject("candidate edges records are malformed")
    matches = [node for node in nodes if node.get("node_id") == operation.node_id]
    if len(matches) != 1:
        raise _reject("omitted node is missing or ambiguous", status_code=409)
    if _sha(_canonical_bytes(matches[0])) != operation.expected_node_sha256:
        raise _reject("omitted node preimage is stale", status_code=409)
    if any(operation.node_id in (edge.get("from_node_id"), edge.get("to_node_id")) for edge in edges):
        raise _reject("omitted node has an incident edge", status_code=409)
    for key in ("beats", "proposed_writes", "ignored_items", "deferred_items"):
        if _contains(parent.get(key, []), operation.node_id):
            raise _reject("omitted node has a dependent candidate record", status_code=409)
    return operation.node_id


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


def _replay_atomic_batch(parent: dict, manifest: dict, source_bytes: bytes | None, span_bytes: bytes | None) -> dict:
    from graph_memory.source_span import source_span_index_from_dict, validate_source_span_index
    from graph_memory.extraction.category_candidate_graph_extractor import materialize_promote_evidence_ref
    from graph_memory.anchor_quotes import find_anchor_quote_matches
    from apps.live_control_server.services.extract_promote import _assert_and_project_candidate_evidence

    final_batch = manifest.get("schema") == MANIFEST_SCHEMA_V8
    if manifest.get("schema") not in {MANIFEST_SCHEMA_V7, MANIFEST_SCHEMA_V8}:
        raise _reject("atomic manifest schema changed")
    expected_keys = {"schema", "source_revision_sha256", "span_index_sha256", "profile_id", "node_description_replacements", "node_label_replacements", "edge_tuple_replacements", "evidence_replacements", "edge_omissions"}
    if final_batch:
        expected_keys |= {"expected_parent_revision", "node_type_replacements", "node_omissions"}
    if set(manifest) != expected_keys:
        raise _reject("atomic manifest fields changed")
    try:
        request_class = RecapCandidateCorrectionRequestV8 if final_batch else RecapCandidateCorrectionRequestV7
        request = request_class.model_validate({
            **{k: v for k, v in manifest.items() if k != "schema"},
            "schema": "dmb_recap_candidate_correction_request_v8" if final_batch else "dmb_recap_candidate_correction_request_v7",
            "parent_run_id": "replay", "parent_candidate_sha256": "0" * 64,
        })
    except (ValueError, TypeError) as exc:
        raise _reject("atomic manifest is malformed") from exc
    if source_bytes is None or span_bytes is None or _sha(source_bytes) != request.source_revision_sha256 or _sha(span_bytes) != request.span_index_sha256:
        raise _reject("atomic batch frozen source or span index changed", status_code=409)
    index = source_span_index_from_dict(json.loads(span_bytes))
    validate_source_span_index(index, source_artifact_id=index.source_artifact_id, content_sha256=request.source_revision_sha256)
    if parent.get("source_artifact_ids") != [index.source_artifact_id]:
        raise _reject("atomic batch source identity changed", status_code=409)
    # Retained records must never dangle after an omission. Plan against the
    # unchanged parent and reject dependencies rather than cascading edits.
    omitted = {x.edge_id for x in request.edge_omissions}
    for op in request.edge_omissions:
        matches = [e for e in parent.get("edges", []) if e.get("edge_id") == op.edge_id]
        if len(matches) != 1 or _sha(_canonical_bytes(matches[0])) != op.expected_edge_sha256:
            raise _reject("atomic edge omission preimage is stale", status_code=409)
        for key in ("beats", "proposed_writes", "ignored_items", "deferred_items"):
            if _contains(parent.get(key, []), op.edge_id):
                raise _reject("omitted edge has a dependent candidate record", status_code=409)
    kind_plans = {}
    omitted_node = None
    if final_batch:
        if request.node_omissions:
            omitted_node = _plan_node_omission(parent, [x.model_dump(mode="json") for x in request.node_omissions])
        for operation in request.node_type_replacements:
            kind_plans.update(_plan_node_type_replacements(parent, [operation.model_dump(mode="json")]))
    child = copy.deepcopy(parent)
    def record(kind, identifier):
        collection, key = ("nodes", "node_id") if kind == "node" else ("edges", "edge_id")
        matches = [x for x in parent.get(collection, []) if x.get(key) == identifier]
        if len(matches) != 1:
            raise _reject("atomic batch record missing or ambiguous", status_code=409)
        return matches[0], next(x for x in child[collection] if x.get(key) == identifier)
    for operations, field, original, replacement in (
        (request.node_description_replacements, "description", "original_description", "replacement_description"),
        (request.node_label_replacements, "label", "original_label", "replacement_label"),
    ):
        for op in operations:
            old, new = record("node", op.node_id)
            if old.get(field) != getattr(op, original):
                raise _reject("atomic node preimage is stale", status_code=409)
            new[field] = getattr(op, replacement)
    # Validate rewrites against original preimages, but duplicates against final omissions.
    tuple_parent = copy.deepcopy(parent)
    tuple_parent["edges"] = [e for e in parent.get("edges", []) if e.get("edge_id") not in omitted]
    for node in child["nodes"]:
        if node["node_id"] in kind_plans:
            node["node_type"] = kind_plans[node["node_id"]]
    if request.edge_tuple_replacements:
        plans = _plan_edge_tuple_replacements(tuple_parent, [x.model_dump(mode="json") for x in request.edge_tuple_replacements],
            **({"projected_node_types": kind_plans} if final_batch else {}))
        for identifier, values in plans.items():
            record("edge", identifier)[1].update(values)
    for op in request.evidence_replacements:
        old, new = record(op.record_kind, op.record_id)
        refs = old.get("evidence_refs", [])
        if op.evidence_index >= len(refs) or _sha(_canonical_bytes(refs[op.evidence_index])) != op.expected_evidence_ref_sha256:
            raise _reject("atomic evidence preimage is stale", status_code=409)
        spans = [x for x in index.spans if x.source_span_id == op.source_span_ref_id]
        if len(spans) != 1:
            raise _reject("atomic evidence span is not frozen")
        span = spans[0]
        paragraph = "\n".join(source_bytes.decode("utf-8").splitlines()[span.start_line - 1:span.end_line])
        if any(not find_anchor_quote_matches(paragraph, [quote]) for quote in op.anchor_quotes):
            raise _reject("atomic evidence quote is not literal")
        derived = materialize_promote_evidence_ref(
            {"source_span_ref_id": op.source_span_ref_id, "anchor_quotes": op.anchor_quotes},
            source_artifact_id=index.source_artifact_id, source_ref_id=index.source_ref_id,
        )
        if derived == refs[op.evidence_index]:
            raise _reject("atomic evidence replacement is unchanged")
        new["evidence_refs"][op.evidence_index] = derived
    child["edges"] = [e for e in child.get("edges", []) if e.get("edge_id") not in omitted]
    if final_batch and omitted_node is not None:
        child["nodes"] = [n for n in child["nodes"] if n["node_id"] != omitted_node]
    ids = [n.get("node_id") for n in child.get("nodes", [])]
    edges = [e.get("edge_id") for e in child.get("edges", [])]
    tuples = [tuple(e.get(f) for f in EDGE_TUPLE_FIELDS) for e in child.get("edges", [])]
    if len(set(ids)) != len(ids) or len(set(edges)) != len(edges) or len(set(tuples)) != len(tuples) or any(e.get(f) not in ids for e in child.get("edges", []) for f in ("from_node_id", "to_node_id")):
        raise _reject("atomic final references or tuples conflict")
    if final_batch:
        # Qualify every surviving tuple, not only edits or incident edges.
        index_by_id = {n["node_id"]: n for n in child["nodes"]}
        vocabulary = CURRENT_V5_TARGET.world_object_loader()
        if any(n.get("node_type") not in NODE_TYPES for n in child["nodes"]):
            raise _reject("final candidate node kind is not admitted")
        for edge in child["edges"]:
            reason = edge_endpoint_kind_admission_reason(
                buddy_predicate=edge["relationship_type"],
                from_buddy_kind=kernel_kind_for_node_type(index_by_id[edge["from_node_id"]]["node_type"]),
                to_buddy_kind=kernel_kind_for_node_type(index_by_id[edge["to_node_id"]]["node_type"]),
                vocabulary=vocabulary,
            )
            if validate_edge_predicate(edge["relationship_type"], None) or reason is not None:
                raise _reject("final candidate tuple is not admitted to its native predicate")
    _assert_and_project_candidate_evidence(candidate_payload=child, source_prose=source_bytes.decode("utf-8"), source_artifact_id=index.source_artifact_id, span_index=index)
    return child

_PC_MANIFEST_KEYS = {
    "schema", "expected_parent_revision", "source_revision_sha256", "span_index_sha256",
    "profile_id", "registry_path", "registry_sha256", "roster_session", "roster_key",
    "world_id", "expected_head_revision_id", "reviewer_id", "review_decision_ref", "attachments",
}


def _pc_registry(manifest: dict, *, campaign_id: str, session_id: str) -> set[str]:
    """Read the current exact registry; never trust a manifest roster list."""
    import re
    from graph_memory.party_context import CAMPAIGN_CORPUS, _roster_slugs

    raw_path = manifest["registry_path"]
    if (not isinstance(raw_path, str) or not raw_path.startswith("corpus/")
        or Path(raw_path).is_absolute() or ".." in Path(raw_path).parts):
        raise _reject("PC registry path is outside the corpus root")
    campaign_source = CAMPAIGN_CORPUS.get(campaign_id)
    if campaign_source is None:
        raise _reject("PC campaign has no authoritative registry location", status_code=409)
    expected_path = campaign_source[0] / campaign_source[1] / "_party_registry.json"
    if Path(raw_path) != expected_path:
        raise _reject("PC registry path differs from canonical campaign source", status_code=409)
    try:
        corpus_root = (repo_root() / "corpus").resolve(strict=True)
        path = (repo_root() / raw_path).resolve(strict=True)
    except OSError as exc:
        raise _reject("PC registry is unavailable", status_code=409) from exc
    if not path.is_relative_to(corpus_root) or path.name != "_party_registry.json" or not path.is_file():
        raise _reject("PC registry identity is invalid")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise _reject("PC registry is unreadable", status_code=409) from exc
    if _sha(data) != manifest["registry_sha256"]:
        raise _reject("PC registry bytes changed", status_code=409)
    try:
        registry = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _reject("PC registry is unreadable") from exc
    if (not isinstance(registry, dict)
        or registry.get("schema") not in {"party_registry_v1", "party_registry_v2"}
        or registry.get("campaign_id") != campaign_id):
        raise _reject("PC registry campaign changed", status_code=409)
    match = re.fullmatch(r"(?:session[-_ ]*)?0*([1-9][0-9]*)", session_id, re.IGNORECASE)
    if match is None or int(match.group(1)) != manifest["roster_session"]:
        raise _reject("PC roster session differs from parent candidate", status_code=409)
    slugs, key, _ = _roster_slugs(registry, "session_pc_rosters", str(manifest["roster_session"]))
    if key != manifest["roster_key"] or len(slugs) != len(set(slugs)):
        raise _reject("PC roster carry-forward basis changed", status_code=409)
    return set(slugs)


def _replay_pc_references(parent: dict, manifest: dict, source_bytes: bytes | None,
                          span_bytes: bytes | None, *, historical: bool = False) -> dict:
    """Change only reviewed null corpus references in a copied candidate."""
    from graph_memory.anchor_quotes import find_anchor_quote_matches

    if set(manifest) != _PC_MANIFEST_KEYS or manifest.get("schema") != MANIFEST_SCHEMA_V9:
        raise _reject("PC reference manifest fields changed")
    try:
        request = RecapCandidateCorrectionRequestV9.model_validate({
            **{key: value for key, value in manifest.items() if key != "schema"},
            "schema": "dmb_recap_candidate_correction_request_v9",
            "parent_run_id": "replay", "parent_candidate_sha256": "0" * 64,
        })
    except (ValueError, TypeError) as exc:
        raise _reject("PC reference manifest is malformed") from exc
    if (source_bytes is None or span_bytes is None
        or _sha(source_bytes) != request.source_revision_sha256
        or _sha(span_bytes) != request.span_index_sha256):
        raise _reject("PC reference frozen source or spans changed", status_code=409)
    if not isinstance(parent.get("nodes"), list) or not isinstance(parent.get("session_id"), str):
        raise _reject("PC reference parent candidate is malformed")
    # An introduction was checked against the then-current registry/head when
    # created. Descendant review replays its frozen source proof, not mutable
    # historical external state.
    roster = None if historical else _pc_registry(
        manifest, campaign_id=parent.get("campaign_id"), session_id=parent["session_id"])
    try:
        index = json.loads(span_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _reject("PC reference span index is unreadable") from exc
    if (not isinstance(index, dict) or index.get("schema") != "dmb_source_span_index_v1"
        or index.get("content_sha256") != request.source_revision_sha256
        or parent.get("source_artifact_ids") != [index.get("source_artifact_id")]
        or not isinstance(index.get("spans"), list)):
        raise _reject("PC reference span authority changed", status_code=409)
    child = copy.deepcopy(parent)
    try:
        source_lines = source_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise _reject("PC actor source is not UTF-8") from exc
    for operation in request.attachments:
        if roster is not None and operation.corpus_ref.ref_id not in roster:
            raise _reject("PC reference is not in the selected roster", status_code=409)
        nodes = [node for node in parent["nodes"] if isinstance(node, dict) and node.get("node_id") == operation.node_id]
        if len(nodes) != 1 or nodes[0].get("node_type") != "character":
            raise _reject("PC reference node is missing or wrong kind", status_code=409)
        old = nodes[0]
        if "corpus_ref" not in old or old["corpus_ref"] is not None:
            raise _reject("PC reference null preimage changed", status_code=409)
        refs = old.get("evidence_refs")
        if (not isinstance(refs, list) or not any(
            isinstance(ref, dict) and isinstance(ref.get("anchor_quotes"), list)
            and ref.get("source_span_ref_id") == operation.source_span_ref_id
            and operation.anchor_quote in ref.get("anchor_quotes", [])
            and ref.get("source_artifact_id") == index["source_artifact_id"]
            and ref.get("source_ref_id") == index["source_ref_id"]
            for ref in refs)):
            raise _reject("PC actor anchor is absent from candidate evidence", status_code=409)
        spans = [span for span in index["spans"] if isinstance(span, dict)
                 and span.get("source_span_id") == operation.source_span_ref_id]
        if len(spans) != 1:
            raise _reject("PC actor span is missing or ambiguous", status_code=409)
        span = spans[0]
        start, end = span.get("start_line"), span.get("end_line")
        if (type(start) is not int or type(end) is not int
            or not 1 <= start <= end <= len(source_lines)
            or any(span.get(key) != index.get(key)
                   for key in ("content_sha256", "source_artifact_id", "source_ref_id"))):
            raise _reject("PC actor span authority changed", status_code=409)
        paragraph = "\n".join(source_lines[start - 1:end])
        if (not find_anchor_quote_matches(paragraph, [operation.anchor_quote])
            or not _exact_pc_mention(operation.anchor_quote, operation.pc_mention)):
            raise _reject("PC quote or selected mention is not literal in its span", status_code=409)
        next(node for node in child["nodes"] if node["node_id"] == operation.node_id)["corpus_ref"] = operation.corpus_ref.model_dump(mode="json")
    try:
        validate_candidate_document_integrity(child)
        load_typed_candidate_graph(child)
    except (CandidateAdmissionIntegrityError, CandidateGraphMappingError) as exc:
        raise _reject("PC reference child failed candidate validation") from exc
    return child


def _exact_pc_mention(quote: str, mention: str) -> bool:
    """A full literal mention, not a substring or fuzzy label similarity."""
    import re

    return re.search(r"(?<!\w)" + re.escape(mention.casefold()) + r"(?!\w)",
                     quote.casefold()) is not None


def verify_pc_reference_native_basis(candidate: dict, manifest: dict) -> bool:
    """Re-read one native head and prove each selected PC target without writes."""
    if manifest.get("schema") != MANIFEST_SCHEMA_V9:
        return True
    try:
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import load_production_mutation_context
        from graph_memory.extract_identity_gate import _known_party_anchor

        context = load_production_mutation_context(manifest["world_id"])
        if (context.world_id != manifest["world_id"]
            or context.revision_id != manifest["expected_head_revision_id"]
            or context.head_revision_id != manifest["expected_head_revision_id"]):
            return False
        preview = load_typed_candidate_graph(candidate)
        nodes = {node.node_id: node for node in preview.nodes}
        for row in manifest["attachments"]:
            node = nodes.get(row["node_id"])
            if node is None:
                return False
            target = _known_party_anchor(
                node, context, world_id=manifest["world_id"],
                campaign_id=candidate.get("campaign_id"),
            )
            if target is None or target.object_id != row["native_object_id"]:
                return False
            # Roster membership and exact native identity are established above.
            # The reviewed source mention must name this selected target.
            names = (target.label, *target.aliases)
            if not any(row["pc_mention"].casefold() == name.strip().casefold()
                       for name in names if isinstance(name, str) and name.strip()):
                return False
        return True
    except (AttributeError, KeyError, OSError, RuntimeError, ValueError, TypeError, CandidateGraphMappingError):
        return False



def _replay_evidence_append(parent: dict, manifest: dict, source_bytes: bytes | None, span_bytes: bytes | None) -> dict:
    """Validate the whole append batch before producing an immutable child."""
    from graph_memory.source_span import source_span_index_from_dict, validate_source_span_index
    from graph_memory.extraction.category_candidate_graph_extractor import materialize_promote_evidence_ref

    keys = {"schema", "expected_parent_revision", "source_revision_sha256", "span_index_sha256",
            "profile_id", "evidence_appends", "node_description_replacements"}
    if set(manifest) != keys or manifest.get("schema") != MANIFEST_SCHEMA_V10:
        raise _reject("evidence append manifest fields changed")
    try:
        request = RecapCandidateCorrectionRequestV10.model_validate({
            **{k: v for k, v in manifest.items() if k != "schema"},
            "schema": "dmb_recap_candidate_correction_request_v10",
            "parent_run_id": "replay", "parent_candidate_sha256": "0" * 64,
        })
    except (ValueError, TypeError) as exc:
        raise _reject("evidence append manifest is malformed") from exc
    if source_bytes is None or span_bytes is None or _sha(source_bytes) != request.source_revision_sha256 or _sha(span_bytes) != request.span_index_sha256:
        raise _reject("evidence append frozen source/index changed", status_code=409)
    index = source_span_index_from_dict(json.loads(span_bytes))
    validate_source_span_index(index, source_artifact_id=index.source_artifact_id,
                               content_sha256=request.source_revision_sha256)
    if parent.get("source_artifact_ids") != [index.source_artifact_id]:
        raise _reject("evidence append source identity changed", status_code=409)
    child = copy.deepcopy(parent)
    for op in request.node_description_replacements:
        matches = [n for n in child.get("nodes", []) if n.get("node_id") == op.node_id]
        if len(matches) != 1 or matches[0].get("description") != op.original_description:
            raise _reject("append description preimage is stale", status_code=409)
        matches[0]["description"] = op.replacement_description
    for op in request.evidence_appends:
        collection, id_key = ("nodes", "node_id") if op.record_kind == "node" else ("edges", "edge_id")
        originals = [r for r in parent.get(collection, []) if r.get(id_key) == op.record_id]
        if len(originals) != 1 or not isinstance(originals[0].get("evidence_refs"), list) or any(not isinstance(ref, dict) for ref in originals[0]["evidence_refs"]):
            raise _reject("evidence append target missing or ambiguous", status_code=409)
        original_refs = originals[0]["evidence_refs"]
        if _sha(_canonical_bytes(original_refs)) != op.expected_evidence_refs_sha256:
            raise _reject("evidence append citation array preimage is stale", status_code=409)
        matches = [span for span in index.spans if span.source_span_id == op.source_span_ref_id]
        if len(matches) != 1:
            raise _reject("evidence append span is not frozen")
        span = matches[0]
        paragraph = "\n".join(source_bytes.decode("utf-8").splitlines()[span.start_line - 1:span.end_line])
        if any(quote not in paragraph for quote in op.anchor_quotes):
            raise _reject("evidence append quote is not literal")
        derived = materialize_promote_evidence_ref(
            {"source_span_ref_id": op.source_span_ref_id, "anchor_quotes": op.anchor_quotes},
            source_artifact_id=index.source_artifact_id, source_ref_id=index.source_ref_id,
        )
        target = next(r for r in child[collection] if r[id_key] == op.record_id)
        if any(ref.get("source_span_ref_id") == op.source_span_ref_id or ref.get("source_anchor_id") == derived["source_anchor_id"] for ref in target["evidence_refs"]):
            raise _reject("duplicate evidence append", status_code=409)
        target["evidence_refs"].append(derived)
    return child

def replay_candidate(parent: dict, manifest: dict, *, source_bytes: bytes | None = None, span_bytes: bytes | None = None) -> dict:
    """Reconstruct one bounded correction request; never patch arbitrary JSON."""
    if not isinstance(parent, dict) or not isinstance(manifest, dict):
        raise _reject("semantic candidate replay input is malformed")
    if manifest.get("schema") == MANIFEST_SCHEMA_V10:
        return _replay_evidence_append(parent, manifest, source_bytes, span_bytes)
    if manifest.get("schema") == MANIFEST_SCHEMA_V9:
        return _replay_pc_references(parent, manifest, source_bytes, span_bytes)
    if manifest.get("schema") in {MANIFEST_SCHEMA_V7, MANIFEST_SCHEMA_V8}:
        return _replay_atomic_batch(parent, manifest, source_bytes, span_bytes)
    if manifest.get("schema") == MANIFEST_SCHEMA_V6:
        return _replay_evidence_ref_split(parent, manifest, source_bytes, span_bytes)
    v3 = manifest.get("schema") == MANIFEST_SCHEMA_V3
    v5 = manifest.get("schema") == MANIFEST_SCHEMA_V5
    v4 = manifest.get("schema") == MANIFEST_SCHEMA_V4
    v2 = manifest.get("schema") == MANIFEST_SCHEMA_V2
    v1_label_manifest = not (v2 or v3 or v4 or v5) and "node_label_replacements" in manifest
    expected_keys = (
        {"schema", "evidence_span_replacements"}
        if v4 or v5
        else {"schema", "edge_tuple_replacements"}
        if v3
        else {"schema", "node_description_replacements", "omitted_edge_ids"}
    )
    legacy_v3_keys = {"schema", "edge_tuple_replacements"}
    extended_v3_keys = legacy_v3_keys | {"node_type_replacements"}
    if v2:
        expected_keys.add("session_action_replacements")
    node_omission = "node_omissions" in manifest
    if node_omission and manifest.get("schema") == MANIFEST_SCHEMA:
        expected_keys.add("node_omissions")
    if v1_label_manifest:
        expected_keys.add("node_label_replacements")
    manifest_keys_valid = (
        set(manifest) in (legacy_v3_keys, extended_v3_keys)
        if v3 else set(manifest) == expected_keys
    )
    if not manifest_keys_valid or manifest.get("schema") not in {
        MANIFEST_SCHEMA, MANIFEST_SCHEMA_V2, MANIFEST_SCHEMA_V3, MANIFEST_SCHEMA_V4,
        MANIFEST_SCHEMA_V5,
    }:
        raise _reject("semantic candidate manifest is malformed")
    replacements = manifest.get("node_description_replacements", [])
    omitted = manifest.get("omitted_edge_ids", [])
    actions = manifest.get("session_action_replacements", [])
    label_replacements = manifest.get("node_label_replacements", [])
    edge_tuple_replacements = manifest.get("edge_tuple_replacements", [])
    node_type_replacements = manifest.get("node_type_replacements", [])
    evidence_span_replacements = manifest.get("evidence_span_replacements", [])
    if (
        not isinstance(replacements, list) or (not v3 and len(replacements) > 1)
        or not isinstance(label_replacements, list) or len(label_replacements) > 1
        or not isinstance(omitted, list) or (not v3 and len(omitted) > 1)
        or not isinstance(actions, list) or (len(actions) != 1 if v2 else bool(actions))
        or (v3 and (not isinstance(edge_tuple_replacements, list) or not 1 <= len(edge_tuple_replacements) <= MAX_EDGE_TUPLE_REPLACEMENTS))
        or (v3 and "node_type_replacements" in manifest and (not isinstance(node_type_replacements, list) or len(node_type_replacements) != 1))
        or (v4 and (not isinstance(evidence_span_replacements, list) or len(evidence_span_replacements) != 1))
        or (v5 and (not isinstance(evidence_span_replacements, list) or not 1 <= len(evidence_span_replacements) <= 7))
        or (not (v3 or v4 or v5) and not replacements and not label_replacements and not omitted and not actions and not node_omission)
    ):
        raise _reject("semantic candidate manifest exceeds bounded scope")
    child = copy.deepcopy(parent)
    for key in ("nodes", "edges"):
        records = child.get(key, [])
        if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
            raise _reject(f"candidate {key} records are malformed")
    if node_omission:
        if replacements or label_replacements or omitted or actions:
            raise _reject("node omission must be the only candidate correction")
        node_id = _plan_node_omission(parent, manifest["node_omissions"])
        child["nodes"] = [node for node in child["nodes"] if node.get("node_id") != node_id]
        return child
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
        node_type_plans = (
            _plan_node_type_replacements(parent, node_type_replacements)
            if "node_type_replacements" in manifest else {}
        )
        if node_type_plans:
            node_id = next(iter(node_type_plans))
            paired = any(
                isinstance(operation, dict)
                and any(
                    isinstance(operation.get(key), dict)
                    and node_id in {
                        operation[key].get("from_node_id"),
                        operation[key].get("to_node_id"),
                    }
                    for key in ("expected_tuple", "replacement_tuple")
                )
                for operation in edge_tuple_replacements
            )
            if not paired:
                raise _reject("node type replacement must be paired with an edge tuple replacement")
        plans = _plan_edge_tuple_replacements(
            parent, edge_tuple_replacements, projected_node_types=node_type_plans,
        )
        for edge in child["edges"]:
            replacement = plans.get(edge.get("edge_id"))
            if replacement is not None:
                for field in EDGE_TUPLE_FIELDS:
                    edge[field] = replacement[field]
        for node in child["nodes"]:
            replacement_type = node_type_plans.get(node.get("node_id"))
            if replacement_type is not None:
                node["node_type"] = replacement_type
        return child
    for item in label_replacements:
        if not isinstance(item, dict) or set(item) != {"node_id", "original_label", "replacement_label"}:
            raise _reject("node label replacement manifest is malformed")
        if (
            not isinstance(item["node_id"], str) or not item["node_id"].strip()
            or item["node_id"] != item["node_id"].strip()
            or not isinstance(item["original_label"], str) or not item["original_label"].strip()
            or item["original_label"] != item["original_label"].strip()
            or not isinstance(item["replacement_label"], str) or not item["replacement_label"].strip()
            or item["replacement_label"] != item["replacement_label"].strip()
            or len(item["original_label"]) > 4096 or len(item["replacement_label"]) > 4096
            or item["original_label"] == item["replacement_label"]
        ):
            raise _reject("node label replacement manifest is malformed")
        matches = [node for node in child.get("nodes", []) if node.get("node_id") == item["node_id"]]
        if len(matches) != 1 or matches[0].get("label") != item["original_label"]:
            raise _reject("node label target is missing or stale", status_code=409)
        matches[0]["label"] = item["replacement_label"]
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
        from application_state.ingest.service import RecapSemanticBasisV12
        from apps.live_control_server.services.source_artifact_registry import (
            _read_exact_repo_uri_bytes,
            load_registered_source_artifact_bytes,
        )
        from graph_memory.evidence.source_artifact import validate_source_artifact_scope

        expected_world_scope = _frozen_recap_world_lineage(parent)
        actual_world_scope = {
            key: run.lineage[key]
            for key in ("world_campaign_ingest_context", "native_world_id", "campaign_id")
            if key in run.lineage
        }
        if actual_world_scope != expected_world_scope:
            return False
        manifest = run.lineage["semantic_candidate_manifest"]
        if _sha(_canonical_bytes(manifest)) != run.lineage.get("manifest_sha256"):
            return False
        material: dict[str, bytes] = {}
        for key in ("candidate_graph", "source_artifact", "source_span_index"):
            parent_ref = parent.components[key]
            child_ref = run.components[key]
            source_binding = run.lineage.get("derivation") == SOURCE_BINDING_DERIVATION_V11
            if key == "source_span_index" and parent_ref != child_ref:
                return False
            if key == "source_artifact" and not source_binding and parent_ref != child_ref:
                return False
            for owner, ref in (("parent", parent_ref), ("child", child_ref)):
                value = _read_exact_repo_uri_bytes(root, ref.uri)
                if _sha(value) != ref.sha256.removeprefix("sha256:"):
                    return False
                material[f"{owner}:{key}"] = value
        if run.lineage.get("derivation") == SOURCE_BINDING_DERIVATION_V11:
            raw_basis = run.lineage.get("semantic_source_binding_basis_v12")
            if not isinstance(raw_basis, dict):
                return False
            basis = RecapSemanticBasisV12.model_validate(raw_basis, strict=True)
            child_source = run.components["source_artifact"]
            parent_source = parent.components["source_artifact"]
            child_span_ref = run.components["source_span_index"]
            source_artifact, canonical_bytes = load_registered_source_artifact_bytes(
                root, run.source_artifact_id,
            )
            validate_source_artifact_scope(source_artifact)
            disposition = run.lineage.get("semantic_disposition")
            if (
                basis.model_dump(mode="json", by_alias=True) != raw_basis
                or basis.derivation != SOURCE_BINDING_DERIVATION_V11
                or run.lineage.get("operation_derivation") != basis.operation_derivation
                or run.lineage.get("operation_manifest_schema") != basis.operation_manifest_schema
                or basis.parent_source_uri != parent_source.uri
                or basis.child_snapshot_uri != child_source.uri
                or not child_source.uri.startswith("repo://")
                or basis.span_index_uri != child_span_ref.uri
                or basis.source_artifact_id != run.source_artifact_id
                or source_artifact.source_artifact_id != run.source_artifact_id
                or str(source_artifact.source_domain) != "recap"
                or source_artifact.campaign_id != parent.campaign_id
                or source_artifact.session_id != parent.session_id
                or child_source.sha256.removeprefix("sha256:") != basis.source_revision_sha256
                or parent_source.sha256.removeprefix("sha256:") != basis.source_revision_sha256
                or material["parent:source_artifact"] != material["child:source_artifact"]
                or material["parent:source_artifact"] != canonical_bytes
                or _sha(canonical_bytes) != basis.source_revision_sha256
                or child_source.uri != basis.child_snapshot_uri
                or parent_source.uri != basis.parent_source_uri
                or child_span_ref.uri != basis.span_index_uri
                or child_span_ref.sha256.removeprefix("sha256:") != basis.span_index_sha256
                or parent.components["source_span_index"].sha256.removeprefix("sha256:") != basis.span_index_sha256
                or basis.operation_basis.child_run_id != run.run_id
                or basis.operation_basis.parent_run_id != parent.run_id
                or basis.operation_basis.candidate_uri != run.components["candidate_graph"].uri
                or basis.operation_basis.candidate_sha256 != run.components["candidate_graph"].sha256.removeprefix("sha256:")
                or not isinstance(disposition, dict)
                or disposition.get("basis_sha256") != basis.digest()
            ):
                return False
            validate_recap_source_run_world_binding(
                source_world_id=source_artifact.world_id,
                campaign_id=parent.campaign_id,
                lineage=_frozen_recap_world_lineage(parent),
            )
        parent_bytes = material["parent:candidate_graph"]
        child_bytes = material["child:candidate_graph"]
        expected = replay_candidate(json.loads(parent_bytes), manifest, source_bytes=material["parent:source_artifact"], span_bytes=material["parent:source_span_index"])
        # Source-bound replays validate the frozen correction basis. Mutable
        # native target identity is checked at prepare/confirm against the
        # inherited proof, so an unrelated later World-head change cannot
        # rewrite the accepted semantic disposition into a generic hold.
        source_binding = (
            run.lineage.get("derivation") == SOURCE_BINDING_DERIVATION_V11
            or run.lineage.get("_source_binding_outer_derivation")
            == SOURCE_BINDING_DERIVATION_V11
        )
        return (child_bytes == _canonical_bytes(expected)
                and (source_binding or verify_pc_reference_native_basis(expected, manifest)))
    except (AttributeError, KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _validated_recap_world_scope(parent: ExtractionRun, *, source_world_id: str | None) -> dict[str, object]:
    """Carry only the parent's frozen World scope after matching the source."""
    scope = _frozen_recap_world_lineage(parent)
    if scope and not source_world_id:
        raise _reject("World-scoped recap source is missing its canonical World binding")
    try:
        validate_recap_source_run_world_binding(
            source_world_id=source_world_id,
            campaign_id=parent.campaign_id,
            lineage=scope,
        )
    except GraphRunRegistryError as exc:
        raise _reject(str(exc), status_code=exc.status_code) from exc
    return scope


def _preflight_source_snapshot(parent: ExtractionRun, resolved, root: Path):
    """Verify exact canonical, parent, and span bytes before any child write."""
    from application_state.errors import ApplicationStateError
    from application_state.source import service as source_service
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        _read_exact_repo_uri_bytes,
        load_registered_source_artifact_bytes,
    )
    from graph_memory.evidence.source_artifact import validate_source_artifact_scope

    parent_source = parent.components.get("source_artifact")
    parent_spans = parent.components.get("source_span_index")
    parent_candidate = parent.components.get("candidate_graph")
    if not all((parent_source, parent_spans, parent_candidate)):
        raise _reject("parent recap components are incomplete", status_code=409)
    try:
        artifact, canonical_source_bytes = load_registered_source_artifact_bytes(
            root, parent.source_artifact_id,
        )
        parent_source_bytes = _read_exact_repo_uri_bytes(root, parent_source.uri)
        span_bytes = _read_exact_repo_uri_bytes(root, parent_spans.uri)
        parent_candidate_bytes = _read_exact_repo_uri_bytes(root, parent_candidate.uri)
    except SourceArtifactRegistryError as exc:
        raise _reject(f"parent source snapshot preflight failed: {exc}", status_code=exc.status_code) from exc
    try:
        validate_source_artifact_scope(artifact)
    except ValueError as exc:
        raise _reject(f"registered recap SourceArtifact is invalid: {exc}", status_code=409) from exc
    source_digest = _sha(canonical_source_bytes)
    if (
        artifact.source_artifact_id != parent.source_artifact_id
        or str(artifact.source_domain) != "recap"
        or artifact.campaign_id != parent.campaign_id
        or artifact.session_id != parent.session_id
        or getattr(resolved, "source_domain", None) != "recap"
        or getattr(resolved, "campaign_id", None) != parent.campaign_id
        or getattr(resolved, "session_id", None) != parent.session_id
        or getattr(resolved, "source_artifact_id", None) != parent.source_artifact_id
        or getattr(resolved, "world_id", None) != artifact.world_id
        or parent_source_bytes != canonical_source_bytes
        or _sha(parent_source_bytes) != source_digest
        or _sha(parent_source_bytes) != parent_source.sha256.removeprefix("sha256:")
        or source_digest != (artifact.content_sha256 or "").removeprefix("sha256:")
        or source_digest != resolved.source_revision_id.removeprefix("sha256:")
        or _sha(span_bytes) != parent_spans.sha256.removeprefix("sha256:")
    ):
        raise _reject(
            "registered source, frozen parent, or resolved recap identity changed",
            status_code=409,
        )
    scope = _validated_recap_world_scope(parent, source_world_id=artifact.world_id)
    try:
        # The resolver paths must name the same immutable bytes as the frozen refs.
        if (
            resolved.normalized_recap_path.read_bytes() != canonical_source_bytes
            or resolved.source_span_index_path.read_bytes() != span_bytes
            or resolved.candidate_graph_path.read_bytes() != parent_candidate_bytes
        ):
            raise _reject("resolved recap files differ from the frozen component refs", status_code=409)
        span_index = _load_frozen_span_index_for_resolved_run(resolved)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _reject(f"frozen source span index is invalid: {exc}", status_code=409) from exc
    try:
        source_service.persist_source_markdown(
            source_artifact_id=artifact.source_artifact_id,
            source_domain=str(artifact.source_domain),
            campaign_id=artifact.campaign_id,
            session_id=artifact.session_id,
            world_id=artifact.world_id,
            markdown=canonical_source_bytes.decode("utf-8", errors="strict"),
            content_sha256=source_digest,
            lineage={"adopted_from_uri": artifact.uri},
            dry_run=True,
        )
    except (ApplicationStateError, UnicodeDecodeError) as exc:
        raise _reject(f"canonical recap source cannot be durably bound: {exc}", status_code=409) from exc
    return artifact, parent_candidate_bytes, canonical_source_bytes, span_bytes, span_index, scope


INHERITED_PC_PROOF_SCHEMA = "dmb_inherited_pc_reference_proof_v1"


def inherited_pc_proof_digest(proof: dict) -> str:
    return _sha(_canonical_bytes(proof))


def _frozen_component(run: ExtractionRun, key: str, root: Path) -> bytes:
    """Read one exact immutable component without escaping its artifact root."""
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        _read_exact_repo_uri_bytes,
    )

    ref = run.components[key]
    try:
        value = _read_exact_repo_uri_bytes(root, ref.uri)
    except SourceArtifactRegistryError as exc:
        raise _reject("inherited PC component escaped its artifact root", status_code=409) from exc
    if _sha(value) != ref.sha256.removeprefix("sha256:"):
        raise _reject("inherited PC component digest changed", status_code=409)
    return value


def _unique_pc_node(payload: dict, node_id: str) -> dict:
    nodes = payload.get("nodes")
    matches = [node for node in nodes if isinstance(node, dict) and node.get("node_id") == node_id] if isinstance(nodes, list) else []
    if len(matches) != 1 or matches[0].get("node_type") != "character":
        raise _reject("inherited PC node is missing or wrong kind", status_code=409)
    return matches[0]


def inherited_pc_reference_proof(
    run: ExtractionRun, root: Path, *, candidate_override: dict | None = None,
    source_snapshot_override: bytes | None = None,
) -> dict | None:
    """Derive surviving V9 attachments through sealed, immutable correction links.

    This deliberately does not re-read the historical registry or original
    World head. The current native target is checked at publication time.
    """
    run_operation = (
        run.lineage.get("operation_derivation")
        if run.lineage.get("derivation") == SOURCE_BINDING_DERIVATION_V11
        else run.lineage.get("derivation")
    )
    if run_operation not in {DERIVATION_V7, DERIVATION_V8, DERIVATION_V10}:
        return None
    final_bytes = (_canonical_bytes(candidate_override) if candidate_override is not None
                   else _frozen_component(run, "candidate_graph", root))
    if _sha(final_bytes) != run.components["candidate_graph"].sha256.removeprefix("sha256:"):
        raise _reject("inherited PC final candidate digest changed", status_code=409)
    final = json.loads(final_bytes)
    if not isinstance(final, dict) or not isinstance(final.get("nodes"), list):
        raise _reject("inherited PC final candidate is malformed", status_code=409)
    pc_nodes = [node for node in final["nodes"] if isinstance(node, dict)
                and isinstance(node.get("corpus_ref"), dict)
                and node["corpus_ref"].get("type") == "pc"
                and node["corpus_ref"].get("resolution") == "resolved"]
    if not pc_nodes:
        return None
    states: list[tuple[dict, dict, dict]] = []  # candidate, manifest, immutable link
    seen: set[str] = set()
    current = run
    current_bytes = final_bytes
    while current.lineage.get("derivation") in {
        DERIVATION, DERIVATION_V2, DERIVATION_V3, DERIVATION_V4, DERIVATION_V5,
        DERIVATION_V6, DERIVATION_V7, DERIVATION_V8, DERIVATION_V9, DERIVATION_V10,
        SOURCE_BINDING_DERIVATION_V11,
    }:
        if current.run_id in seen or len(seen) >= 64:
            raise _reject("inherited PC lineage is cyclic or unbounded", status_code=409)
        seen.add(current.run_id)
        lineage = current.lineage
        projected_outer = lineage.get("_source_binding_outer_derivation")
        outer_binding = (
            lineage.get("derivation") == SOURCE_BINDING_DERIVATION_V11
            or projected_outer == SOURCE_BINDING_DERIVATION_V11
        )
        actual_outer_binding = lineage.get("derivation") == SOURCE_BINDING_DERIVATION_V11
        operation_derivation = (
            lineage.get("operation_derivation") if actual_outer_binding
            else lineage.get("derivation")
        )
        identity_derivation = (
            SOURCE_BINDING_DERIVATION_V11 if outer_binding
            else lineage.get("derivation")
        )
        parent_id = lineage.get("parent_run_id")
        manifest = lineage.get("semantic_candidate_manifest")
        if not isinstance(parent_id, str) or not parent_id or not isinstance(manifest, dict):
            raise _reject("inherited PC lineage is missing its manifest", status_code=409)
        manifest_sha = _sha(_canonical_bytes(manifest))
        if lineage.get("manifest_sha256") != manifest_sha:
            raise _reject("inherited PC manifest digest changed", status_code=409)
        try:
            parent = get_extraction_run(root, parent_id)
        except GraphRunRegistryError as exc:
            raise _reject("inherited PC parent is unavailable", status_code=409) from exc
        if parent.run_id in seen:
            raise _reject("inherited PC lineage is cyclic", status_code=409)
        parent_bytes = _frozen_component(parent, "candidate_graph", root)
        source_bytes = _frozen_component(parent, "source_artifact", root)
        span_bytes = _frozen_component(parent, "source_span_index", root)
        current_source = (
            source_snapshot_override
            if outer_binding and current.run_id == run.run_id and source_snapshot_override is not None
            else _frozen_component(current, "source_artifact", root)
        )
        current_source_ref = current.components["source_artifact"]
        parent_source_ref = parent.components["source_artifact"]
        source_refs_invalid = (
            current_source_ref != parent_source_ref
            if projected_outer == SOURCE_BINDING_DERIVATION_V11
            else current_source_ref.sha256 != parent_source_ref.sha256
            or current_source_ref.uri == parent_source_ref.uri
            if actual_outer_binding
            else current_source_ref != parent_source_ref
        )
        if (source_refs_invalid
            or current.components["source_span_index"] != parent.components["source_span_index"]
            or current_source != source_bytes
            or lineage.get("parent_candidate_sha256") != _sha(parent_bytes)
            or current.campaign_id != parent.campaign_id or current.session_id != parent.session_id
            or current.source_artifact_id != parent.source_artifact_id
            or current.profile_id != parent.profile_id
            or current.run_id != str(uuid5(NAMESPACE_URL,
                f"dmb:{identity_derivation}:{parent_id}:{_sha(parent_bytes)}:{manifest_sha}"))):
            raise _reject("inherited PC lineage identity changed", status_code=409)
        if actual_outer_binding:
            from apps.live_control_server.services.source_artifact_registry import (
                load_registered_source_artifact_bytes,
            )
            from graph_memory.evidence.source_artifact import validate_source_artifact_scope

            try:
                artifact, canonical_source = load_registered_source_artifact_bytes(
                    root, current.source_artifact_id,
                )
                validate_source_artifact_scope(artifact)
            except (ValueError, OSError) as exc:
                raise _reject("inherited PC source-binding artifact changed", status_code=409) from exc
            if (
                canonical_source != current_source
                or artifact.source_artifact_id != current.source_artifact_id
                or str(artifact.source_domain) != "recap"
                or artifact.campaign_id != parent.campaign_id
                or artifact.session_id != parent.session_id
                or current.components["source_artifact"].uri
                != f"repo://out/graph_memory/derived_candidates/{current.run_id}/source.md"
            ):
                raise _reject("inherited PC source-binding pins changed", status_code=409)
            if lineage.get("semantic_source_binding_basis_v12") is not None:
                if not verify_child_replay(current, parent, root):
                    raise _reject("inherited PC source-binding replay changed", status_code=409)
        if operation_derivation not in {
            DERIVATION, DERIVATION_V2, DERIVATION_V3, DERIVATION_V4,
            DERIVATION_V5, DERIVATION_V6, DERIVATION_V7, DERIVATION_V8,
            DERIVATION_V9, DERIVATION_V10,
        }:
            raise _reject("inherited PC operation derivation is unknown", status_code=409)
        parent_payload = json.loads(parent_bytes)
        if operation_derivation == DERIVATION_V9:
            expected = _replay_pc_references(parent_payload, manifest, source_bytes, span_bytes,
                                             historical=True)
        else:
            expected = replay_candidate(parent_payload, manifest, source_bytes=source_bytes,
                                        span_bytes=span_bytes)
        if current_bytes != _canonical_bytes(expected):
            raise _reject("inherited PC lineage replay changed", status_code=409)
        link = {
            "run_id": current.run_id, "parent_run_id": parent_id,
            "derivation": identity_derivation, "manifest_sha256": manifest_sha,
            "candidate_sha256": _sha(current_bytes),
            "parent_candidate_sha256": _sha(parent_bytes),
        }
        if outer_binding:
            link["operation_derivation"] = operation_derivation
        states.append((json.loads(current_bytes), manifest, link))
        current, current_bytes = parent, parent_bytes

    rows: list[dict] = []
    for selected in pc_nodes:
        node_id, ref = selected.get("node_id"), selected["corpus_ref"]
        if not isinstance(node_id, str):
            raise _reject("inherited PC node ID is malformed", status_code=409)
        origin_index = next((index for index, (_, manifest, _) in enumerate(states)
            if manifest.get("schema") == MANIFEST_SCHEMA_V9
            and any(row.get("node_id") == node_id for row in manifest.get("attachments", [])
                    if isinstance(row, dict))), None)
        if origin_index is None:
            continue  # A pre-existing source candidate PC is outside this V9 overlay.
        _, origin_manifest, origin_link = states[origin_index]
        introductions = [row for row in origin_manifest["attachments"] if row["node_id"] == node_id]
        if len(introductions) != 1 or introductions[0].get("corpus_ref") != ref:
            raise _reject("inherited PC introduction changed", status_code=409)
        introduction = introductions[0]
        for payload, _, _ in states[:origin_index + 1]:
            node = _unique_pc_node(payload, node_id)
            evidence = node.get("evidence_refs")
            if node.get("corpus_ref") != ref or not isinstance(evidence, list) or not any(
                isinstance(item, dict)
                and item.get("source_span_ref_id") == introduction["source_span_ref_id"]
                and isinstance(item.get("anchor_quotes"), list)
                and introduction["anchor_quote"] in item["anchor_quotes"]
                for item in evidence
            ):
                raise _reject("inherited PC attachment tuple changed", status_code=409)
        if (origin_manifest.get("source_revision_sha256") !=
            run.components["source_artifact"].sha256.removeprefix("sha256:")
            or origin_manifest.get("span_index_sha256") !=
            run.components["source_span_index"].sha256.removeprefix("sha256:")):
            raise _reject("inherited PC frozen source/index changed", status_code=409)
        rows.append({
            "node_id": node_id, "corpus_ref": ref,
            "native_object_id": introduction["native_object_id"],
            "origin_world_id": origin_manifest["world_id"],
            "origin_run_id": origin_link["run_id"],
            "origin_manifest_sha256": origin_link["manifest_sha256"],
            "source_revision_sha256": origin_manifest["source_revision_sha256"],
            "span_index_sha256": origin_manifest["span_index_sha256"],
            "source_span_ref_id": introduction["source_span_ref_id"],
            "anchor_quote": introduction["anchor_quote"],
            "pc_mention": introduction["pc_mention"],
            "lineage_links": [link for _, _, link in states[:origin_index + 1]],
        })
    if not rows:
        return None
    rows.sort(key=lambda row: row["node_id"])
    return {"schema": INHERITED_PC_PROOF_SCHEMA,
            "final_candidate_sha256": _sha(final_bytes), "rows": rows}


def verify_inherited_pc_native_basis(candidate: dict, proof: dict, context: object) -> bool:
    """Resolve every surviving inherited target against the current native World."""
    try:
        from graph_memory.extract_identity_gate import _known_party_anchor

        preview = load_typed_candidate_graph(candidate)
        nodes = {node.node_id: node for node in preview.nodes}
        if _sha(_canonical_bytes(candidate)) != proof["final_candidate_sha256"]:
            return False
        for row in proof["rows"]:
            if row["origin_world_id"] != context.world_id:
                return False
            node = nodes.get(row["node_id"])
            if node is None:
                return False
            target = _known_party_anchor(
                node, context, world_id=context.world_id,
                campaign_id=candidate.get("campaign_id"),
            )
            if target is None or target.object_id != row["native_object_id"]:
                return False
            names = (target.label, *target.aliases)
            if not any(row["pc_mention"].casefold() == name.strip().casefold()
                       for name in names if isinstance(name, str) and name.strip()):
                return False
        return True
    except (AttributeError, KeyError, ValueError, TypeError, CandidateGraphMappingError):
        return False


def correct_recap_candidate(
    request: RecapCandidateCorrectionRequest | RecapCandidateCorrectionRequestV2 | RecapCandidateCorrectionRequestV3 | RecapCandidateCorrectionRequestV4 | RecapCandidateCorrectionRequestV5 | RecapCandidateCorrectionRequestV6 | RecapCandidateCorrectionRequestV7 | RecapCandidateCorrectionRequestV8 | RecapCandidateCorrectionRequestV9 | RecapCandidateCorrectionRequestV10,
) -> RecapCandidateCorrectionResponse | RecapCandidateCorrectionResponseV2 | RecapCandidateCorrectionResponseV3 | RecapCandidateCorrectionResponseV4 | RecapCandidateCorrectionResponseV5 | RecapCandidateCorrectionResponseV6 | RecapCandidateCorrectionResponseV7 | RecapCandidateCorrectionResponseV8 | RecapCandidateCorrectionResponseV9 | RecapCandidateCorrectionResponseV10:
    """Create one held reviewable child without altering parent or WorldGraph."""
    from application_state.ingest.service import (
        RecapSemanticBasisV2,
        RecapSemanticBasisV3,
        RecapSemanticBasisV4,
        RecapSemanticBasisV5,
        RecapSemanticBasisV6,
        RecapSemanticBasisV7,
        RecapSemanticBasisV8,
        RecapSemanticBasisV9,
        RecapSemanticBasisV10,
        RecapSemanticBasisV11,
        RecapSemanticBasisV12,
    )

    root = artifact_data_root(repo_root())
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
    source_ref = parent.components["source_artifact"]
    span_ref = parent.components["source_span_index"]
    artifact, parent_bytes, source_bytes, span_bytes, span_index, world_scope = (
        _preflight_source_snapshot(parent, resolved, root)
    )
    parent_sha = _sha(parent_bytes)
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
    v10 = isinstance(request, RecapCandidateCorrectionRequestV10)
    v9 = isinstance(request, RecapCandidateCorrectionRequestV9)
    v8 = isinstance(request, RecapCandidateCorrectionRequestV8)
    v7 = isinstance(request, RecapCandidateCorrectionRequestV7)
    v6 = isinstance(request, RecapCandidateCorrectionRequestV6)
    v5 = isinstance(request, RecapCandidateCorrectionRequestV5)
    v3 = isinstance(request, RecapCandidateCorrectionRequestV3)
    v4 = isinstance(request, RecapCandidateCorrectionRequestV4)
    v2 = isinstance(request, RecapCandidateCorrectionRequestV2)
    derivation = DERIVATION_V10 if v10 else DERIVATION_V9 if v9 else DERIVATION_V8 if v8 else DERIVATION_V7 if v7 else DERIVATION_V6 if v6 else DERIVATION_V5 if v5 else DERIVATION_V4 if v4 else DERIVATION_V3 if v3 else DERIVATION_V2 if v2 else DERIVATION
    if (v8 or v9 or v10) and request.expected_parent_revision != parent.revision:
        raise _reject("final batch parent revision changed", status_code=409)
    if v10:
        if request.source_revision_sha256 != source_sha or request.span_index_sha256 != span_sha or request.profile_id != parent.profile_id:
            raise _reject("append request source/index/profile pins changed", status_code=409)
        manifest = request.model_dump(mode="json", exclude={"schema_", "parent_run_id", "parent_candidate_sha256"})
        manifest["schema"] = MANIFEST_SCHEMA_V10
        manifest["evidence_appends"].sort(key=lambda item: (item["record_kind"], item["record_id"], item["source_span_ref_id"]))
    elif v9:
        if (request.source_revision_sha256 != source_sha
            or request.span_index_sha256 != span_sha
            or request.profile_id != parent.profile_id):
            raise _reject("PC reference source/index/profile pins changed", status_code=409)
        manifest = request.model_dump(mode="json", exclude={"schema_", "parent_run_id", "parent_candidate_sha256"})
        manifest["schema"] = MANIFEST_SCHEMA_V9
        manifest["attachments"].sort(key=lambda item: item["node_id"])
    elif v7:
        if request.source_revision_sha256 != source_sha or request.span_index_sha256 != span_sha or request.profile_id != parent.profile_id:
            raise _reject("atomic request source/index/profile pins changed", status_code=409)
        manifest = request.model_dump(mode="json", exclude={"schema_", "parent_run_id", "parent_candidate_sha256"})
        manifest["schema"] = MANIFEST_SCHEMA_V8 if v8 else MANIFEST_SCHEMA_V7
        for key, coordinate in (("node_description_replacements", lambda x: x["node_id"]), ("node_label_replacements", lambda x: x["node_id"]), ("edge_tuple_replacements", lambda x: x["edge_id"]), ("edge_omissions", lambda x: x["edge_id"]), ("evidence_replacements", lambda x: (x["record_kind"], x["record_id"], x["evidence_index"]))):
            manifest[key].sort(key=coordinate)
        if v8:
            for key in ("node_type_replacements", "node_omissions"):
                manifest[key].sort(key=lambda x: x["node_id"])
    elif v6:
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
        if request.node_type_replacements:
            manifest["node_type_replacements"] = [
                item.model_dump(mode="json") for item in request.node_type_replacements
            ]
    else:
        manifest = {
            "schema": MANIFEST_SCHEMA_V2 if v2 else MANIFEST_SCHEMA,
            "node_description_replacements": [
                item.model_dump(mode="json") for item in sorted(request.node_description_replacements, key=lambda value: value.node_id)
            ],
            "omitted_edge_ids": sorted(request.omitted_edge_ids),
        }
        if not (v2 or v3 or v4 or v5) and request.node_label_replacements:
            manifest["node_label_replacements"] = [
                item.model_dump(mode="json") for item in sorted(request.node_label_replacements, key=lambda value: value.node_id)
            ]
    if isinstance(request, RecapCandidateCorrectionRequest) and request.node_omissions:
        manifest["node_omissions"] = [item.model_dump(mode="json") for item in request.node_omissions]
    if v2:
        manifest["session_action_replacements"] = [
            item.model_dump(mode="json") for item in request.session_action_replacements
        ]
    payload = replay_candidate(parent_payload, manifest, source_bytes=source_bytes, span_bytes=span_bytes)
    if v9 and not verify_pc_reference_native_basis(payload, manifest):
        raise _reject("PC reference native World/head/identity basis changed", status_code=409)
    _assert_candidate_scope_matches_run(payload, campaign_id=parent.campaign_id, session_id=parent.session_id)
    evidence_arguments = dict(
        source_prose=source_bytes.decode("utf-8", errors="strict"),
        source_artifact_id=parent.source_artifact_id,
        span_index=span_index,
    )
    parent_failures = _candidate_quote_occurrences(candidate_payload=parent_payload, **evidence_arguments)
    child_failures = _candidate_quote_occurrences(candidate_payload=payload, **evidence_arguments)
    split = manifest.get("evidence_ref_splits", [None])[0] if v6 else None
    for failure in child_failures:
        mapped = dict(failure)
        if split and failure["record_kind"] == split["record_kind"] and failure["record_id"] == split["record_id"]:
            index = failure["evidence_index"]
            start = split["evidence_index"]
            width = len(split["parts"])
            if start <= index < start + width:
                raise _reject("split output evidence must validate strictly")
            if index >= start + width:
                mapped["evidence_index"] -= width - 1
        if mapped not in parent_failures:
            raise _reject("corrected candidate introduces or changes invalid evidence; no child was created")
    try:
        validate_candidate_document_integrity(payload)
    except CandidateAdmissionIntegrityError as exc:
        raise _reject("corrected candidate failed document integrity") from exc
    try:
        load_typed_candidate_graph(payload)
    except CandidateGraphMappingError as exc:
        raise _reject("corrected candidate failed typed validation") from exc
    manifest_sha = _sha(_canonical_bytes(manifest))
    legacy_child_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{derivation}:{parent.run_id}:{parent_sha}:{manifest_sha}",
    ))
    child_id = str(uuid5(
        NAMESPACE_URL,
        f"dmb:{SOURCE_BINDING_DERIVATION_V11}:{parent.run_id}:{parent_sha}:{manifest_sha}",
    ))
    child_bytes = _canonical_bytes(payload)
    child_sha = _sha(child_bytes)
    child_relative = f"out/graph_memory/derived_candidates/{child_id}"
    child_candidate_uri = f"repo://{child_relative}/candidate_graph.json"
    child_source_uri = f"repo://{child_relative}/source.md"
    components = dict(parent.components)
    components[ExtractionRunComponentKind.CANDIDATE_GRAPH.value] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH, uri=child_candidate_uri,
        sha256=child_sha, exists=True,
    )
    components[ExtractionRunComponentKind.SOURCE_ARTIFACT.value] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.SOURCE_ARTIFACT, uri=child_source_uri,
        sha256=source_sha, exists=True,
    )
    lineage = {
        "derivation": SOURCE_BINDING_DERIVATION_V11,
        "operation_derivation": derivation,
        "operation_manifest_schema": manifest["schema"],
        "parent_run_id": parent.run_id,
        "parent_candidate_sha256": parent_sha,
        "manifest_sha256": manifest_sha,
        "semantic_candidate_manifest": manifest,
        **world_scope,
    }
    inherited_proof = None
    if v7 or v8 or v10:
        prospective = ExtractionRun(
            run_id=child_id, source_artifact_id=parent.source_artifact_id,
            source_domain="recap", campaign_id=parent.campaign_id,
            session_id=parent.session_id, profile_id=parent.profile_id,
            status=ExtractionRunStatus.REVIEWABLE, components=components, lineage=lineage,
        )
        inherited_proof = inherited_pc_reference_proof(
            prospective, root, candidate_override=payload,
            source_snapshot_override=source_bytes,
        )
        if inherited_proof is not None:
            lineage["inherited_pc_proof"] = inherited_proof
    inherited_digest = (inherited_pc_proof_digest(inherited_proof)
                        if inherited_proof is not None else None)
    basis_fields = dict(
        parent_run_id=parent.run_id, parent_candidate_sha256=parent_sha,
        manifest_sha256=manifest_sha, child_run_id=child_id,
        candidate_uri=child_candidate_uri, candidate_sha256=child_sha,
        source_artifact_id=parent.source_artifact_id,
        source_uri=source_ref.uri, source_revision_sha256=source_sha,
        span_index_uri=span_ref.uri, span_index_sha256=span_sha,
        profile_id=parent.profile_id, profile_version="1.0",
        campaign_id=parent.campaign_id, session_id=parent.session_id,
    )
    operation_basis = (
        RecapSemanticBasisV11(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V10,
            expected_parent_revision=request.expected_parent_revision, inherited_pc_proof_sha256=inherited_digest)
        if v10 else
        RecapSemanticBasisV10(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V9,
            expected_parent_revision=request.expected_parent_revision,
            registry_sha256=request.registry_sha256, roster_key=request.roster_key,
            world_id=request.world_id, expected_head_revision_id=request.expected_head_revision_id)
        if v9 else
        RecapSemanticBasisV9(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V8, expected_parent_revision=request.expected_parent_revision, inherited_pc_proof_sha256=inherited_digest)
        if v8 else
        RecapSemanticBasisV8(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V7, inherited_pc_proof_sha256=inherited_digest)
        if v7 else
        RecapSemanticBasisV7(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V6)
        if v6 else
        RecapSemanticBasisV6(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V5)
        if v5 else
        RecapSemanticBasisV5(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V4)
        if v4 else RecapSemanticBasisV4(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V3)
        if v3 else RecapSemanticBasisV3(**basis_fields, derivation=derivation, manifest_schema=MANIFEST_SCHEMA_V2)
        if v2 else RecapSemanticBasisV2(**basis_fields)
    )
    request_version = (
        10 if v10 else 9 if v9 else 8 if v8 else 7 if v7 else 6 if v6
        else 5 if v5 else 4 if v4 else 3 if v3 else 2 if v2 else 1
    )
    basis = RecapSemanticBasisV12(
        request_version=request_version,
        derivation=SOURCE_BINDING_DERIVATION_V11,
        operation_derivation=derivation,
        operation_manifest_schema=manifest["schema"],
        operation_basis=operation_basis,
        parent_source_uri=source_ref.uri,
        child_snapshot_uri=child_source_uri,
        source_artifact_id=parent.source_artifact_id,
        source_revision_sha256=source_sha,
        span_index_uri=span_ref.uri,
        span_index_sha256=span_sha,
    )
    lineage["semantic_source_binding_basis_v12"] = basis.model_dump(
        mode="json", by_alias=True,
    )
    lineage["semantic_disposition"] = {
        "version": 1, "state": "held", "basis_sha256": basis.digest(),
    }
    response_type = (
        RecapCandidateCorrectionResponseV10 if v10
        else RecapCandidateCorrectionResponseV9 if v9
        else RecapCandidateCorrectionResponseV8 if v8
        else RecapCandidateCorrectionResponseV7 if v7
        else RecapCandidateCorrectionResponseV6 if v6
        else RecapCandidateCorrectionResponseV5 if v5
        else RecapCandidateCorrectionResponseV4 if v4
        else RecapCandidateCorrectionResponseV3 if v3
        else RecapCandidateCorrectionResponseV2 if v2
        else RecapCandidateCorrectionResponse
    )

    with _source_binding_child_lock(root, child_id):
        # The first preflight can be followed by a wait on another request for
        # this deterministic child. Re-read under the lock so a source or span
        # change during that wait cannot claim a DRAFT row/package from stale
        # pre-lock bytes.
        locked_snapshot = _preflight_source_snapshot(parent, resolved, root)
        if (
            locked_snapshot[0] != artifact
            or locked_snapshot[1] != parent_bytes
            or locked_snapshot[2] != source_bytes
            or locked_snapshot[3] != span_bytes
            or locked_snapshot[5] != world_scope
        ):
            raise _reject(
                "recap source snapshot changed while waiting for the child lock",
                status_code=409,
            )
        legacy_exists, legacy_files = _source_binding_package_state(root, legacy_child_id)
        try:
            legacy_run = get_extraction_run(root, legacy_child_id)
        except GraphRunRegistryError as exc:
            if exc.status_code != 404:
                raise _reject(f"legacy child lookup failed: {exc}", status_code=409) from exc
            legacy_run = None
        if legacy_run is None:
            if legacy_exists:
                raise _reject(
                    f"legacy child {legacy_child_id} has an orphan candidate package; "
                    "it cannot be adopted by source binding",
                    status_code=409,
                )
        else:
            if (
                legacy_run.status != ExtractionRunStatus.REVIEWABLE
                or legacy_run.lineage.get("derivation") != derivation
                or legacy_run.lineage.get("parent_run_id") != parent.run_id
                or legacy_run.lineage.get("manifest_sha256") != manifest_sha
                or legacy_run.lineage.get("semantic_candidate_manifest") != manifest
                or legacy_run.components.get("candidate_graph") is None
                or legacy_run.components["candidate_graph"].uri
                != f"out/graph_memory/derived_candidates/{legacy_child_id}/candidate_graph.json"
                or set(legacy_files) != {"candidate_graph.json"}
                or legacy_files.get("candidate_graph.json") is None
                or legacy_run.components.get("source_artifact") != source_ref
                or legacy_run.components.get("source_span_index") != span_ref
                or not verify_child_replay(legacy_run, parent, root)
            ):
                raise _reject(
                    f"legacy child {legacy_child_id} is not an exact reusable REVIEWABLE child",
                    status_code=409,
                )
            from apps.live_control_server.services.recap_semantic_disposition import (
                assess_recap_semantics,
            )
            legacy_assessment = assess_recap_semantics(
                legacy_run, parent=parent, source_revision_id=source_sha, root=root,
            )
            legacy_disposition = legacy_run.lineage.get("semantic_disposition") or {}
            if (
                legacy_assessment.basis is None
                or legacy_assessment.basis_sha256 is None
                or legacy_disposition.get("basis_sha256") != legacy_assessment.basis_sha256
                or legacy_disposition.get("state") not in {"held", "accepted", "rejected"}
            ):
                raise _reject(
                    f"legacy child {legacy_child_id} has no exact reusable semantic basis",
                    status_code=409,
                )
            return response_type(
                run_id=legacy_child_id, parent_run_id=parent.run_id,
                parent_candidate_sha256=parent_sha,
                candidate_sha256=legacy_run.components["candidate_graph"].sha256.removeprefix("sha256:"),
                manifest_sha256=manifest_sha,
                semantic_basis_sha256=legacy_assessment.basis_sha256,
                semantic_state=legacy_disposition["state"],
            )

        package_exists, package_files = _source_binding_package_state(root, child_id)
        try:
            child = get_extraction_run(root, child_id)
        except GraphRunRegistryError as exc:
            if exc.status_code != 404:
                raise _reject(
                    f"source-binding child {child_id} lookup failed: {exc}", status_code=409,
                ) from exc
            child = None
        if child is None and package_exists:
            raise _reject(
                f"source-binding child {child_id} has an orphan package; it cannot be adopted",
                status_code=409,
            )
        existing_child_row = child is not None
        if child is not None:
            if (
                child.components != components
                or child.source_artifact_id != parent.source_artifact_id
                or child.source_domain != "recap"
                or child.profile_id != parent.profile_id
                or child.campaign_id != parent.campaign_id
                or child.session_id != parent.session_id
                or set(child.lineage) != set(lineage)
                or {key: child.lineage.get(key) for key in lineage if key != "semantic_disposition"}
                != {key: value for key, value in lineage.items() if key != "semantic_disposition"}
            ):
                raise _reject(
                    f"source-binding child {child_id} row identity conflicts; held status preserved",
                    status_code=409,
                )
            if child.status != ExtractionRunStatus.DRAFT and (
                set(package_files) != {"source.md", "candidate_graph.json"}
                or package_files.get("source.md") != source_bytes
                or package_files.get("candidate_graph.json") != child_bytes
            ):
                raise _reject(
                    f"source-binding child {child_id} is {child.status.value} with an incomplete package; held status preserved",
                    status_code=409,
                )
        else:
            try:
                child = create_extraction_run(
                    root, run_id=child_id, source_artifact_id=parent.source_artifact_id,
                    source_domain="recap", campaign_id=parent.campaign_id,
                    session_id=parent.session_id, profile_id=parent.profile_id,
                    components=components, status=ExtractionRunStatus.DRAFT,
                    lineage=lineage,
                )
            except GraphRunRegistryError as exc:
                try:
                    child = get_extraction_run(root, child_id)
                except GraphRunRegistryError:
                    raise _reject(
                        f"source-binding child {child_id} DRAFT creation failed: {exc}; "
                        "no held child row was confirmed",
                        status_code=409,
                    ) from exc
                if child.lineage != lineage or child.components != components:
                    raise _reject(
                        f"source-binding child {child_id} DRAFT creation conflicted; held status preserved",
                        status_code=409,
                    ) from exc

        if child.status not in _LIFECYCLE:
            raise _reject(
                f"source-binding child {child_id} has non-resumable status {child.status.value}; held status preserved",
                status_code=409,
            )
        _publish_child_package_files(
            root, child_id, source_bytes=source_bytes, candidate_bytes=child_bytes,
            allow_existing=existing_child_row,
        )
        package_exists, package_files = _source_binding_package_state(root, child_id)
        if (
            not package_exists
            or package_files != {"source.md": source_bytes, "candidate_graph.json": child_bytes}
        ):
            raise _reject(
                f"source-binding child {child_id} package did not seal; held status preserved",
                status_code=409,
            )
        for _ in range(8):
            if child.status == ExtractionRunStatus.REVIEWABLE:
                break
            next_status = _LIFECYCLE[_LIFECYCLE.index(child.status) + 1]
            try:
                child = update_extraction_run_status(
                    root, child_id, status=next_status, expected_revision=child.revision,
                )
            except GraphRunRegistryError as exc:
                if exc.status_code != 409:
                    raise _reject(
                        f"source-binding child {child_id} seal failed: {exc}; "
                        "held status preserved",
                        status_code=409,
                    ) from exc
                child = get_extraction_run(root, child_id)
        if child.status != ExtractionRunStatus.REVIEWABLE or not verify_child_replay(child, parent, root):
            raise _reject(
                f"source-binding child {child_id} could not be replayed and sealed; "
                "held status preserved",
                status_code=409,
            )
        try:
            resolved_child = resolve_promotable_ingest_run(child_id, root=root)
        except PromotableIngestRunError as exc:
            raise _reject(
                f"source-binding child {child_id} could not be resolved; held status preserved",
                status_code=409,
            ) from exc
        if resolved_child.run_id != child_id:
            raise _reject(
                f"source-binding child {child_id} resolved to another run; held status preserved",
                status_code=409,
            )
        raw = child.lineage.get("semantic_disposition") or {}
        semantic_state = raw.get("state")
        if semantic_state not in {"held", "accepted", "rejected"} or raw.get("basis_sha256") != basis.digest():
            raise _reject(
                f"source-binding child {child_id} semantic basis conflicts; held status preserved",
                status_code=409,
            )
        if semantic_state == "held" and raw != lineage["semantic_disposition"]:
            raise _reject(
                f"source-binding child {child_id} semantic hold conflicts; held status preserved",
                status_code=409,
            )
        if semantic_state in {"accepted", "rejected"}:
            from apps.live_control_server.services.recap_semantic_disposition import (
                assess_recap_semantics,
            )
            assessment = assess_recap_semantics(
                child, parent=parent, source_revision_id=source_sha, root=root,
            )
            if assessment.disposition is None or assessment.disposition.get("state") != semantic_state:
                raise _reject(
                    f"source-binding child {child_id} semantic decision conflicts; held status preserved",
                    status_code=409,
                )
        return response_type(
            run_id=child_id, parent_run_id=parent.run_id,
            parent_candidate_sha256=parent_sha, candidate_sha256=child_sha,
            manifest_sha256=manifest_sha, semantic_basis_sha256=basis.digest(),
            semantic_state=semantic_state,
        )

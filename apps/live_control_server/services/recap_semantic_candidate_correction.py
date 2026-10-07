"""Bounded, immutable semantic correction of one exact recap candidate."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequest,
    RecapCandidateCorrectionResponse,
)
from apps.live_control_server.services.exact_run_evidence_correction import (
    _LIFECYCLE,
    _canonical_bytes,
    _reject,
    _sha,
    _write_child_candidate,
)
from apps.live_control_server.services.extract_promote import (
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
    load_typed_candidate_graph,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)

DERIVATION = "operator_recap_semantic_candidate_correction_v1"
MANIFEST_SCHEMA = "dmb_recap_semantic_candidate_manifest_v1"
PROFILE = "recap_category_v1@1.0"


def _contains(value: object, target: str) -> bool:
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, list):
        return any(_contains(item, target) for item in value)
    return value == target


def replay_candidate(parent: dict, manifest: dict) -> dict:
    """Reconstruct exactly one bounded edit; never patch arbitrary JSON."""
    if set(manifest) != {"schema", "node_description_replacements", "omitted_edge_ids"} or manifest.get("schema") != MANIFEST_SCHEMA:
        raise _reject("semantic candidate manifest is malformed")
    replacements = manifest["node_description_replacements"]
    omitted = manifest["omitted_edge_ids"]
    if (
        not isinstance(replacements, list) or len(replacements) > 1
        or not isinstance(omitted, list) or len(omitted) > 1
        or not replacements and not omitted
    ):
        raise _reject("semantic candidate manifest exceeds bounded scope")
    child = copy.deepcopy(parent)
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
        expected = replay_candidate(json.loads(parent_bytes), manifest)
        return child_bytes == _canonical_bytes(expected)
    except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def correct_recap_candidate(request: RecapCandidateCorrectionRequest) -> RecapCandidateCorrectionResponse:
    """Create one held reviewable child without altering parent or WorldGraph."""
    from application_state.ingest.service import RecapSemanticBasisV2

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
    source_sha = _sha(resolved.normalized_recap_path.read_bytes())
    span_sha = _sha(resolved.source_span_index_path.read_bytes())
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
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "node_description_replacements": [
            item.model_dump(mode="json") for item in sorted(request.node_description_replacements, key=lambda value: value.node_id)
        ],
        "omitted_edge_ids": sorted(request.omitted_edge_ids),
    }
    payload = replay_candidate(parent_payload, manifest)
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
    child_id = str(uuid5(NAMESPACE_URL, f"dmb:{DERIVATION}:{parent.run_id}:{parent_sha}:{manifest_sha}"))
    child_bytes = _canonical_bytes(payload)
    child_sha = _sha(child_bytes)
    child_path = root / "out" / "graph_memory" / "derived_candidates" / child_id / "candidate_graph.json"
    child_uri = child_path.relative_to(root).as_posix()
    basis = RecapSemanticBasisV2(
        parent_run_id=parent.run_id, parent_candidate_sha256=parent_sha,
        manifest_sha256=manifest_sha, child_run_id=child_id,
        candidate_uri=child_uri, candidate_sha256=child_sha,
        source_artifact_id=parent.source_artifact_id,
        source_uri=source_ref.uri, source_revision_sha256=source_sha,
        span_index_uri=span_ref.uri, span_index_sha256=span_sha,
        profile_id=parent.profile_id, profile_version="1.0",
        campaign_id=parent.campaign_id, session_id=parent.session_id,
    )
    lineage = {
        "derivation": DERIVATION,
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
    return RecapCandidateCorrectionResponse(
        run_id=child_id, parent_run_id=parent.run_id,
        parent_candidate_sha256=parent_sha, candidate_sha256=child_sha,
        manifest_sha256=manifest_sha, semantic_basis_sha256=basis.digest(),
        semantic_state=semantic_state,
    )

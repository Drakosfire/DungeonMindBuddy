"""Explicit, immutable quote-only child of one managed-World ExtractionRun."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.extract_promote import (
    ExactRunEvidenceCorrectionRequest,
    ExactRunEvidenceCorrectionResponse,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _assert_and_project_candidate_evidence,
    _assert_candidate_scope_matches_run,
    _load_frozen_span_index_for_resolved_run,
    _paragraph_for_span,
)
from apps.live_control_server.services.first_world_graph import admit_managed_world
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
from graph_memory.anchor_quotes import find_anchor_quote_matches
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)

_PROFILE = "worldbuilding_shepherds_flock_v0@0.1"
_DERIVATION = "operator_literal_evidence_correction_v1"
_LIFECYCLE = (
    ExtractionRunStatus.DRAFT,
    ExtractionRunStatus.PREPARED,
    ExtractionRunStatus.EXTRACTED,
    ExtractionRunStatus.VALIDATED,
    ExtractionRunStatus.REVIEWABLE,
)


def _reject(message: str, *, status_code: int = 422) -> ExtractPromoteError:
    return ExtractPromoteError(
        message,
        code="evidence_correction_invalid" if status_code == 422 else "evidence_correction_conflict",
        status_code=status_code,
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _qualify_payload(*, payload: dict, resolved: object, source_prose: str, span_index: object) -> None:
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )

    _assert_candidate_scope_matches_run(
        payload,
        campaign_id=resolved.campaign_id,
        session_id=resolved.session_id,
    )
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=source_prose,
        source_artifact_id=resolved.source_artifact_id,
        span_index=span_index,
    )
    profile = get_extraction_profile(
        WORLDBUILDING_PROFILE_ID, WORLDBUILDING_PROFILE_VERSION
    )
    validator = profile.post_extraction_validator
    if validator is None:
        raise _reject("managed-World extraction profile has no validator")
    errors = [str(item) for item in validator(payload) if str(item).strip()]
    if errors:
        raise _reject("child candidate failed managed-World profile validation: " + "; ".join(errors))


def _write_child_candidate(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise _reject("derived candidate path contains different bytes", status_code=409)
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".candidate-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        if path.exists() and path.read_bytes() != data:
            raise _reject("derived candidate path contains different bytes", status_code=409)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def correct_exact_run_evidence(
    request: ExactRunEvidenceCorrectionRequest,
) -> ExactRunEvidenceCorrectionResponse:
    """Seal one quote-only child; never mutate parent or publish a World head."""
    repo = repo_root()
    try:
        resolved = resolve_promotable_ingest_run(request.parent_run_id, root=repo)
        parent = get_extraction_run(repo, request.parent_run_id)
    except (PromotableIngestRunError, GraphRunRegistryError) as exc:
        raise _reject(f"parent run is not reviewable: {exc}") from exc
    if (
        resolved.source_domain != "worldbuilding"
        or parent.source_domain != "worldbuilding"
        or resolved.extraction_profile != _PROFILE
        or parent.profile_id != _PROFILE
    ):
        raise _reject("correction requires the exact managed-World worldbuilding profile")
    if not resolved.world_id or resolved.session_id:
        raise _reject("worldbuilding run has an invalid World/session binding")
    try:
        admit_managed_world(repo, resolved.world_id)
    except Exception as exc:  # noqa: BLE001 - managed World admission fails closed
        raise _reject("parent run does not belong to a managed World") from exc

    parent_bytes = resolved.candidate_graph_path.read_bytes()
    parent_sha = _sha(parent_bytes)
    if parent_sha != request.parent_candidate_sha256:
        raise _reject("parent candidate digest changed", status_code=409)
    try:
        payload = json.loads(parent_bytes)
        source_prose = resolved.normalized_recap_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        raise _reject("parent candidate or source is unreadable") from exc
    if not isinstance(payload, dict):
        raise _reject("parent candidate root must be an object")
    span_index = _load_frozen_span_index_for_resolved_run(resolved)
    # Integrity, artifact and span bindings must already be sound. Only false
    # quote membership is allowed to pass through this inspection gate.
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=source_prose,
        source_artifact_id=resolved.source_artifact_id,
        span_index=span_index,
        inspect_false_anchor_quotes=True,
    )
    spans = {span.source_span_id: span for span in span_index.spans}
    source_lines = source_prose.splitlines()
    keyed: dict[tuple[str, int, int], object] = {}
    for correction in request.corrections:
        key = (correction.assertion_id, correction.evidence_index, correction.quote_index)
        if key in keyed:
            raise _reject("duplicate correction target")
        keyed[key] = correction
    ordered = [keyed[key] for key in sorted(keyed)]
    for correction in ordered:
        holders = [
            item for kind in ("nodes", "edges") for item in (payload.get(kind) or [])
            if str(item.get("node_id") or item.get("edge_id") or "") == correction.assertion_id
        ]
        if len(holders) != 1:
            raise _reject("correction assertion ID is missing or ambiguous")
        refs = holders[0].get("evidence_refs") or []
        if correction.evidence_index >= len(refs):
            raise _reject("correction evidence index is not present")
        ref = refs[correction.evidence_index]
        if ref.get("source_span_ref_id") != correction.source_span_ref_id:
            raise _reject("correction source span does not match the frozen candidate", status_code=409)
        quotes = ref.get("anchor_quotes") or []
        if correction.quote_index >= len(quotes) or quotes[correction.quote_index] != correction.original_quote:
            raise _reject("correction original quote/index is stale", status_code=409)
        span = spans.get(correction.source_span_ref_id)
        if span is None:
            raise _reject("correction references an unknown frozen source span")
        paragraph = _paragraph_for_span(
            source_lines, start_line=int(span.start_line), end_line=int(span.end_line)
        ).strip()
        if find_anchor_quote_matches(paragraph, [correction.original_quote]):
            raise _reject("correction target is already literal")
        replacement = correction.replacement_quote.strip()
        if not replacement or not find_anchor_quote_matches(paragraph, [replacement]):
            raise _reject("replacement quote is not literal in the exact source paragraph")
        quotes[correction.quote_index] = replacement
    _qualify_payload(payload=payload, resolved=resolved, source_prose=source_prose, span_index=span_index)

    canonical_corrections = [item.model_dump(mode="json", by_alias=True) for item in ordered]
    correction_digest = _sha(_canonical_bytes({
        "parentRunId": request.parent_run_id,
        "parentCandidateSha256": parent_sha,
        "corrections": canonical_corrections,
    }))
    child_id = str(uuid5(NAMESPACE_URL, f"dmb:{_DERIVATION}:{correction_digest}"))
    child_bytes = _canonical_bytes(payload)
    child_sha = _sha(child_bytes)
    child_path = repo / "out" / "graph_memory" / "derived_candidates" / child_id / "candidate_graph.json"
    child_uri = child_path.relative_to(repo).as_posix()
    lineage = {
        "derivation": _DERIVATION,
        "parent_run_id": request.parent_run_id,
        "parent_candidate_sha256": parent_sha,
        "correction_digest": correction_digest,
    }
    components = dict(parent.components)
    components[ExtractionRunComponentKind.CANDIDATE_GRAPH.value] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri=child_uri,
        sha256=child_sha,
        exists=True,
    )
    try:
        child = get_extraction_run(repo, child_id)
    except GraphRunRegistryError as exc:
        if exc.status_code != 404:
            raise _reject(f"derived run lookup failed: {exc}") from exc
        try:
            child = create_extraction_run(
                repo,
                run_id=child_id,
                source_artifact_id=parent.source_artifact_id,
                source_domain=parent.source_domain,
                campaign_id=parent.campaign_id,
                session_id=parent.session_id,
                profile_id=parent.profile_id,
                components=components,
                status=ExtractionRunStatus.DRAFT,
                lineage=lineage,
            )
        except GraphRunRegistryError:
            # An identical concurrent request may have won the create race.
            child = get_extraction_run(repo, child_id)
    if child.lineage != lineage or child.components != components or child.source_artifact_id != parent.source_artifact_id:
        raise _reject("derived run identity conflicts with existing run", status_code=409)
    _write_child_candidate(child_path, child_bytes)
    for _ in range(8):
        child = get_extraction_run(repo, child_id)
        if child.status == ExtractionRunStatus.REVIEWABLE:
            break
        if child.status not in _LIFECYCLE:
            raise _reject("derived run is not in a sealable lifecycle state", status_code=409)
        next_status = _LIFECYCLE[_LIFECYCLE.index(child.status) + 1]
        try:
            child = update_extraction_run_status(
                repo, child_id, status=next_status, expected_revision=child.revision
            )
        except GraphRunRegistryError as exc:
            if exc.status_code != 409:
                raise _reject(f"derived run seal failed: {exc}") from exc
    if child.status != ExtractionRunStatus.REVIEWABLE:
        raise _reject("derived run could not be sealed", status_code=409)
    if child_path.read_bytes() != child_bytes:
        raise _reject("derived candidate changed during seal", status_code=409)
    # Canonical registry resolution checks source/index/candidate component SHAs.
    resolve_promotable_ingest_run(child_id, root=repo)
    return ExactRunEvidenceCorrectionResponse(
        run_id=child_id,
        parent_run_id=request.parent_run_id,
        parent_candidate_sha256=parent_sha,
        candidate_sha256=child_sha,
        correction_digest=correction_digest,
    )

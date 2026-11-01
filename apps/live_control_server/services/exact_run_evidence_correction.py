"""Explicit, immutable quote-only child of one managed-World ExtractionRun."""

from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from apps.live_control_server.config import artifact_data_root, repo_root
from apps.live_control_server.models.extract_promote import (
    ExactRunEvidenceCorrectionRequest,
    ExactRunEvidenceCorrectionResponse,
    WorldbuildingEvidenceCorrectionRequest,
    WorldbuildingFrozenSpanCatalog,
    RecapEvidenceCorrectionResponse,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _assert_and_project_candidate_evidence,
    _assert_candidate_scope_matches_run,
    _paragraph_for_span,
)
from apps.live_control_server.services.first_world_graph import admit_managed_world
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
    get_extraction_run,
    load_reviewable_extraction_data,
    update_extraction_run_status,
)
from graph_memory.anchor_quotes import find_anchor_quote_matches
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)

_PROFILE = "worldbuilding_shepherds_flock_v0@0.1"
_DERIVATION = "operator_frozen_evidence_partition_v2"
_RECAP_DERIVATION = "operator_recap_literal_evidence_correction_v1"
_RECAP_PROFILE = "recap_category_v1@1.0"
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


def _frozen_recap_world_lineage(parent: ExtractionRun) -> dict[str, object]:
    """Copy the exact parent World binding into a derived recap run.

    A v2 SourceArtifact is World-scoped, so its parent must already carry the
    immutable context that authorized it. This helper never resolves or infers
    a World; the run registry checks that the copied values still match the
    registered source before persisting the child.
    """
    context = parent.lineage.get("world_campaign_ingest_context")
    if context is not None:
        if (
            not isinstance(context, dict)
            or not isinstance(context.get("native_world_id"), str)
            or not context["native_world_id"].strip()
            or context.get("campaign_id") != parent.campaign_id
        ):
            raise _reject("parent recap run has invalid frozen World context")
        return {"world_campaign_ingest_context": dict(context)}

    native_world_id = parent.lineage.get("native_world_id")
    campaign_id = parent.lineage.get("campaign_id")
    if parent.source_artifact_id.startswith("artifact:recap:v2:"):
        if (
            not isinstance(native_world_id, str)
            or not native_world_id.strip()
            or campaign_id != parent.campaign_id
        ):
            raise _reject("parent recap run is missing its exact verified World context")

    copied: dict[str, object] = {}
    if native_world_id is not None:
        copied["native_world_id"] = native_world_id
    if campaign_id is not None:
        copied["campaign_id"] = campaign_id
    return copied


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _qualify_payload(*, payload: dict, parent: ExtractionRun, source_prose: str, span_index: object) -> None:
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )

    _assert_candidate_scope_matches_run(
        payload,
        campaign_id=parent.campaign_id,
        session_id=parent.session_id,
    )
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=source_prose,
        source_artifact_id=parent.source_artifact_id,
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


def _apply_literal_quote_corrections(
    payload: dict,
    request: ExactRunEvidenceCorrectionRequest,
    *,
    source_prose: str,
    span_index: object,
) -> list:
    """Change only selected false quotes against the frozen source paragraphs."""
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
            item for kind, id_field in (("nodes", "node_id"), ("edges", "edge_id"), ("beats", "beat_id"))
            for item in (payload.get(kind) or [])
            if str(item.get(id_field) or "") == correction.assertion_id
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
    return ordered


def _worldbuilding_parent(run_id):
    repo = artifact_data_root(repo_root())
    try:
        data = load_reviewable_extraction_data(repo, run_id)
    except GraphRunRegistryError as exc:
        raise ExtractPromoteError(
            f"parent Worldbuilding evidence unavailable: {exc}",
            code="evidence_correction_unavailable" if exc.status_code >= 500 else "evidence_correction_invalid",
            status_code=exc.status_code,
        ) from exc
    parent = data.run
    if parent.source_domain != "worldbuilding" or parent.profile_id != _PROFILE:
        raise _reject("correction requires the exact managed-World worldbuilding profile")
    if not data.source_artifact.world_id or parent.session_id:
        raise _reject("worldbuilding run has an invalid World/session binding")
    try:
        admit_managed_world(repo, data.source_artifact.world_id)
    except Exception as exc:  # noqa: BLE001 - managed World admission fails closed
        raise _reject("parent run does not belong to a managed World") from exc

    try:
        payload = json.loads(data.candidate_bytes)
        source_prose = data.source_bytes.decode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _reject("parent candidate or source is unreadable") from exc
    if not isinstance(payload, dict):
        raise _reject("parent candidate root must be an object")
    span_index = data.span_index
    # Integrity, artifact and span bindings must already be sound. Only false
    # quote membership is allowed to pass through this inspection gate.
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=source_prose,
        source_artifact_id=parent.source_artifact_id,
        span_index=span_index,
        inspect_false_anchor_quotes=True,
    )
    return repo, data, parent, payload, source_prose, span_index


def get_worldbuilding_frozen_spans(run_id: str) -> WorldbuildingFrozenSpanCatalog:
    """Project exact frozen paragraphs, never client-derived paragraph identities."""
    _, data, parent, payload, source, index = _worldbuilding_parent(run_id)
    spans = list(index.spans)
    if len({span.source_span_id for span in spans}) != len(spans):
        raise _reject("frozen source span IDs are ambiguous")
    return WorldbuildingFrozenSpanCatalog(
        parent_run_id=run_id, parent_revision=parent.revision, parent_status=parent.status,
        world_id=data.source_artifact.world_id, source_artifact_id=parent.source_artifact_id,
        source_sha256=_sha(data.source_bytes),
        span_index_sha256=_sha(data.span_bytes),
        parent_candidate_sha256=_sha(data.candidate_bytes),
        spans=[dict(source_span_ref_id=span.source_span_id, start_line=span.start_line,
            end_line=span.end_line, paragraph_text=_paragraph_for_span(source.splitlines(),
                start_line=int(span.start_line), end_line=int(span.end_line)).strip()) for span in spans],
        evidence_refs=[dict(assertion_id=row.get("node_id") or row.get("edge_id"),
            evidence_index=i, ref_sha256=_sha(_canonical_bytes(ref)))
            for collection in ("nodes", "edges") for row in payload.get(collection, [])
            for i, ref in enumerate(row.get("evidence_refs", []))])


def _apply_evidence_partitions(payload, request, *, source_prose, span_index):
    """Complete original-quote partitions; no automatic matching or semantic edits."""
    from copy import deepcopy
    spans = list(span_index.spans)
    if len({span.source_span_id for span in spans}) != len(spans):
        raise _reject("frozen source span IDs are ambiguous")
    paragraphs = {span.source_span_id: _paragraph_for_span(source_prose.splitlines(),
        start_line=int(span.start_line), end_line=int(span.end_line)).strip() for span in spans}
    targets = {}
    for change in request.corrections:
        key = (change.assertion_id, change.evidence_index)
        if key in targets:
            raise _reject("duplicate correction target")
        targets[key] = change
    plans = []
    for key, change in sorted(targets.items()):
        holders = [row for collection in ("nodes", "edges") for row in payload.get(collection, [])
            if (row.get("node_id") or row.get("edge_id")) == change.assertion_id]
        if len(holders) != 1:
            raise _reject("correction assertion ID is missing or ambiguous")
        refs = holders[0].get("evidence_refs", [])
        if change.evidence_index >= len(refs):
            raise _reject("correction evidence index is stale", status_code=409)
        old = refs[change.evidence_index]
        if _sha(_canonical_bytes(old)) != change.expected_ref_sha256:
            raise _reject("correction evidence preimage is stale", status_code=409)
        quotes = old.get("anchor_quotes", [])
        if not quotes:
            raise _reject("correction requires original quote assignments")
        seen_indices, replacements = set(), []
        for part in change.parts:
            sid = part.source_span_ref_id
            if sid not in paragraphs:
                raise _reject("correction source span is unknown")
            assignments = sorted(part.quote_assignments, key=lambda item: item.original_quote_index)
            replacement = []
            for assignment in assignments:
                index = assignment.original_quote_index
                if index >= len(quotes) or index in seen_indices:
                    raise _reject("original quote index is unknown or duplicated")
                seen_indices.add(index)
                if not find_anchor_quote_matches(paragraphs[sid], [assignment.replacement_quote]):
                    raise _reject("replacement quote is not literal in the selected frozen paragraph")
                replacement.append(assignment.replacement_quote)
            ref = deepcopy(old)
            ref["source_span_ref_id"], ref["anchor_quotes"] = sid, replacement
            replacements.append((assignments[0].original_quote_index, ref, [a.original_quote_index for a in assignments]))
        if seen_indices != set(range(len(quotes))):
            raise _reject("every original quote index must be assigned exactly once")
        ordered_parts = sorted(replacements)
        if [i for _, _, indices in ordered_parts for i in indices] != list(range(len(quotes))):
            raise _reject("paragraph partitions must preserve original quote order")
        new_refs = [ref for _, ref, _ in ordered_parts]
        if new_refs == [old]:
            raise _reject("correction evidence is unchanged")
        plans.append((holders[0], change.evidence_index, new_refs))
    # Descending indices avoid shifting another selected evidence ref in the same holder.
    for holder, index, replacements in sorted(plans, key=lambda item: item[1], reverse=True):
        holder["evidence_refs"][index:index + 1] = replacements
    return [targets[key] for key in sorted(targets)]


def correct_exact_run_evidence(
    request: WorldbuildingEvidenceCorrectionRequest,
) -> ExactRunEvidenceCorrectionResponse:
    """Derive an unpublished, completely qualified child from explicit frozen spans."""
    repo, data, parent, payload, source_prose, span_index = _worldbuilding_parent(request.parent_run_id)
    parent_sha = _sha(data.candidate_bytes)
    if (parent.revision != request.expected_parent_revision or parent.status != request.expected_parent_status
        or parent_sha != request.parent_candidate_sha256 or data.source_artifact.world_id != request.world_id
        or parent.source_artifact_id != request.source_artifact_id
        or _sha(data.source_bytes) != request.source_sha256
        or _sha(data.span_bytes) != request.span_index_sha256):
        raise _reject("frozen parent/source/span-index preimage changed", status_code=409)
    ordered = _apply_evidence_partitions(
        payload, request, source_prose=source_prose, span_index=span_index
    )
    _qualify_payload(payload=payload, parent=parent, source_prose=source_prose, span_index=span_index)

    canonical_corrections = [item.model_dump(mode="json", by_alias=True) for item in ordered]
    correction_digest = _sha(_canonical_bytes(request.model_dump(mode="json", by_alias=True) |
        {"corrections": canonical_corrections}))
    child_id = str(uuid5(NAMESPACE_URL, f"dmb:{_DERIVATION}:{correction_digest}"))
    child_bytes = _canonical_bytes(payload)
    child_sha = _sha(child_bytes)
    # Historical locator metadata only; actual child bytes belong to APP.
    child_uri = f"out/graph_memory/derived_candidates/{child_id}/candidate_graph.json"
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
    if (
        child.lineage != lineage
        or child.components != components
        or child.source_artifact_id != parent.source_artifact_id
        or child.source_domain != parent.source_domain
        or child.profile_id != parent.profile_id
        or child.campaign_id != parent.campaign_id
        or child.session_id != parent.session_id
    ):
        raise _reject("derived run identity conflicts with existing run", status_code=409)
    from application_state.ingest.components import persist_component_payload

    for kind, data in (("candidate_graph", child_bytes),
                       ("source_span_index", data.span_bytes)):
        persist_component_payload(run_id=child_id, expected_revision=child.revision,
                                  kind=kind, payload=data)
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
    # The same database owner validates the final bound child evidence.
    try:
        load_reviewable_extraction_data(repo, child_id)
    except GraphRunRegistryError as exc:
        raise ExtractPromoteError(str(exc), code="evidence_correction_invalid",
                                  status_code=exc.status_code) from exc
    return ExactRunEvidenceCorrectionResponse(
        run_id=child_id,
        parent_run_id=request.parent_run_id,
        parent_candidate_sha256=parent_sha,
        candidate_sha256=child_sha,
        correction_digest=correction_digest,
    )


def correct_recap_run_evidence(
    request: ExactRunEvidenceCorrectionRequest,
) -> RecapEvidenceCorrectionResponse:
    """Create one literal-only recap child with a canonical semantic hold."""
    from application_state.ingest.service import RecapSemanticBasisV1
    from apps.live_control_server.services.recap_semantic_disposition import (
        assess_recap_semantics,
    )

    repo = artifact_data_root(repo_root())
    try:
        data = load_reviewable_extraction_data(repo, request.parent_run_id)
    except GraphRunRegistryError as exc:
        raise ExtractPromoteError(
            f"parent recap evidence unavailable: {exc}",
            code="evidence_correction_unavailable" if exc.status_code >= 500 else "evidence_correction_invalid",
            status_code=exc.status_code,
        ) from exc
    parent = data.run
    if (
        parent.source_domain != "recap"
        or parent.profile_id != _RECAP_PROFILE
        or not parent.campaign_id
        or not parent.session_id
    ):
        raise _reject("correction requires an exact frozen recap review bundle")
    world_lineage = _frozen_recap_world_lineage(parent)

    parent_bytes = data.candidate_bytes
    parent_sha = _sha(parent_bytes)
    source = parent.components[ExtractionRunComponentKind.SOURCE_ARTIFACT.value]
    spans = parent.components[ExtractionRunComponentKind.SOURCE_SPAN_INDEX.value]
    source_sha = source.sha256.removeprefix("sha256:").lower()
    span_sha = spans.sha256.removeprefix("sha256:").lower()
    if parent_sha != request.parent_candidate_sha256:
        raise _reject("parent candidate or source digest changed", status_code=409)
    try:
        payload = json.loads(parent_bytes)
        source_prose = data.source_bytes.decode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _reject("parent candidate or source is unreadable") from exc
    if not isinstance(payload, dict):
        raise _reject("parent candidate root must be an object")
    span_index = data.span_index
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=source_prose,
        source_artifact_id=parent.source_artifact_id,
        span_index=span_index,
        inspect_false_anchor_quotes=True,
    )
    ordered = _apply_literal_quote_corrections(
        payload, request, source_prose=source_prose, span_index=span_index
    )
    _assert_candidate_scope_matches_run(
        payload, campaign_id=parent.campaign_id, session_id=parent.session_id
    )
    _assert_and_project_candidate_evidence(
        candidate_payload=payload,
        source_prose=source_prose,
        source_artifact_id=parent.source_artifact_id,
        span_index=span_index,
    )

    correction_digest = _sha(_canonical_bytes({
        "parentRunId": request.parent_run_id,
        "parentCandidateSha256": parent_sha,
        "corrections": [item.model_dump(mode="json", by_alias=True) for item in ordered],
    }))
    child_id = str(uuid5(NAMESPACE_URL, f"dmb:{_RECAP_DERIVATION}:{correction_digest}"))
    child_bytes = _canonical_bytes(payload)
    child_sha = _sha(child_bytes)
    # Historical locator metadata only; actual child bytes belong to APP.
    child_uri = f"out/graph_memory/derived_candidates/{child_id}/candidate_graph.json"
    basis = RecapSemanticBasisV1(
        parent_run_id=parent.run_id,
        parent_candidate_sha256=parent_sha,
        correction_digest=correction_digest,
        child_run_id=child_id,
        candidate_uri=child_uri,
        candidate_sha256=child_sha,
        source_artifact_id=parent.source_artifact_id,
        source_uri=source.uri,
        source_revision_sha256=source_sha,
        span_index_uri=spans.uri,
        span_index_sha256=span_sha,
        profile_id=parent.profile_id,
        profile_version="1.0",
        campaign_id=parent.campaign_id,
        session_id=parent.session_id,
    )
    lineage = {
        # A derived recap run must stay bound to the exact World context that
        # authorized its parent. Copy frozen values only; this path must never
        # resolve a current/default World for an already captured run.
        **world_lineage,
        "derivation": _RECAP_DERIVATION,
        "parent_run_id": parent.run_id,
        "parent_candidate_sha256": parent_sha,
        "correction_digest": correction_digest,
        "semantic_disposition": {
            "version": 1, "state": "held", "basis_sha256": basis.digest(),
        },
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
                source_domain="recap",
                campaign_id=parent.campaign_id,
                session_id=parent.session_id,
                profile_id=parent.profile_id,
                components=components,
                status=ExtractionRunStatus.DRAFT,
                lineage=lineage,
            )
        except GraphRunRegistryError:
            child = get_extraction_run(repo, child_id)
    identity_lineage = {
        key: child.lineage.get(key)
        for key in ("derivation", "parent_run_id", "parent_candidate_sha256", "correction_digest")
    }
    expected_identity_lineage = {
        key: lineage[key] for key in identity_lineage
    }
    raw_disposition = child.lineage.get("semantic_disposition")
    semantic_state = "held"
    if isinstance(raw_disposition, dict) and raw_disposition.get("state") in {"accepted", "rejected"}:
        assessment = assess_recap_semantics(
            child, parent=parent, source_revision_id=source_sha
        )
        if (
            child.status != ExtractionRunStatus.REVIEWABLE
            or set(child.lineage) != set(lineage)
            or set(raw_disposition) != {
                "version", "state", "basis_sha256", "review_decision_ref",
                "reviewer_id", "decided_at", "from_revision",
            }
            or type(raw_disposition.get("from_revision")) is not int
            or raw_disposition["from_revision"] != child.revision - 1
            or assessment.disposition is None
            or assessment.disposition.get("state") != raw_disposition["state"]
            or assessment.basis_sha256 != basis.digest()
        ):
            raise _reject("derived run semantic decision conflicts with exact basis", status_code=409)
        semantic_state = raw_disposition["state"]
    elif child.lineage != lineage:
        raise _reject("derived run identity conflicts with existing run", status_code=409)
    if (
        identity_lineage != expected_identity_lineage
        or any(child.lineage.get(key) != value for key, value in world_lineage.items())
        or child.components != components
        or child.source_artifact_id != parent.source_artifact_id
        or child.source_domain != "recap"
        or child.profile_id != parent.profile_id
        or child.campaign_id != parent.campaign_id
        or child.session_id != parent.session_id
    ):
        raise _reject("derived run identity conflicts with existing run", status_code=409)
    # The immutable payload owner handles exact replay/restoration, never a file.
    from application_state.ingest.components import persist_component_payload

    for kind, payload_bytes in (("candidate_graph", child_bytes),
                       ("source_span_index", data.span_bytes)):
        persist_component_payload(run_id=child_id, expected_revision=child.revision,
                                  kind=kind, payload=payload_bytes)
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
        raise _reject("derived recap child could not be sealed", status_code=409)
    load_reviewable_extraction_data(repo, child_id)
    return RecapEvidenceCorrectionResponse(
        run_id=child_id,
        parent_run_id=parent.run_id,
        parent_candidate_sha256=parent_sha,
        candidate_sha256=child_sha,
        correction_digest=correction_digest,
        semantic_state=semantic_state,
        semantic_basis_sha256=basis.digest(),
    )

"""Production boundary from immutable candidate graph to governed publication.

Candidate integrity and admission eligibility are intentionally separate.  The
complete input is digested before qualification.  A derived eligibility view
may omit unsupported items only after every omission has an explicit sealed
disposition; the caller's candidate is never changed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any, TypeVar

from apps.live_control_server.models.candidate_graph_admission import (
    CandidateAdmissionBinding,
    CandidateAdmissionDisposition,
    CandidateAdmissionIntegrityError,
    CandidateAdmissionNotConfirmableError,
    CandidateIntegrityDiagnostic,
)
from graph_memory.candidate_document_integrity import (
    classify_candidate_document_integrity,
)
from graph_memory.candidate_graph_preview import NODE_TYPES
from graph_memory.extract_promote_ops import (
    ExtractPromotePrepareResult,
    prepare_extract_promote,
)
from graph_memory.candidate_graph_to_contribution import verify_source_revision
from graph_memory.candidate_graph_to_contribution import kernel_kind_for_node_type
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET,
    edge_endpoint_kind_admission_reason,
)
from graph_memory.extract_promote_proposal import (
    bind_candidate_admission_to_proposal,
    seal_promote_proposal,
    verify_promote_proposal,
)
from apps.live_control_server.models.world_graph_mutation_context import (
    mutation_context_from_world_root,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    AdmittedSourceIdentity,
    WorldGraphSourceAdmissionError,
    WorldGraphSourceAdmissionRequest,
)

_T = TypeVar("_T")
_SOURCE_ADMISSION_EFFECT_KEY = "source_admission"


def canonical_candidate_digest(candidate_graph: Mapping[str, Any]) -> str:
    """Hash the complete semantic candidate before any qualification."""
    encoded = json.dumps(
        candidate_graph,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_candidate_document_integrity(candidate_graph: Mapping[str, Any]):
    """Return the exact typed preview while treating unsupported kinds as eligibility."""
    digest = canonical_candidate_digest(candidate_graph)
    classification = classify_candidate_document_integrity(candidate_graph)
    if classification.parse_error:
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code="typed_parse_failed",
                    message=classification.parse_error,
                )
            ],
            candidate_digest=digest,
        )
    if classification.integrity_issues:
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code=issue.code,
                    object_id=issue.object_id,
                    field=issue.field,
                    message=issue.message,
                )
                for issue in classification.integrity_issues
            ],
            candidate_digest=digest,
        )
    assert classification.preview is not None
    return classification.preview


def _integrity_and_eligibility(
    candidate_graph: Mapping[str, Any],
) -> tuple[dict[str, Any], list[CandidateAdmissionDisposition], str]:
    digest = canonical_candidate_digest(candidate_graph)
    raw = copy.deepcopy(dict(candidate_graph))
    validate_candidate_document_integrity(raw)

    unsupported_ids = {
        str(node.get("node_id") or "")
        for node in raw.get("nodes", [])
        if isinstance(node, Mapping)
        and (
            str(node.get("node_type") or "") not in NODE_TYPES
            or kernel_kind_for_node_type(str(node.get("node_type") or ""))
            not in CURRENT_V5_TARGET.buddy_to_dm_kind
        )
    }
    dispositions = [
        CandidateAdmissionDisposition(
            item_id=str(node.get("node_id") or ""),
            item_kind="node",
            outcome="rejected",
            reason="unsupported_node_type",
        )
        for node in raw.get("nodes", [])
        if isinstance(node, Mapping)
        and str(node.get("node_id") or "") in unsupported_ids
    ]

    buddy_kind_by_node_id = {
        str(node.get("node_id") or ""): kernel_kind_for_node_type(
            str(node.get("node_type") or "")
        )
        for node in raw.get("nodes", [])
        if isinstance(node, Mapping)
        and str(node.get("node_id") or "") not in unsupported_ids
    }
    vocabulary = CURRENT_V5_TARGET.world_object_loader()

    admitted_edges: list[Any] = []
    not_admitted_ids = set(unsupported_ids)
    for edge in raw.get("edges", []):
        if not isinstance(edge, Mapping):
            admitted_edges.append(edge)
            continue
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        blocked = [
            endpoint
            for endpoint in (from_id, to_id)
            if endpoint in unsupported_ids
        ]
        predicate = str(edge.get("relationship_type") or "").strip()
        if blocked:
            edge_id = str(edge.get("edge_id") or "")
            not_admitted_ids.add(edge_id)
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=edge_id,
                    item_kind="edge",
                    outcome="rejected",
                    reason="endpoint_not_admitted",
                    depends_on=blocked,
                )
            )
            continue
        endpoint_reason = edge_endpoint_kind_admission_reason(
            buddy_predicate=predicate,
            from_buddy_kind=buddy_kind_by_node_id.get(from_id, ""),
            to_buddy_kind=buddy_kind_by_node_id.get(to_id, ""),
            vocabulary=vocabulary,
        )
        if endpoint_reason is not None:
            edge_id = str(edge.get("edge_id") or "")
            not_admitted_ids.add(edge_id)
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=edge_id,
                    item_kind="edge",
                    outcome="rejected",
                    reason=endpoint_reason,
                )
            )
        else:
            admitted_edges.append(edge)

    # This is an eligibility projection, not repaired candidate authority: the
    # complete original remains bound by digest and every excluded item receives
    # a sealed disposition.
    projected = copy.deepcopy(raw)
    projected["nodes"] = [
        node
        for node in raw.get("nodes", [])
        if not isinstance(node, Mapping)
        or str(node.get("node_id") or "") not in unsupported_ids
    ]
    projected["edges"] = admitted_edges
    admitted_beats: list[Any] = []
    for beat in raw.get("beats", []):
        if not isinstance(beat, Mapping):
            admitted_beats.append(beat)
            continue
        blocked = sorted(
            (
                set(map(str, beat.get("involved_node_ids", [])))
                | set(map(str, beat.get("unresolved_thread_node_ids", [])))
            )
            & unsupported_ids
        )
        if blocked:
            beat_id = str(beat.get("beat_id") or "")
            not_admitted_ids.add(beat_id)
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=beat_id,
                    item_kind="beat",
                    outcome="rejected",
                    reason="dependency_not_admitted",
                    depends_on=blocked,
                )
            )
        else:
            admitted_beats.append(beat)
    projected["beats"] = admitted_beats
    retained_targets = {
        str(node.get("node_id") or "")
        for node in projected.get("nodes", [])
        if isinstance(node, Mapping)
    } | {
        str(edge.get("edge_id") or "")
        for edge in projected.get("edges", [])
        if isinstance(edge, Mapping)
    } | {
        str(beat.get("beat_id") or "")
        for beat in projected.get("beats", [])
        if isinstance(beat, Mapping)
    }
    admitted_writes: list[Any] = []
    for write in raw.get("proposed_writes", []):
        if not isinstance(write, Mapping):
            admitted_writes.append(write)
            continue
        target_id = str(write.get("target_id") or "")
        if target_id not in retained_targets or target_id in not_admitted_ids:
            dispositions.append(
                CandidateAdmissionDisposition(
                    item_id=str(write.get("write_id") or ""),
                    item_kind="proposed_write",
                    outcome="rejected",
                    reason="target_not_admitted",
                    depends_on=[target_id] if target_id else [],
                )
            )
        else:
            admitted_writes.append(write)
    projected["proposed_writes"] = admitted_writes
    return projected, dispositions, digest


_RECAP_SOURCE_DOMAIN_KEYS = frozenset({"recap", "session_recap"})


def _scope_check_recap_source_artifact(
    artifact: Any,
    *,
    world_id: str,
    campaign_id: str,
) -> None:
    art_campaign = str(getattr(artifact, "campaign_id", "") or "").strip()
    if art_campaign and campaign_id and art_campaign != campaign_id:
        raise CandidateAdmissionNotConfirmableError(
            "source artifact belongs to a different campaign"
        )
    art_world = str(getattr(artifact, "world_id", "") or "").strip()
    if art_world and world_id and art_world != world_id:
        raise CandidateAdmissionNotConfirmableError(
            "source artifact belongs to a different world"
        )
    domain = str(getattr(artifact, "source_domain", "") or "").strip()
    if domain not in _RECAP_SOURCE_DOMAIN_KEYS:
        raise CandidateAdmissionNotConfirmableError(
            "governed recap admission requires a recap source artifact"
        )
    if not art_campaign or not str(getattr(artifact, "session_id", "") or "").strip():
        raise CandidateAdmissionNotConfirmableError(
            "recap source artifact requires campaign_id and session_id"
        )


def _require_recap_source_artifact(source_artifact: Any) -> Any:
    """Reject non-recap domains. Recap key canonicalization lives on the adapter."""
    if source_artifact is None:
        raise CandidateAdmissionNotConfirmableError(
            "confirmable recap admission requires the canonical source artifact"
        )
    domain = str(getattr(source_artifact, "source_domain", "") or "").strip()
    if domain not in _RECAP_SOURCE_DOMAIN_KEYS:
        raise CandidateAdmissionNotConfirmableError(
            "governed recap admission requires a recap source artifact"
        )
    return source_artifact


def _source_admission_authority(source_admission: Any | None) -> Any:
    if source_admission is not None:
        return source_admission
    from apps.live_control_server.ports.world_graph_source_admission_access import (
        get_world_graph_source_admission_authority,
    )

    return get_world_graph_source_admission_authority()


def _raise_source_admission(
    exc: WorldGraphSourceAdmissionError,
    *,
    candidate_digest: str,
) -> None:
    if exc.code == "source_identity_conflict":
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code="source_identity_conflict",
                    field="source_revision_id",
                    message=str(exc),
                )
            ],
            candidate_digest=candidate_digest,
        ) from exc
    raise CandidateAdmissionNotConfirmableError(str(exc)) from exc


def _admit_confirmable_recap_source(
    *,
    world_id: str,
    campaign_id: str,
    source_uri: str,
    verified_revision_id: str,
    source_artifact_id: str,
    source_artifact: Any | None,
    source_admission: Any | None,
    candidate_digest: str,
) -> AdmittedSourceIdentity:
    if not source_artifact_id or not verified_revision_id or not source_uri:
        raise CandidateAdmissionNotConfirmableError(
            "confirmable recap admission requires source artifact, revision, and URI"
        )
    artifact = _require_recap_source_artifact(source_artifact)
    _scope_check_recap_source_artifact(
        artifact, world_id=world_id, campaign_id=campaign_id
    )
    request = WorldGraphSourceAdmissionRequest(
        world_id=world_id,
        campaign_id=campaign_id,
        source_artifact=artifact,
        source_revision_token=verified_revision_id,
        source_uri=source_uri,
    )
    try:
        return _source_admission_authority(source_admission).prove_or_admit(request)
    except WorldGraphSourceAdmissionError as exc:
        _raise_source_admission(exc, candidate_digest=candidate_digest)
        raise


def _seal_source_admission(
    package: Mapping[str, Any],
    admitted: AdmittedSourceIdentity,
) -> dict[str, Any]:
    from graph_memory.extract_promote_proposal import compute_proposal_digest

    sealed = dict(package)
    effect = dict(sealed.get("effect") or {})
    effect[_SOURCE_ADMISSION_EFFECT_KEY] = {
        "source_artifact_id": admitted.source_artifact_id,
        "source_revision_id": admitted.source_revision_id,
        "buddy_source_revision_id": admitted.buddy_source_revision_id,
        "content_sha256": admitted.content_sha256,
    }
    sealed["effect"] = effect
    sealed["proposal_digest"] = compute_proposal_digest(effect)
    return sealed


def prepare_candidate_graph_admission(
    *, candidate_graph: Mapping[str, Any], **prepare_kwargs: Any
) -> ExtractPromotePrepareResult:
    """Prepare and seal one exact candidate against one pinned parent."""
    source_admission = prepare_kwargs.pop("source_admission", None)
    source_artifact = prepare_kwargs.pop("source_artifact", None)
    projected, dispositions, digest = _integrity_and_eligibility(candidate_graph)
    has_structurally_admissible_nodes = bool(projected.get("nodes"))
    has_standing_context = prepare_kwargs.get("registry_context_graph") is not None
    if has_structurally_admissible_nodes or has_standing_context:
        result = prepare_extract_promote(candidate_graph=projected, **prepare_kwargs)
    else:
        mutation_context = prepare_kwargs.get("mutation_context")
        world_id = str(prepare_kwargs.get("world_id") or "eldyrwild")
        if mutation_context is None:
            world_root = prepare_kwargs.get("world_root")
            if world_root is None:
                raise CandidateAdmissionNotConfirmableError(
                    "mutation_context or world_root is required to seal admission"
                )
            mutation_context = mutation_context_from_world_root(world_root, world_id)
        source_uri = str(prepare_kwargs.get("source_uri") or "")
        source_revision_id = verify_source_revision(
            source_uri=source_uri,
            source_revision_id=str(prepare_kwargs.get("source_revision_id") or ""),
            repo_root=prepare_kwargs.get("repo_root"),
            disclose_computed_digest=bool(
                prepare_kwargs.get("disclose_source_digest", True)
            ),
        )
        source_artifact_id = str(
            prepare_kwargs.get("source_artifact_id")
            or next(iter(candidate_graph.get("source_artifact_ids") or []), "")
        ).strip()
        if not source_artifact_id:
            raise CandidateAdmissionNotConfirmableError(
                "source_artifact_id is required to seal admission"
            )
        package = seal_promote_proposal(
            world_id=world_id,
            parent_revision_id=mutation_context.revision_id,
            source_revision_id=source_revision_id,
            source_artifact_id=source_artifact_id,
            verified_source_uri=source_uri,
            candidate_preview_id=str(candidate_graph.get("preview_id") or ""),
            candidate_schema=str(candidate_graph.get("schema") or ""),
            candidate_version=str(candidate_graph.get("version") or ""),
            contribution_meta={
                "source_kind": "source_extraction",
                "source_artifact_id": source_artifact_id,
                "source_revision_id": source_revision_id,
                "extraction_profile": str(
                    prepare_kwargs.get("extraction_profile") or "current_default"
                ),
                "campaign_scope": prepare_kwargs.get("campaign_scope"),
                "authored_by": "extract-identity-gate",
            },
            accepted_proposals=[],
            rejected_assertions=[],
            unresolved_mentions=[],
            node_id_map={},
            identity_outcome_snapshot={},
            prepared_by=str(prepare_kwargs.get("prepared_by") or ""),
            diagnostics=["candidate_admission:no_admissible_assertions"],
            world_root=(
                str(prepare_kwargs["world_root"])
                if prepare_kwargs.get("world_root") is not None
                else None
            ),
            candidate_graph_path=prepare_kwargs.get("candidate_graph_path"),
        )
        result = ExtractPromotePrepareResult(
            review_package=package,
            proposal_id=str(package["proposal_id"]),
            proposal_digest=str(package["proposal_digest"]),
            parent_revision_id=mutation_context.revision_id,
            world_id=world_id,
            accepted_proposals_count=0,
            unresolved_mentions_count=0,
            rejected_assertions_count=0,
            confirmable=False,
            review_items=[],
            review_summary={
                "new_object_count": 0,
                "connect_existing_count": 0,
                "relationship_count": 0,
                "unresolved_mention_count": 0,
                "rejected_assertion_count": len(dispositions),
            },
        )
    effect = dict(result.review_package.get("effect") or {})
    confirmable = bool(effect.get("accepted_proposals"))
    result = replace(result, confirmable=confirmable)
    binding = CandidateAdmissionBinding(
        candidate_digest=digest,
        candidate_locator=prepare_kwargs.get("candidate_graph_path"),
        candidate_preview_id=str(candidate_graph.get("preview_id") or ""),
        source_artifact_id=str(effect.get("source_artifact_id") or ""),
        source_revision_id=str(effect.get("source_revision_id") or ""),
        world_id=result.world_id,
        parent_revision_id=result.parent_revision_id,
        confirmable=confirmable,
        dispositions=dispositions,
        exact_candidate_counts={
            key: len(candidate_graph.get(key) or [])
            for key in ("nodes", "edges", "beats", "proposed_writes")
        },
    )
    package = bind_candidate_admission_to_proposal(
        result.review_package, binding.as_effect_payload()
    )
    if confirmable:
        admitted = _admit_confirmable_recap_source(
            world_id=result.world_id,
            campaign_id=str(
                prepare_kwargs.get("campaign_scope")
                or candidate_graph.get("campaign_id")
                or ""
            ).strip(),
            source_uri=str(prepare_kwargs.get("source_uri") or "").strip(),
            verified_revision_id=str(effect.get("source_revision_id") or "").strip(),
            source_artifact_id=str(
                effect.get("source_artifact_id")
                or prepare_kwargs.get("source_artifact_id")
                or ""
            ).strip(),
            source_artifact=source_artifact,
            source_admission=source_admission,
            candidate_digest=digest,
        )
        package = _seal_source_admission(package, admitted)
    return replace(
        result,
        review_package=package,
        proposal_digest=str(package["proposal_digest"]),
        rejected_assertions_count=result.rejected_assertions_count
        + sum(item.outcome == "rejected" for item in dispositions),
    )


def verify_candidate_graph_admission_confirmation(
    *, review_package: Mapping[str, Any], candidate_graph: Mapping[str, Any]
) -> CandidateAdmissionBinding:
    """Re-prove exact candidate binding before governed confirmation."""
    effect = dict(review_package.get("effect") or {})
    raw_binding = effect.get("candidate_admission")
    if not isinstance(raw_binding, Mapping):
        raise CandidateAdmissionIntegrityError(
            [CandidateIntegrityDiagnostic(code="admission_binding_missing", message="sealed proposal has no candidate admission binding")],
            candidate_digest=canonical_candidate_digest(candidate_graph),
        )
    # Prove the ordinary proposal seal before trusting even a nonconfirmable
    # admission flag from its effect.
    verify_promote_proposal(review_package, confirming_principal="candidate-admission")
    binding = CandidateAdmissionBinding.model_validate(raw_binding)
    if not binding.confirmable:
        raise CandidateAdmissionNotConfirmableError(
            "candidate admission is not confirmable: no admissible assertions"
        )
    source_admission = effect.get(_SOURCE_ADMISSION_EFFECT_KEY)
    if not isinstance(source_admission, Mapping) or not str(
        source_admission.get("source_artifact_id") or ""
    ).strip() or not str(source_admission.get("source_revision_id") or "").strip():
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code="source_admission_missing",
                    message="confirmable proposal is missing sealed source admission",
                )
            ],
            candidate_digest=canonical_candidate_digest(candidate_graph),
        )
    sealed_pairs = {
        "world_id": str(effect.get("world_id") or ""),
        "parent_revision_id": str(effect.get("parent_revision_id") or ""),
        "source_artifact_id": str(effect.get("source_artifact_id") or ""),
        "source_revision_id": str(effect.get("source_revision_id") or ""),
        "candidate_preview_id": str(effect.get("candidate_preview_id") or ""),
    }
    drifted = [
        field
        for field, sealed in sealed_pairs.items()
        if str(getattr(binding, field)) != sealed
    ]
    if drifted:
        raise CandidateAdmissionIntegrityError(
            [
                CandidateIntegrityDiagnostic(
                    code="admission_binding_mismatch",
                    field=field,
                    message=f"candidate admission {field} disagrees with sealed effect",
                )
                for field in drifted
            ],
            candidate_digest=canonical_candidate_digest(candidate_graph),
        )
    actual = canonical_candidate_digest(candidate_graph)
    if actual != binding.candidate_digest:
        raise CandidateAdmissionIntegrityError(
            [CandidateIntegrityDiagnostic(code="candidate_digest_mismatch", message="candidate changed after prepare")],
            candidate_digest=actual,
        )
    return binding


def _reprove_sealed_recap_source(
    *,
    review_package: Mapping[str, Any],
    source_admission: Any | None,
    candidate_digest: str,
) -> None:
    """Snapshot-prove the sealed prepare pair before governed confirm.

    This proves the already-admitted artifact/revision and its fingerprint, not
    a newly proposed identity. ``source_identity_conflict`` during prepare must
    not reach here via a ``prove()`` fallback. Uninjected callers keep the
    existing verify-only confirm path; product native confirms inject an
    authority, and ``world_graph_writes`` re-proofs independently.
    """
    if source_admission is None:
        return
    effect = dict(review_package.get("effect") or {})
    sealed = effect.get(_SOURCE_ADMISSION_EFFECT_KEY)
    if not isinstance(sealed, Mapping):
        return
    try:
        admitted = _source_admission_authority(source_admission).prove(
            world_id=str(effect.get("world_id") or ""),
            source_artifact_id=str(sealed.get("source_artifact_id") or ""),
            source_revision_id=str(sealed.get("source_revision_id") or ""),
            source_revision_token=str(sealed.get("buddy_source_revision_id") or "")
            or None,
        )
    except WorldGraphSourceAdmissionError as exc:
        _raise_source_admission(exc, candidate_digest=candidate_digest)
        raise
    except Exception as exc:
        from dungeonmind.domain.errors import PersistenceIntegrityError

        if not isinstance(exc, PersistenceIntegrityError):
            raise
        _raise_source_admission(
            WorldGraphSourceAdmissionError(
                str(exc),
                code="source_identity_conflict",
            ),
            candidate_digest=candidate_digest,
        )
        raise
    sealed_sha = str(sealed.get("content_sha256") or "").strip()
    if sealed_sha and admitted.content_sha256 != sealed_sha:
        _raise_source_admission(
            WorldGraphSourceAdmissionError(
                "Sealed recap source fingerprint drifted from the admitted pair.",
                code="source_identity_conflict",
            ),
            candidate_digest=candidate_digest,
        )


def confirm_candidate_graph_admission(
    *,
    review_package: Mapping[str, Any],
    candidate_graph: Mapping[str, Any],
    governed_confirm: Callable[[], _T],
    source_admission: Any | None = None,
) -> _T:
    """Verify admission, re-prove the sealed source pair, then write once."""
    verify_candidate_graph_admission_confirmation(
        review_package=review_package, candidate_graph=candidate_graph
    )
    _reprove_sealed_recap_source(
        review_package=review_package,
        source_admission=source_admission,
        candidate_digest=canonical_candidate_digest(candidate_graph),
    )
    return governed_confirm()

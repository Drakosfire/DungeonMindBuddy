"""Receipt-only ordinary extract recovery; package digests are NOT signatures.

Pure integrity/recipe groundwork. Terminal correspondence and reader composition
must be proved before this module is wired into a route.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from apps.live_control_server.services.extract_promote import ExtractPromoteError


def _unsupported(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Historical extract recipe is unsupported; retain the original request: {reason}.",
        code="publication_history_unsupported", status_code=409,
    )


def _invalid(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Original extract packet failed integrity verification: {reason}.",
        code="plan_verification_failed", status_code=409,
    )


def validate_original_packet(package: Mapping[str, Any], selection: Sequence[str]) -> dict[str, Any]:
    """Prove carried consistency, never historical authenticity or permission.

    A caller can recompute this unkeyed digest. Only complete correspondence with
    the verified original terminal review can establish the requested history.
    This routine performs no authority, filesystem, source or database reads.
    """
    from graph_memory.extract_promote_proposal import (
        PromoteProposalError, verify_promote_proposal, verify_source_local_identity_basis,
    )
    from apps.live_control_server.models.extract_promote import SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.models.candidate_graph_admission import CandidateAdmissionBinding
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _derive_confirm_operation_id, _require_sealed_identity_ledger, WorldGraphWriteError,
    )
    from apps.live_control_server.services.extract_promote import _PUBLICATION_TARGET_SCHEMA, _PUBLICATION_TARGET_KEY

    if not isinstance(package, Mapping):
        raise _invalid("package shape")
    if (not selection or any(not isinstance(item, str) or not item or item.strip() != item for item in selection)
            or len(set(selection)) != len(selection)):
        raise _invalid("explicit nonempty unique selection")
    frozen = deepcopy(dict(package))
    try:
        verified = verify_promote_proposal(frozen, confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
                                           selected_assertion_ids=list(selection))
    except (PromoteProposalError, TypeError, ValueError, KeyError) as exc:
        raise _invalid("proposal/selection consistency") from exc
    effect = verified["effect"]
    slices = verified["contribution_slices"]
    if len(slices) != 1:
        raise _unsupported("multiple contribution slices")
    part = slices[0]
    meta = part.get("contribution_meta") or {}
    if meta.get("source_kind") != "source_extraction":
        raise _unsupported("non-extraction source")
    for field in ("source_proven_endpoint_basis", "recap_source_observation_basis"):
        if effect.get(field) is not None:
            raise _unsupported(field)
    target = effect.get(_PUBLICATION_TARGET_KEY)
    if (not isinstance(target, Mapping) or target.get("schema") != _PUBLICATION_TARGET_SCHEMA
            or target.get("native_world_id") != verified["world_id"]
            or not isinstance(target.get("managed_world_id"), str) or not target["managed_world_id"].strip()
            or type(target.get("binding_version")) is not int or target["binding_version"] < 1):
        raise _invalid("managed/native target identity")
    source = effect.get("source_admission")
    if not isinstance(source, Mapping):
        raise _unsupported("missing original source admission")
    for field in ("source_artifact_id", "source_revision_id", "buddy_source_revision_id", "content_sha256"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise _unsupported("incomplete original source admission")
    pair = (source["source_artifact_id"], source["buddy_source_revision_id"])
    if pair != (verified["source_artifact_id"], verified["source_revision_id"]):
        raise _invalid("source admission coordinates")
    try:
        admission = CandidateAdmissionBinding.model_validate(effect.get("candidate_admission"))
        if (not admission.confirmable or admission.world_id != verified["world_id"]
                or admission.parent_revision_id != verified["parent_revision_id"]
                or (admission.source_artifact_id, admission.source_revision_id) != pair
                or admission.candidate_preview_id != verified["candidate_preview_id"]):
            raise ValueError("candidate coordinates")
        ledger = effect.get("identity_ledger")
        if (not isinstance(ledger, Mapping) or not isinstance(ledger.get("decisions"), list)
                or any(not isinstance(item, Mapping) for item in ledger["decisions"])):
            raise ValueError("identity ledger shape")
        _require_sealed_identity_ledger(frozen)
        verify_source_local_identity_basis(effect, require=True)
    except (TypeError, ValueError, KeyError, WorldGraphWriteError) as exc:
        raise _invalid("candidate/source-local/ledger correspondence") from exc
    basis = part.get("identity_basis") or {}
    nodes = basis.get("nodes") or {}
    if any(record.get("classification") != "source_local" for record in nodes.values()):
        raise _unsupported("non-source-local identity")
    for raw in [*(part.get("accepted_proposals") or []), *(part.get("rejected_assertions") or [])]:
        if (raw.get("source_artifact_id"), raw.get("source_revision_id")) != pair:
            raise _unsupported("multiple source pairs")
    return {
        "package": frozen, "verified": verified, "selection": tuple(selection),
        "source_admission": dict(source),
        "operation_id": _derive_confirm_operation_id(world_id=verified["world_id"], package=frozen,
                                                     assertion_ids=tuple(selection)),
    }

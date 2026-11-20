"""Kernel-free Buddy → DungeonMind contribution mapping (CUTOVER D.3A).


Extracted from the historical Eldyrwild adoption producer so mounted first-world
and Graph Review publication can map contributions without importing
``graph_memory.kernel`` / ``world_supergraph`` / ``union_supergraph`` or
``integrations/dungeonmind_kernel/**``.
"""


from __future__ import annotations


import json
from datetime import UTC, datetime
from typing import Any


from dungeonmind.contracts.contribution import (
    AcceptanceState,
    ContributionSourceKind,
    ContributionStatus,
    GraphContributionAssertionCorrection,
    GraphContributionAssertionCorrectionKind,
    GraphContributionAssertionV2,
    GraphContributionV2,
    GraphContributionAssertionV3,
    GraphContributionV3,
)
from dungeonmind.contracts.evidence import EvidenceRef, EvidenceRefV2, EvidenceRole, SourceDomain
from dungeonmind.contracts.identity import IdentityOutcome
from dungeonmind.contracts.vocabulary import (
    ContributionEpistemicKind,
    Visibility,
)
from dungeonmind.domain.canonical import canonical_json, canonical_sha256


class ContributionMappingError(RuntimeError):
    """Fail-closed contribution mapping STOP."""


    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(message: str, code: str) -> ContributionMappingError:
    return ContributionMappingError(message, code=code)


_SOURCE_KIND_MAP = {
    "source_extraction": ContributionSourceKind.EXTRACTION,
    "standing_context": ContributionSourceKind.STANDING_CONTEXT,
    "graph_review_authored_assertion": ContributionSourceKind.GRAPH_REVIEW,
    "identity_decision": ContributionSourceKind.IDENTITY_DECISION,
    "manual_import": ContributionSourceKind.MANUAL_IMPORT,
}
_SOURCE_DOMAIN_MAP = {
    "recap": SourceDomain.SESSION_RECAP,
    "session_recap": SourceDomain.SESSION_RECAP,
    "worldbuilding": SourceDomain.WORLDBUILDING,
    "rulebook": SourceDomain.RULEBOOK,
    "prep": SourceDomain.PREP,
    "manual": SourceDomain.MANUAL,
}
_EVIDENCE_ROLE_MAP = {
    "support": EvidenceRole.SUPPORT,
    "contribution_support": EvidenceRole.SUPPORT,
    "contradiction": EvidenceRole.CONTRADICTION,
    "context": EvidenceRole.CONTEXT,
}
_CONTRIBUTION_EPISTEMIC_DIRECT = {
    "asserted": ContributionEpistemicKind.ASSERTED,
    "inferred": ContributionEpistemicKind.INFERRED,
    "speculative": ContributionEpistemicKind.SPECULATIVE,
    "source_derived_candidate": ContributionEpistemicKind.SOURCE_DERIVED_CANDIDATE,
}


CONTRIBUTION_EVIDENCE_ID_MARK = ":dmv1:"
GRAPH_REVIEW_EVIDENCE_ID_MARK = ":dmv3:"
CONTRIBUTION_EVIDENCE_V1_BINDING_FIELDS = (
    "schema_version",
    "source_artifact_id",
    "source_revision_id",
    "source_domain",
    "evidence_role",
    "can_open_source",
    "can_highlight_span",
    "locator",
    "uri",
)


def contribution_evidence_v1_binding_payload(
    ref: EvidenceRef | dict[str, Any],
) -> dict[str, Any]:
    """Immutable dm_evidence_ref_v1 fields excluding evidence_ref_id."""
    if isinstance(ref, EvidenceRef):
        payload = ref.model_dump(mode="json")
    else:
        payload = dict(ref)
    return {field: payload.get(field) for field in CONTRIBUTION_EVIDENCE_V1_BINDING_FIELDS}


def exported_contribution_evidence_ref_id(
    raw_buddy_evidence_ref_id: str,
    binding: EvidenceRef | dict[str, Any],
) -> str:
    digest = canonical_sha256(contribution_evidence_v1_binding_payload(binding))
    return f"{raw_buddy_evidence_ref_id}{CONTRIBUTION_EVIDENCE_ID_MARK}{digest}"


def raw_buddy_evidence_ref_id(exported_evidence_ref_id: str) -> str:
    marker = CONTRIBUTION_EVIDENCE_ID_MARK
    if marker not in exported_evidence_ref_id:
        raise _fail(
            f"exported evidence_ref_id is missing {marker}: {exported_evidence_ref_id}",
            "contribution_evidence_id_unmarked",
        )
    raw, digest = exported_evidence_ref_id.rsplit(marker, 1)
    if not raw or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise _fail(
            f"exported evidence_ref_id is not raw:dmv1:<sha256>: {exported_evidence_ref_id}",
            "contribution_evidence_id_malformed",
        )
    return raw


def _map_source_domain(raw: str) -> SourceDomain | None:
    return _SOURCE_DOMAIN_MAP.get(raw)


def _map_evidence_role(raw: str) -> EvidenceRole:
    mapped = _EVIDENCE_ROLE_MAP.get(raw)
    if mapped is None:
        raise _fail(f"unsupported Buddy evidence role {raw!r}", "evidence_role_unmapped")
    return mapped


def _parse_aware(value: str | None, *, field_name: str) -> datetime:
    if not value or not str(value).strip():
        raise _fail(f"{field_name} is missing a timestamp", "timestamp_missing")
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _map_source_kind(raw: str | None) -> ContributionSourceKind:
    text = str(raw or "").strip()
    try:
        return ContributionSourceKind(text)
    except Exception:
        return ContributionSourceKind.OTHER


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _require_source_pair(
    artifact_id: str | None,
    revision_id: str | None,
    *,
    field: str,
) -> tuple[str, str]:
    if not artifact_id or not revision_id:
        raise _fail(f"{field} is missing source identity", "source_identity_missing")
    return artifact_id, revision_id


def _map_acceptance(raw: str) -> AcceptanceState:
    if raw == "accepted":
        return AcceptanceState.ACCEPTED
    if raw == "rejected":
        return AcceptanceState.REJECTED
    if raw == "candidate":
        return AcceptanceState.CANDIDATE
    raise _fail(f"unsupported acceptance state {raw!r}", "acceptance_unmapped")


def _map_visibility(raw: str | None) -> Visibility:
    if raw in (None, "", "gm"):
        return Visibility.GM
    if raw == "player":
        return Visibility.PLAYER
    raise _fail(f"unsupported visibility {raw!r}", "visibility_unmapped")


def _map_identity_outcome(raw: str | None) -> IdentityOutcome | None:
    if raw is None:
        return None
    try:
        return IdentityOutcome(raw)
    except ValueError as exc:
        raise _fail(f"unsupported identity outcome {raw!r}", "identity_outcome_unmapped") from exc


def _map_contribution_evidence_ref(
    store: Any,
    evidence_ref_id: str,
    *,
    fallback_source_artifact_id: str | None,
    source_revision_id: str | None,
) -> EvidenceRef:
    evidence = store.evidence.get(evidence_ref_id)
    if evidence is not None:
        domain_key = str(evidence.source_domain)
        domain = _map_source_domain(domain_key) or SourceDomain.OTHER
        draft = EvidenceRef(
            evidence_ref_id=evidence.evidence_ref_id,
            source_artifact_id=evidence.source_artifact_id,
            source_revision_id=source_revision_id,
            source_domain=domain,
            evidence_role=_map_evidence_role(str(evidence.evidence_role)),
            can_open_source=bool(evidence.can_open_source),
            can_highlight_span=bool(evidence.can_highlight_span),
            locator=evidence.locator,
            uri=evidence.uri,
        )
        return draft.model_copy(
            update={
                "evidence_ref_id": exported_contribution_evidence_ref_id(
                    evidence_ref_id,
                    draft,
                )
            }
        )
    if not fallback_source_artifact_id:
        raise _fail(f"contribution evidence missing: {evidence_ref_id}", "evidence_missing")
    draft = EvidenceRef(
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=fallback_source_artifact_id,
        source_revision_id=source_revision_id,
        source_domain=SourceDomain.OTHER,
        evidence_role=EvidenceRole.SUPPORT,
        can_open_source=False,
        can_highlight_span=False,
        locator=None,
        uri=None,
    )
    return draft.model_copy(
        update={
            "evidence_ref_id": exported_contribution_evidence_ref_id(evidence_ref_id, draft)
        }
    )


def _map_contribution_epistemic(raw: str | None) -> tuple[ContributionEpistemicKind, str | None]:
    if raw in _CONTRIBUTION_EPISTEMIC_DIRECT:
        return _CONTRIBUTION_EPISTEMIC_DIRECT[raw], None
    if raw == "fact":
        return ContributionEpistemicKind.ASSERTED, "fact"
    if raw is None:
        return ContributionEpistemicKind.ASSERTED, "null"
    raise _fail(f"unsupported Buddy epistemic kind {raw!r}", "epistemic_unmapped")


def _map_contributions(
    store: Any,
    contributions: list[Any],
    pair_to_dm: dict[tuple[str, str], str],
) -> list[GraphContributionV2]:
    mapped: list[GraphContributionV2] = []
    for contribution in contributions:
        assertions: list[GraphContributionAssertionV2] = []
        epistemic_history: dict[str, str | None] = {}
        contribution_pair = _require_source_pair(
            contribution.source_artifact_id,
            contribution.source_revision_id,
            field=contribution.contribution_id,
        )
        contribution_revision_id = pair_to_dm[contribution_pair]
        for assertion, _partition in (
            *((item, "candidate") for item in contribution.candidate_assertions),
            *((item, "accepted") for item in contribution.accepted_assertions),
            *((item, "rejected") for item in contribution.rejected_assertions),
        ):
            epistemic, original = _map_contribution_epistemic(assertion.epistemic_kind)
            if original is not None:
                epistemic_history[assertion.assertion_id] = None if original == "null" else original
            assertion_pair = _require_source_pair(
                assertion.source_artifact_id,
                assertion.source_revision_id,
                field=assertion.assertion_id,
            )
            assertion_revision_id = pair_to_dm[assertion_pair]
            assertions.append(
                GraphContributionAssertionV2(
                    assertion_id=assertion.assertion_id,
                    assertion_kind=str(assertion.assertion_kind),
                    subject_object_id=assertion.subject_node_id,
                    object_object_id=assertion.target_node_id,
                    predicate=assertion.predicate,
                    label=assertion.label,
                    value=canonical_json(assertion.value) if assertion.value else None,
                    evidence_refs=[
                        _map_contribution_evidence_ref(
                            store,
                            evidence_id,
                            fallback_source_artifact_id=assertion.source_artifact_id,
                            source_revision_id=assertion_revision_id,
                        )
                        for evidence_id in assertion.evidence_ref_ids
                    ],
                    source_artifact_id=assertion.source_artifact_id,
                    source_revision_id=assertion_revision_id,
                    campaign_scope=assertion.campaign_scope,
                    temporal_scope=assertion.temporal_scope,
                    visibility=_map_visibility(assertion.visibility),
                    epistemic_kind=epistemic,
                    acceptance_state=_map_acceptance(assertion.acceptance_state),
                    identity_resolution_outcome=_map_identity_outcome(
                        assertion.identity_resolution_outcome
                    ),
                )
            )
        corrections = [
            GraphContributionAssertionCorrection(
                correction_kind=GraphContributionAssertionCorrectionKind(item.correction_kind),
                target_contribution_id=item.target_contribution_id,
                target_assertion_id=item.target_assertion_id,
                replacement_assertion_id=item.replacement_assertion_id,
            )
            for item in contribution.assertion_corrections
        ]
        diagnostics: dict[str, Any] = {}
        if contribution.diagnostics:
            diagnostics["buddy_diagnostics"] = list(contribution.diagnostics)
        if epistemic_history:
            diagnostics["buddy_assertion_epistemic"] = epistemic_history
        mapped.append(
            GraphContributionV2(
                contribution_id=contribution.contribution_id,
                world_id=contribution.world_id,
                source_kind=_SOURCE_KIND_MAP[contribution.source_kind],
                source_artifact_id=contribution.source_artifact_id,
                source_revision_id=contribution_revision_id,
                extraction_profile=contribution.extraction_profile,
                produced_at=_parse_aware(contribution.produced_at, field_name="produced_at"),
                campaign_scope=contribution.campaign_scope,
                status=ContributionStatus(contribution.status),
                supersedes_contribution_id=contribution.supersedes_contribution_id,
                assertions=assertions,
                unresolved_mentions=[
                    _canonical_json(mention.model_dump(mode="json"))
                    for mention in contribution.unresolved_mentions
                ],
                identity_decision_ids=list(contribution.identity_decision_ids),
                authored_by=contribution.authored_by,
                diagnostics=diagnostics,
                assertion_corrections=corrections,
            )
        )
    return mapped


def map_graph_review_contribution_v3(
    store: Any,
    contribution: Any,
    pair_to_dm: dict[tuple[str, str], str],
) -> GraphContributionV3:
    """Map only fresh Graph Review evidence into the governed typed review family."""
    if contribution.source_kind != "graph_review_authored_assertion":
        raise _fail("typed Graph Review mapping requires Graph Review source kind", "source_kind_unmapped")
    mapped = _map_contributions(store, [contribution], pair_to_dm)
    if len(mapped) != 1:
        raise _fail("Graph Review mapping produced no unique contribution", "contribution_unmapped")

    def valid_digest(value: Any) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
        )

    buddy_by_id = {
        assertion.assertion_id: assertion
        for assertion in [
            *contribution.candidate_assertions,
            *contribution.accepted_assertions,
            *contribution.rejected_assertions,
        ]
    }
    typed_assertions: list[GraphContributionAssertionV3] = []
    for assertion in mapped[0].assertions:
        original = buddy_by_id[assertion.assertion_id]
        rows = original.value.get("evidence") if isinstance(original.value, dict) else None
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise _fail("Graph Review assertion lacks one verified source passage", "evidence_span_missing")
        row = rows[0]
        raw_id = str(row.get("evidence_ref_id") or "")
        source_artifact_id = str(row.get("source_artifact_id") or "")
        buddy_revision_id = str(row.get("source_revision_id") or "")
        source_span_ref_id = str(row.get("source_span_ref_id") or "")
        source_domain_key = str(row.get("source_domain") or "")
        domain = _map_source_domain(source_domain_key)
        if (
            list(original.evidence_ref_ids) != [raw_id]
            or source_artifact_id != original.source_artifact_id
            or buddy_revision_id != original.source_revision_id
            or not source_span_ref_id
            or domain not in {SourceDomain.WORLDBUILDING, SourceDomain.SESSION_RECAP}
            or not valid_digest(row.get("source_content_sha256"))
            or not valid_digest(row.get("span_content_sha256"))
            or (
                domain is SourceDomain.WORLDBUILDING
                and not valid_digest(row.get("span_index_sha256"))
            )
            or not str(row.get("visibility_state") or "").strip()
        ):
            raise _fail("Graph Review verified evidence disagrees with its assertion", "evidence_span_mismatch")
        dm_revision_id = pair_to_dm[(source_artifact_id, buddy_revision_id)]
        binding = {
            "source_artifact_id": source_artifact_id,
            "source_revision_id": dm_revision_id,
            "source_domain_key": source_domain_key,
            "source_domain": domain.value,
            "source_span_ref_id": source_span_ref_id,
            "source_content_sha256": row.get("source_content_sha256"),
            "span_content_sha256": row.get("span_content_sha256"),
            "span_index_sha256": row.get("span_index_sha256"),
            "visibility_state": row.get("visibility_state"),
        }
        evidence_id = f"{raw_id}{GRAPH_REVIEW_EVIDENCE_ID_MARK}{canonical_sha256(binding)}"
        typed = EvidenceRefV2(
            evidence_ref_id=evidence_id,
            source_artifact_id=source_artifact_id,
            source_revision_id=dm_revision_id,
            source_domain_key=source_domain_key,
            source_domain=domain,
            evidence_role=EvidenceRole.SUPPORT,
            can_open_source=True,
            can_highlight_span=True,
            session_id=None,
            source_span_ref_id=source_span_ref_id,
            locator=None,
            uri=None,
            source_locator=None,
            line_ref=None,
        )
        typed_assertions.append(GraphContributionAssertionV3.model_validate({
            **assertion.model_dump(mode="json"),
            "evidence_refs": [typed.model_dump(mode="json")],
        }))
    return GraphContributionV3.model_validate({
        **mapped[0].model_dump(mode="json"),
        "schema_version": "dm_graph_contribution_v3",
        "assertions": [assertion.model_dump(mode="json") for assertion in typed_assertions],
    })


def map_worldbuilding_extraction_contribution_v3(
    store: Any,
    contribution: Any,
    pair_to_dm: dict[tuple[str, str], str],
) -> GraphContributionV3:
    """Preserve every explicitly declared worldbuilding span in fresh extraction."""
    if contribution.source_kind != "source_extraction":
        raise _fail("typed extraction requires extraction source kind", "source_kind_unmapped")
    mapped = _map_contributions(store, [contribution], pair_to_dm)[0]
    originals = {
        item.assertion_id: item
        for item in [
            *contribution.candidate_assertions,
            *contribution.accepted_assertions,
            *contribution.rejected_assertions,
        ]
    }
    typed_assertions = []
    for assertion in mapped.assertions:
        original = originals[assertion.assertion_id]
        rows = original.value.get("evidence") if isinstance(original.value, dict) else None
        ids = list(original.evidence_ref_ids)
        if not ids or not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise _fail("extraction lacks explicit source evidence", "evidence_span_missing")
        by_id = {str(row.get("evidence_ref_id") or ""): row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != set(ids) or len(set(ids)) != len(ids):
            raise _fail("extraction evidence closure disagrees", "evidence_span_mismatch")
        refs = []
        for raw_id in ids:
            row = by_id[raw_id]
            record = store.evidence.get(raw_id)
            span = str(row.get("source_span_ref_id") or "").strip()
            pair = (original.source_artifact_id, original.source_revision_id)
            if (
                record is None
                or pair not in pair_to_dm
                or row.get("source_artifact_id") != pair[0]
                or (row.get("source_revision_id") is not None
                    and row["source_revision_id"] != pair[1])
                or (row.get("source_content_sha256") is not None
                    and row["source_content_sha256"] != pair[1].removeprefix("sha256:"))
                or row.get("source_domain") != "worldbuilding"
                or str(record.source_domain) != "worldbuilding"
                or record.source_artifact_id != pair[0]
                or not span
                or record.source_span_ref_id != span
            ):
                raise _fail("extraction source binding disagrees", "evidence_span_mismatch")
            typed = EvidenceRefV2(
                evidence_ref_id=raw_id,
                source_artifact_id=pair[0],
                source_revision_id=pair_to_dm[pair],
                source_domain_key="worldbuilding",
                source_domain=SourceDomain.WORLDBUILDING,
                evidence_role=EvidenceRole.SUPPORT,
                can_open_source=True,
                can_highlight_span=True,
                session_id=None,
                source_span_ref_id=span,
                locator=None,
                uri=None,
                source_locator=None,
                line_ref=None,
            )
            binding = typed.model_dump(mode="json", exclude={"evidence_ref_id"})
            refs.append(typed.model_copy(update={
                "evidence_ref_id": f"{raw_id}:dm-extraction-v3:{canonical_sha256(binding)}",
            }))
        typed_assertions.append(GraphContributionAssertionV3.model_validate({
            **assertion.model_dump(mode="json"),
            "evidence_refs": [ref.model_dump(mode="json") for ref in refs],
        }))
    return GraphContributionV3.model_validate({
        **mapped.model_dump(mode="json"),
        "schema_version": "dm_graph_contribution_v3",
        "assertions": [assertion.model_dump(mode="json") for assertion in typed_assertions],
    })

"""Current initializer producer mappings; no inferred source locators."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dungeonmind.contracts.contribution import GraphContributionV3
from dungeonmind.contracts.evidence import EvidenceRefV2, EvidenceRole, SourceDomain

from .contribution_mapping import (
    _map_contributions,
    map_worldbuilding_extraction_contribution_v3,
)


def map_first_world_typed_contribution(
    contribution: Any,
    *,
    artifacts: list[Any],
    pair_to_dm: dict[tuple[str, str], str],
    party_registry: bool,
) -> GraphContributionV3:
    """Map only explicitly closed, reviewed producer evidence to the current command."""
    source_by_id = {artifact.source_artifact_id: artifact for artifact in artifacts}
    evidence = {}
    assertions = [
        *contribution.accepted_assertions,
        *contribution.rejected_assertions,
        *contribution.candidate_assertions,
    ]
    for assertion in assertions:
        artifact = source_by_id.get(assertion.source_artifact_id)
        pair = (assertion.source_artifact_id, assertion.source_revision_id)
        if artifact is None or pair not in pair_to_dm:
            raise ValueError("first-world assertion source is not command-owned")
        if not assertion.evidence_ref_ids or len(
            set(assertion.evidence_ref_ids)
        ) != len(assertion.evidence_ref_ids):
            raise ValueError(
                "first-world assertion requires unique explicit evidence IDs"
            )
        rows = (assertion.value or {}).get("evidence", [])
        if party_registry and rows:
            raise ValueError(
                "Party Registry cannot silently discard declared extraction evidence"
            )
        if not isinstance(rows, list):
            raise ValueError("first-world evidence rows must be a list")
        by_id = {
            row.get("evidence_ref_id"): row for row in rows if isinstance(row, dict)
        }
        if not party_registry and (
            not isinstance(rows, list)
            or len(by_id) != len(rows)
            or set(by_id) != set(assertion.evidence_ref_ids)
        ):
            raise ValueError("first-world extraction evidence closure disagrees")
        for raw_id in assertion.evidence_ref_ids:
            span = None if party_registry else by_id[raw_id].get("source_span_ref_id")
            if not party_registry and (not isinstance(span, str) or not span.strip()):
                raise ValueError(
                    "first-world extraction requires an explicit reviewed span"
                )
            record = SimpleNamespace(
                evidence_ref_id=raw_id,
                source_artifact_id=artifact.source_artifact_id,
                source_domain="party_registry" if party_registry else "worldbuilding",
                evidence_role="support",
                can_open_source=not party_registry,
                can_highlight_span=not party_registry,
                source_span_ref_id=span,
                locator=None,
                uri=None,
            )
            previous = evidence.setdefault(raw_id, record)
            if vars(previous) != vars(record):
                raise ValueError(
                    "first-world evidence ID has conflicting source bindings"
                )
    view = SimpleNamespace(evidence=evidence)
    if not party_registry:
        return map_worldbuilding_extraction_contribution_v3(
            view, contribution, pair_to_dm
        )
    mapped = _map_contributions(view, [contribution], pair_to_dm)[0]
    typed = []
    for assertion in mapped.assertions:
        refs = [
            EvidenceRefV2(
                evidence_ref_id=ref.evidence_ref_id,
                source_artifact_id=ref.source_artifact_id,
                source_revision_id=ref.source_revision_id,
                source_domain_key="party_registry",
                source_domain=SourceDomain.OTHER,
                evidence_role=EvidenceRole.SUPPORT,
                can_open_source=False,
                can_highlight_span=False,
                session_id=None,
                source_span_ref_id=None,
                locator=None,
                uri=None,
                source_locator=None,
                line_ref=None,
            ).model_dump(mode="json")
            for ref in assertion.evidence_refs
        ]
        typed.append({**assertion.model_dump(mode="json"), "evidence_refs": refs})
    return GraphContributionV3.model_validate(
        {
            **mapped.model_dump(mode="json"),
            "schema_version": "dm_graph_contribution_v3",
            "assertions": typed,
        }
    )

"""Threat publication test helpers without legacy graph-engine imports."""
from __future__ import annotations


import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch


import apps.live_control_server.services.threat_publication_identity as identity_svc
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    PROVIDER_DUNGEONMIND,
    MechanicsLocatorV1,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
)
from apps.live_control_server.models.threat_publication_identity import MATCHING_PROFILE_V1
from apps.live_control_server.models.threat_publication_proposal import (
    PrepareThreatPublicationProposalRequestV1,
)
from apps.live_control_server.models.threat_statblock_binding import (
    external_statblock_node_id,
)
from apps.live_control_server.services.threat_draft_store import create_threat_draft
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView


DEFAULT_DIGEST = "sha256:" + "a" * 64


__all__ = [
    "DEFAULT_DIGEST",
    "_locator",
    "_create_draft",
    "_create_new_resolution",
    "_prepare_request",
    "external_statblock_node_id",
]


def _locator(**overrides: Any) -> MechanicsLocatorV1:
    payload: dict[str, Any] = {
        "provider": PROVIDER_DUNGEONMIND,
        "statblock_id": "sb_1",
        "revision_id": "rev_1",
        "contract": "dungeonmind.dungeonbuddy-statblocks",
        "contract_version": "1.0.0",
        "definition_digest": DEFAULT_DIGEST,
    }
    payload.update(overrides)
    return MechanicsLocatorV1.model_validate(payload)


def _create_draft(tmp_path: Path, **overrides: Any):
    payload: dict[str, Any] = {
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "name": "Ironhide Brute",
        "description": "A brutal enforcer.",
        "threat_kind": "creature",
        "generation_intent": GenerationIntentV1(
            ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            target_cr="3",
        ),
        "graph_context_snapshot": GraphContextSnapshotV1(graph_revision_id="rev:aaa"),
        "created_by": "gm",
    }
    payload.update(overrides)
    return create_threat_draft(tmp_path, CreateThreatDraftRequest.model_validate(payload))


def _node(
    node_id: str,
    *,
    label: str,
    kind: str = "Threat",
    aliases: list[str] | None = None,
    role: str = "antagonist",
) -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind,
        role=role,
        aliases=aliases or [],
        source_domains=["worldbuilding"],
    )


def _projection_for(*nodes: WorldGraphProjectionNodeView, revision_id: str):
    return identity_svc.build_projection_fixture(revision_id=revision_id, nodes=list(nodes))


def _prepare(tmp_path: Path, draft_id: str, operation_id: str, **overrides: Any):
    body = identity_svc.PrepareThreatIdentityCandidatesRequestV1.model_validate(overrides or {})
    return identity_svc.prepare_identity_candidates(tmp_path, draft_id, operation_id, body)


def _decide(tmp_path: Path, draft_id: str, operation_id: str, **overrides: Any):
    overrides.setdefault("rejected_candidate_node_ids", [])
    body = identity_svc.CreateThreatIdentityResolutionRequestV1.model_validate(overrides)
    with patch.object(
        identity_svc,
        "_exact_revision_contains_node_id",
        side_effect=lambda _operation, node_id, *, world_root: False,
    ):
        return identity_svc.decide_identity_resolution(tmp_path, draft_id, operation_id, body)


def _reject_all_collisions(candidate_set) -> list[str]:
    return [c.node_id for c in candidate_set.candidates if c.exact_name_collision]


def _create_new_resolution(
    tmp_path: Path, draft, op_id: str, parent: str, *, resolution_id: str | None = None
):
    projection = _projection_for(_node("threat:visible", label="Visible"), revision_id=parent)
    rid = resolution_id or str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Visible")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=rid,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="new",
        )
    assert outcome.response.result_label == "publication_identity_created_new"
    return rid, outcome.response.resolution


def _prepare_request(proposal_id: str | None = None, **overrides: Any):
    payload: dict[str, Any] = {
        "proposal_id": proposal_id or str(uuid.uuid4()),
        "actor": "gm",
    }
    payload.update(overrides)
    return PrepareThreatPublicationProposalRequestV1.model_validate(payload)

"""Service contract for source-backed, inert recap World genesis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.live_control_server.models.recap_world_genesis import (
    RecapWorldGenesisConfirmRequest,
    RecapWorldGenesisPrepareRequest,
)
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationReceipt,
    WorldGraphInitializationState,
)
from apps.live_control_server.services.recap_world_genesis import (
    RecapWorldGenesisError,
    confirm_recap_world_genesis,
    prepare_recap_world_genesis,
)


REPO = Path(__file__).resolve().parents[1]


@dataclass
class _Authority:
    initialized: bool = False
    request: object | None = None

    def probe(self, world_id: str) -> WorldGraphInitializationState:
        return WorldGraphInitializationState(
            world_id=world_id,
            state="initialized" if self.initialized else "uninitialized",
        )

    def initialize(self, request):
        self.request = request
        if self.initialized:
            return WorldGraphInitializationReceipt(
                world_id=request.world_id, initialization_id=request.initialization_id,
                published_revision_id="rev:d0", reviewed_contribution_id=request.reviewed_contribution.contribution_id,
                reviewed_contribution_sha256="digest", accepted_assertion_ids=tuple(
                    item.assertion_id for item in request.reviewed_contribution.accepted_assertions
                ), outcome="already_initialized",
            )
        self.initialized = True
        return WorldGraphInitializationReceipt(
            world_id=request.world_id, initialization_id=request.initialization_id,
            published_revision_id="rev:d0", reviewed_contribution_id=request.reviewed_contribution.contribution_id,
            reviewed_contribution_sha256="digest", accepted_assertion_ids=tuple(
                item.assertion_id for item in request.reviewed_contribution.accepted_assertions
            ), outcome="initialized",
        )


def _prepare(authority: _Authority):
    return prepare_recap_world_genesis(
        RecapWorldGenesisPrepareRequest(
            world_id="eldyrwild", campaign_id="longmont-c1", baseline_roster_key="1", requested_by="tester"
        ), repo=REPO, authority=authority,
    )


def test_c1_prepare_is_inert_and_materializes_six_pc_identities_only() -> None:
    authority = _Authority()
    plan = _prepare(authority)
    assert authority.request is None
    assert plan.source_artifact_id == "artifact:party-registry:longmont-c1"
    assert plan.pc_object_ids == (
        "node:baergrom", "node:bonogo", "node:caelynn", "node:ephanna", "node:karsemine", "node:stafl"
    )
    assert plan.pc_identity_keys == (
        "pc::baergrom", "pc::bonogo", "pc::caelynn", "pc::ephanna", "pc::karsemine", "pc::stafl"
    )
    assert len(plan.accepted_assertion_ids) == 6


def test_confirm_rematerializes_then_uses_party_registry_standing_profile() -> None:
    authority = _Authority()
    plan = _prepare(authority)
    receipt = confirm_recap_world_genesis(
        RecapWorldGenesisConfirmRequest(plan=plan, confirming_principal="operator"), repo=REPO, authority=authority
    )
    assert receipt.published_revision_id == "rev:d0"
    request = authority.request
    assert request is not None
    assert request.source_artifact.source_domain == "party_registry"
    assert request.reviewed_contribution.source_kind == "standing_context"
    assert all(item.assertion_kind == "node" for item in request.reviewed_contribution.accepted_assertions)
    assert not request.reviewed_contribution.candidate_assertions
    assert not request.reviewed_contribution.rejected_assertions


def test_adapter_preserves_party_registry_key_with_other_coarse_domain() -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        _build_command,
    )
    from apps.live_control_server.services.recap_world_genesis import _materialize_plan
    from apps.live_control_server.ports.world_graph_initialization import WorldGraphInitializationRequest

    plan, artifact, contribution = _materialize_plan(
        RecapWorldGenesisPrepareRequest(
            world_id="world:adapter", campaign_id="longmont-c1", baseline_roster_key="1", requested_by="test"
        ), repo=REPO,
    )
    command = _build_command(
        WorldGraphInitializationRequest(
            world_id=plan.world_id, campaign_id=plan.campaign_id, initialization_id=plan.initialization_id,
            source_plan_schema=plan.schema_, source_plan_id=plan.plan_id, source_plan_sha256=plan.plan_digest,
            actor="test", source_artifact=artifact, source_revision_token=plan.source_revision_id,
            source_uri=plan.source_uri, reviewed_contribution=contribution,
        ), requested_initialized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert command.source_artifacts[0].source_domain_key == "party_registry"
    assert command.source_artifacts[0].source_domain.value == "other"
    assert command.reviewed_contribution.source_kind.value == "standing_context"
    assert {item.assertion_kind for item in command.reviewed_contribution.assertions} == {"node"}


def test_changed_registry_bytes_reject_carried_plan_before_initialize(tmp_path: Path) -> None:
    authority = _Authority()
    plan = _prepare(authority)
    source = REPO / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
    target = tmp_path / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes().replace(b'"baergrom"', b'"baergrom" '))
    with pytest.raises(RecapWorldGenesisError) as exc:
        confirm_recap_world_genesis(
            RecapWorldGenesisConfirmRequest(plan=plan, confirming_principal="operator"), repo=tmp_path, authority=authority
        )
    assert exc.value.code == "plan_verification_failed"
    assert authority.request is None


def test_initialized_world_is_refused_before_prepare() -> None:
    with pytest.raises(RecapWorldGenesisError) as exc:
        _prepare(_Authority(initialized=True))
    assert exc.value.code == "already_initialized"

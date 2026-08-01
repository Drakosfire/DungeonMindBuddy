"""SBW09b: Threat publication identity-resolution service tests."""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import apps.live_control_server.services.threat_publication_identity as identity_svc
import apps.live_control_server.services.threat_publication_operations as pub_svc
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    PROVIDER_DUNGEONMIND,
    MechanicsLocatorV1,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptedMechanicsRefV1
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.models.threat_publication import (
    BeginThreatPublicationOperationRequestV1,
    ThreatPublicationOperationResponseV1,
)
from apps.live_control_server.models.threat_publication_identity import (
    MATCHING_PROFILE_V1,
    CreateThreatIdentityResolutionRequestV1,
    PrepareThreatIdentityCandidatesRequestV1,
    ThreatIdentityCandidateSetV1,
    ThreatPublicationIdentityLedgerV1,
    derive_created_node_id,
)
from apps.live_control_server.services.threat_draft_store import (
    _draft_path,
    attach_accepted_mechanics_ref,
    create_threat_draft,
    update_threat_draft,
)
from apps.live_control_server.services.threat_publication_operations import (
    PublicationOperationOutcome,
    begin_publication_operation,
    refresh_publication_operation,
)
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView

DEFAULT_DIGEST = "sha256:" + "a" * 64
PARENT = "rev:parent1"


class _FakeHead:
    def __init__(self, revision_id: str) -> None:
        self.head_revision_id = revision_id


def _mock_head(monkeypatch, revision_id: str) -> None:
    monkeypatch.setattr(
        pub_svc.kernel, "open_world_graph_head", lambda root, world_id: _FakeHead(revision_id)
    )


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


def _mechanics_saved_draft(tmp_path: Path, monkeypatch, *, name: str = "Ironhide Brute"):
    draft = _create_draft(tmp_path, name=name)
    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(), accepted_from_draft_version=draft.version, accepted_at="2020-01-01T00:00:00Z"
    )
    draft = attach_accepted_mechanics_ref(
        tmp_path, draft_id=draft.draft_id, expected_version=draft.version, locator=ref
    )
    _mock_head(monkeypatch, PARENT)
    return draft


def _begin_operation(tmp_path: Path, draft, *, operation_id: str | None = None):
    op_id = operation_id or str(uuid.uuid4())
    request = BeginThreatPublicationOperationRequestV1.model_validate(
        {
            "operation_id": op_id,
            "expected_draft_version": draft.version,
            "expected_parent_revision_id": PARENT,
            "actor": "gm",
        }
    )
    outcome = begin_publication_operation(tmp_path, draft.draft_id, request)
    assert outcome.response.result_label == "publication_ready"
    return op_id, outcome.response.operation


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
        source_domains=["campaign"],
    )


def _projection_for(*nodes: WorldGraphProjectionNodeView):
    return identity_svc.build_projection_fixture(revision_id=PARENT, nodes=list(nodes))


def _prepare(tmp_path: Path, draft_id: str, operation_id: str, **overrides: Any):
    body = PrepareThreatIdentityCandidatesRequestV1.model_validate(overrides or {})
    return identity_svc.prepare_identity_candidates(tmp_path, draft_id, operation_id, body)


def _decide(tmp_path: Path, draft_id: str, operation_id: str, **overrides: Any):
    overrides.setdefault("rejected_candidate_node_ids", [])
    body = CreateThreatIdentityResolutionRequestV1.model_validate(overrides)
    return identity_svc.decide_identity_resolution(tmp_path, draft_id, operation_id, body)


def _reject_all_collisions(candidate_set) -> list[str]:
    return [c.node_id for c in candidate_set.candidates if c.exact_name_collision]


def _persisted_refuse_resolution(
    tmp_path: Path, monkeypatch, *, resolution_id: str | None = None
) -> tuple[Any, str, str]:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    rid = resolution_id or str(uuid.uuid4())
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=rid,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="no",
        )
    return draft, op_id, rid


def _identity_ledger_json(tmp_path: Path, draft_id: str, operation_id: str) -> dict[str, Any]:
    path = identity_svc._ledger_path(tmp_path, draft_id, operation_id)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_identity_ledger_json(
    tmp_path: Path, draft_id: str, operation_id: str, payload: dict[str, Any]
) -> None:
    path = identity_svc._ledger_path(tmp_path, draft_id, operation_id)
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# §13 named tests
# ---------------------------------------------------------------------------


def test_prepare_uses_exact_expected_parent_and_threat_only_candidates(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(
        _node("threat:1", label="Alpha"),
        _node("npc:1", label="Beta", kind="NPC"),
        _node("threat:2", label="Gamma"),
    )

    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        outcome = _prepare(
            tmp_path, draft.draft_id, op_id, query_text="Alpha"
        )

    assert outcome.response.result_label == "publication_identity_candidates_ready"
    assert outcome.response.candidate_set is not None
    ids = {c.node_id for c in outcome.response.candidate_set.candidates}
    assert ids == {"threat:1"}
    assert "npc:1" not in ids


def test_prepare_refreshes_and_rejects_stale_publication_operation(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft)
    draft = update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description="changed",
            threat_kind=draft.threat_kind,
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
        ),
    )
    projection = _projection_for(_node("threat:1", label="Alpha"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        outcome = _prepare(tmp_path, draft.draft_id, op_id)
    assert outcome.response.result_label == "publication_identity_operation_not_ready"
    assert outcome.response.candidate_set is None
    assert identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_prepare_surfaces_exact_alias_collision_despite_unrelated_query(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Ironhide Brute")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(
        _node("threat:low", label="Unrelated", aliases=["zzzz"]),
        _node("threat:hit", label="Other", aliases=["Ironhide Brute"]),
    )
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        outcome = _prepare(
            tmp_path,
            draft.draft_id,
            op_id,
            query_text="completely unrelated query",
        )
    assert outcome.response.candidate_set is not None
    by_id = {c.node_id: c for c in outcome.response.candidate_set.candidates}
    assert "threat:hit" in by_id
    assert by_id["threat:hit"].exact_name_collision is True


def test_candidate_rank_never_selects_identity(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="ZZZZ Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(
        _node("threat:a", label="Alpha Match"),
        _node("threat:b", label="Alpha Backup"),
    )
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        outcome = _prepare(tmp_path, draft.draft_id, op_id, query_text="Alpha Match")
    cs = outcome.response.candidate_set
    assert cs is not None
    assert len(cs.candidates) >= 2
    assert cs.candidates[0].node_id == "threat:a"
    assert cs.candidates[0].match_score >= cs.candidates[1].match_score
    assert outcome.response.resolution is None


def test_create_new_requires_explicit_rejection_of_every_exact_collision(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Ironhide Brute")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:collision", label="Ironhide Brute"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=[],
            actor="gm",
            reason="new threat",
        )
    assert outcome.response.result_label == "publication_identity_review_required"
    assert identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_create_new_derives_stable_name_independent_proposed_threat_id(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique Name XYZ")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:other", label="Other"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Other")
        cs = prepared.response.candidate_set
        assert cs is not None
        expected_id = derive_created_node_id(
            world_id="world_1",
            campaign_id="campaign_1",
            draft_id=draft.draft_id,
            operation_id=op_id,
        )
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="new threat",
        )
    assert outcome.response.result_label == "publication_identity_created_new"
    assert outcome.response.resolution is not None
    assert outcome.response.resolution.created_node_id == expected_id


def test_create_new_rejects_existing_derived_id_without_random_suffix(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique Name XYZ")
    op_id, _op = _begin_operation(tmp_path, draft)
    derived = derive_created_node_id(
        world_id="world_1",
        campaign_id="campaign_1",
        draft_id=draft.draft_id,
        operation_id=op_id,
    )
    projection = _projection_for(_node(derived, label="Existing Derived"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Existing Derived")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="new threat",
        )
    assert outcome.response.result_label == "publication_identity_new_id_collision"
    assert identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_connect_existing_requires_exact_reviewed_threat_node(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:target", label="Target Threat"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Target Threat")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="connect_existing",
            target_node_id="threat:target",
            actor="gm",
            reason="connect",
        )
    assert outcome.response.result_label == "publication_identity_connected_existing"
    assert outcome.response.resolution is not None
    assert outcome.response.resolution.selected_target is not None
    assert outcome.response.resolution.selected_target.node_id == "threat:target"


def test_connect_existing_rejects_wrong_kind_redirect_and_name_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(
        _node("threat:ok", label="Target Threat"),
        _node("npc:wrong", label="Target Threat", kind="NPC"),
    )
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Target Threat")
        cs = prepared.response.candidate_set
        assert cs is not None

        missing = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="connect_existing",
            target_node_id="npc:wrong",
            actor="gm",
            reason="connect",
        )
        redirect = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="connect_existing",
            target_node_id="threat:merged-away",
            actor="gm",
            reason="connect",
        )
    assert missing.response.result_label == "publication_identity_target_not_found"
    assert redirect.response.result_label == "publication_identity_target_not_found"


def test_decision_rejects_changed_candidate_set_digest_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest="sha256:" + "b" * 64,
            decision="refuse",
            actor="gm",
            reason="no",
        )
    assert outcome.response.result_label == "publication_identity_candidate_set_changed"
    assert identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_resolution_exact_replay_does_not_read_predecessor_or_graph(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    resolution_id = str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        request_body = {
            "resolution_id": resolution_id,
            "matching_profile": MATCHING_PROFILE_V1,
            "candidate_query": cs.candidate_query,
            "candidate_set_digest": cs.candidate_set_digest,
            "decision": "refuse",
            "rejected_candidate_node_ids": [],
            "actor": "gm",
            "reason": "no",
        }
        first = _decide(tmp_path, draft.draft_id, op_id, **request_body)
        assert first.created is True

    with patch.object(identity_svc, "refresh_publication_operation") as refresh_mock, patch.object(
        identity_svc, "project_world_graph"
    ) as project_mock:
        replay = _decide(tmp_path, draft.draft_id, op_id, **request_body)
        refresh_mock.assert_not_called()
        project_mock.assert_not_called()

    assert replay.response.result_label == "publication_identity_refused"
    assert replay.created is False


def test_resolution_same_id_changed_request_conflicts(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    resolution_id = str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="no",
        )
        conflict = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="changed reason",
        )
    assert conflict.response.result_label == "publication_identity_input_conflict"
    ledger = identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id)
    assert ledger is not None
    assert len(ledger.resolutions) == 1
    assert ledger.resolutions[0].reason == "no"


def test_one_active_resolution_requires_explicit_supersession(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        first_id = str(uuid.uuid4())
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=first_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="first",
        )
        busy = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="second",
        )
    assert busy.response.result_label == "publication_identity_busy"


def test_supersession_atomically_links_old_new_and_active_pointer(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        first_id = str(uuid.uuid4())
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=first_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="first",
        )
        second_id = str(uuid.uuid4())
        supersede = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=second_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="replace",
            supersedes_resolution_id=first_id,
        )
    assert supersede.response.result_label == "publication_identity_superseded"
    ledger = identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id)
    assert ledger is not None
    assert ledger.active_resolution_id == second_id
    old = next(r for r in ledger.resolutions if r.resolution_id == first_id)
    new = next(r for r in ledger.resolutions if r.resolution_id == second_id)
    assert old.state == "superseded"
    assert old.superseded_by_resolution_id == second_id
    assert new.supersedes_resolution_id == first_id
    assert new.state == "active"


def test_concurrent_first_decisions_have_one_coherent_winner(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
    cs = prepared.response.candidate_set
    assert cs is not None
    monkeypatch.setattr(identity_svc, "project_world_graph", lambda *args, **kwargs: projection)
    barrier = threading.Barrier(2)
    results: list[str] = []

    def worker(resolution_id: str) -> None:
        barrier.wait()
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="race",
        )
        results.append(outcome.response.result_label)

    t1 = threading.Thread(target=worker, args=(str(uuid.uuid4()),))
    t2 = threading.Thread(target=worker, args=(str(uuid.uuid4()),))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    ledger = identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id)
    assert ledger is not None
    assert len(ledger.resolutions) == 1
    assert "publication_identity_refused" in results
    assert "publication_identity_busy" in results


def test_concurrent_supersessions_have_one_coherent_winner(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    first_id = str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=first_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="first",
        )

    monkeypatch.setattr(identity_svc, "project_world_graph", lambda *args, **kwargs: projection)
    barrier = threading.Barrier(2)
    labels: list[str] = []

    def worker(resolution_id: str) -> None:
        barrier.wait()
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="replace",
            supersedes_resolution_id=first_id,
        )
        labels.append(outcome.response.result_label)

    t1 = threading.Thread(target=worker, args=(str(uuid.uuid4()),))
    t2 = threading.Thread(target=worker, args=(str(uuid.uuid4()),))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    ledger = identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id)
    assert ledger is not None
    active = [r for r in ledger.resolutions if r.state == "active"]
    assert len(active) == 1
    assert "publication_identity_superseded" in labels
    assert "publication_identity_busy" in labels or "publication_identity_input_conflict" in labels


def test_atomic_identity_write_failure_preserves_prior_ledger(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    resolution_id = str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="first",
        )
    before_bytes = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()
    with patch.object(identity_svc, "project_world_graph", return_value=projection), patch.object(
        identity_svc, "_save_ledger_unlocked", side_effect=identity_svc._storage_unavailable()
    ):
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="second",
            supersedes_resolution_id=resolution_id,
        )
    after_bytes = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()
    assert before_bytes == after_bytes


def test_corrupt_identity_ledger_fails_closed_without_rewrite(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    path = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, str(uuid.uuid4())
    )
    assert outcome.response.result_label == "publication_identity_integrity_failure"
    assert path.read_text(encoding="utf-8") == "{not json"


def test_identity_ledger_rejects_predecessor_source_or_parent_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, op = _begin_operation(tmp_path, draft)
    ledger = ThreatPublicationIdentityLedgerV1.model_validate(
        {
            "schema": "dmb_threat_publication_identity_ledger_v1",
            "draft_id": draft.draft_id,
            "operation_id": op_id,
            "source_digest": "sha256:" + "f" * 64,
            "expected_parent_revision_id": PARENT,
            "active_resolution_id": None,
            "resolutions": [],
        }
    )
    identity_svc._save_ledger_unlocked(tmp_path, ledger)
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="no",
        )
    assert outcome.response.result_label == "publication_identity_integrity_failure"


def test_identity_flow_leaves_graph_draft_mechanics_and_dms_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    draft_path = _draft_path(tmp_path, draft.draft_id)
    draft_before = draft_path.read_bytes()
    op_id, _op = _begin_operation(tmp_path, draft)
    pub_path = pub_svc._ledger_path(tmp_path, draft.draft_id)
    pub_before = pub_path.read_bytes() if pub_path.is_file() else b""
    graph_root = tmp_path / "world-graph"
    graph_root.mkdir(parents=True, exist_ok=True)
    graph_before = {
        p.relative_to(graph_root): p.read_bytes()
        for p in graph_root.rglob("*")
        if p.is_file()
    }

    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="no",
        )

    assert draft_path.read_bytes() == draft_before
    assert (pub_path.read_bytes() if pub_path.is_file() else b"") == pub_before
    graph_after = {
        p.relative_to(graph_root): p.read_bytes()
        for p in graph_root.rglob("*")
        if p.is_file()
    }
    assert graph_after == graph_before


# ---------------------------------------------------------------------------
# Adversarial hardening tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", ["[]", "null", '"string"'])
def test_malformed_identity_ledger_json_fails_closed(
    tmp_path: Path, monkeypatch, payload: str
) -> None:
    draft, op_id, _rid = _persisted_refuse_resolution(tmp_path, monkeypatch)
    path = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id)
    before = path.read_bytes()
    path.write_text(payload, encoding="utf-8")
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, str(uuid.uuid4())
    )
    assert outcome.response.result_label == "publication_identity_integrity_failure"
    assert path.read_bytes() == payload.encode("utf-8")
    path.write_bytes(before)


def test_persisted_candidate_set_rejects_non_threat_kind() -> None:
    base = {
        "schema": "dmb_threat_publication_identity_candidate_set_v1",
        "draft_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "source_digest": "sha256:" + "a" * 64,
        "expected_parent_revision_id": "rev:parent1",
        "matching_profile": MATCHING_PROFILE_V1,
        "candidate_query": "query",
        "eligible_threat_count": 1,
        "exact_collision_count": 0,
        "truncated": False,
        "candidates": [
            {
                "node_id": "npc:1",
                "label": "Wrong",
                "kind": "NPC",
                "role": "antagonist",
                "aliases": [],
                "source_domains": [],
                "binding_ids": [],
                "has_exact_accepted_binding": False,
                "match_score": 0,
                "match_reasons": [],
                "exact_name_collision": False,
            }
        ],
        "candidate_set_digest": "sha256:" + "b" * 64,
    }
    with pytest.raises(ValueError, match="candidate kind must be Threat"):
        ThreatIdentityCandidateSetV1.model_validate(base)


def test_persisted_candidate_set_rejects_mismatched_collision_count() -> None:
    payload = {
        "schema": "dmb_threat_publication_identity_candidate_set_v1",
        "draft_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "source_digest": "sha256:" + "a" * 64,
        "expected_parent_revision_id": "rev:parent1",
        "matching_profile": MATCHING_PROFILE_V1,
        "candidate_query": "query",
        "eligible_threat_count": 1,
        "exact_collision_count": 1,
        "truncated": False,
        "candidates": [
            {
                "node_id": "threat:1",
                "label": "One",
                "kind": "Threat",
                "role": "antagonist",
                "aliases": [],
                "source_domains": [],
                "binding_ids": [],
                "has_exact_accepted_binding": False,
                "match_score": 0,
                "match_reasons": [],
                "exact_name_collision": False,
            }
        ],
        "candidate_set_digest": "sha256:" + "b" * 64,
    }
    with pytest.raises(ValueError, match="exact_collision_count"):
        ThreatIdentityCandidateSetV1.model_validate(payload)


def test_persisted_candidate_set_rejects_blank_candidate_query() -> None:
    payload = {
        "schema": "dmb_threat_publication_identity_candidate_set_v1",
        "draft_id": str(uuid.uuid4()),
        "operation_id": str(uuid.uuid4()),
        "source_digest": "sha256:" + "a" * 64,
        "expected_parent_revision_id": "rev:parent1",
        "matching_profile": MATCHING_PROFILE_V1,
        "candidate_query": "   ",
        "eligible_threat_count": 0,
        "exact_collision_count": 0,
        "truncated": False,
        "candidates": [],
        "candidate_set_digest": "sha256:" + "b" * 64,
    }
    with pytest.raises(ValueError, match="candidate_query"):
        ThreatIdentityCandidateSetV1.model_validate(payload)


def test_persisted_resolution_rejects_tampered_request_digest(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, resolution_id = _persisted_refuse_resolution(tmp_path, monkeypatch)
    ledger = _identity_ledger_json(tmp_path, draft.draft_id, op_id)
    ledger["resolutions"][0]["request_digest"] = "sha256:" + "c" * 64
    _write_identity_ledger_json(tmp_path, draft.draft_id, op_id, ledger)
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, resolution_id
    )
    assert outcome.response.result_label == "publication_identity_integrity_failure"


def test_persisted_resolution_rejects_tampered_candidate_set_digest(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, resolution_id = _persisted_refuse_resolution(tmp_path, monkeypatch)
    ledger = _identity_ledger_json(tmp_path, draft.draft_id, op_id)
    ledger["resolutions"][0]["candidate_set_digest"] = "sha256:" + "d" * 64
    _write_identity_ledger_json(tmp_path, draft.draft_id, op_id, ledger)
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, resolution_id
    )
    assert outcome.response.result_label == "publication_identity_integrity_failure"


def test_persisted_resolution_rejects_tampered_selected_target_fields(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    resolution_id = str(uuid.uuid4())
    projection = _projection_for(_node("threat:target", label="Target Threat"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Target Threat")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="connect_existing",
            target_node_id="threat:target",
            actor="gm",
            reason="connect",
        )
    ledger = _identity_ledger_json(tmp_path, draft.draft_id, op_id)
    ledger["resolutions"][0]["selected_target"]["label"] = "Tampered Label"
    _write_identity_ledger_json(tmp_path, draft.draft_id, op_id, ledger)
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, resolution_id
    )
    assert outcome.response.result_label == "publication_identity_integrity_failure"


def test_candidate_composition_respects_advisory_bound_of_twelve(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique Advisory Bound")
    op_id, _op = _begin_operation(tmp_path, draft)
    nodes = [_node(f"threat:{index}", label=f"Threat {index}") for index in range(20)]
    projection = _projection_for(*nodes)
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        outcome = _prepare(tmp_path, draft.draft_id, op_id, query_text="Threat")
    cs = outcome.response.candidate_set
    assert cs is not None
    non_collisions = [candidate for candidate in cs.candidates if not candidate.exact_name_collision]
    assert len(non_collisions) <= 12
    assert cs.truncated is True
    assert len(cs.candidates) <= 32


def test_read_missing_predecessor_operation_returns_not_found(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, resolution_id = _persisted_refuse_resolution(tmp_path, monkeypatch)
    pub_path = pub_svc._ledger_path(tmp_path, draft.draft_id)
    pub_path.unlink()
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, resolution_id
    )
    assert outcome.response.result_label == "publication_identity_not_found"
    assert outcome.response.resolution is None


def test_read_fails_closed_on_predecessor_source_parent_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, resolution_id = _persisted_refuse_resolution(tmp_path, monkeypatch)
    predecessor = pub_svc.read_publication_operation(tmp_path, draft.draft_id, op_id)
    assert predecessor.response.operation is not None
    tampered_operation = predecessor.response.operation.model_copy(
        update={"source_digest": "sha256:" + "e" * 64}
    )
    tampered_outcome = PublicationOperationOutcome(
        predecessor.response.model_copy(update={"operation": tampered_operation})
    )
    with patch.object(
        identity_svc, "read_publication_operation", return_value=tampered_outcome
    ):
        outcome = identity_svc.read_identity_resolution(
            tmp_path, draft.draft_id, op_id, resolution_id
        )
    assert outcome.response.result_label == "publication_identity_integrity_failure"


def test_read_preserves_historical_resolution_for_stale_predecessor(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, resolution_id = _persisted_refuse_resolution(tmp_path, monkeypatch)
    draft = update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description="changed",
            threat_kind=draft.threat_kind,
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
        ),
    )
    refresh = refresh_publication_operation(tmp_path, draft.draft_id, op_id)
    assert refresh.response.operation is not None
    assert refresh.response.operation.state == "stale"
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, resolution_id
    )
    assert outcome.response.result_label == "publication_identity_refused"
    assert outcome.response.resolution is not None
    assert outcome.response.predecessor_state == "stale"
    assert outcome.response.predecessor_usable is False


def test_read_rejects_tampered_created_node_id_when_predecessor_available(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique Create")
    op_id, _op = _begin_operation(tmp_path, draft)
    resolution_id = str(uuid.uuid4())
    projection = _projection_for(_node("threat:other", label="Other"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Other")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=resolution_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="new threat",
        )
    ledger = _identity_ledger_json(tmp_path, draft.draft_id, op_id)
    ledger["resolutions"][0]["created_node_id"] = "threat:authored:" + "f" * 32
    _write_identity_ledger_json(tmp_path, draft.draft_id, op_id, ledger)
    outcome = identity_svc.read_identity_resolution(
        tmp_path, draft.draft_id, op_id, resolution_id
    )
    assert outcome.response.result_label == "publication_identity_integrity_failure"


# ---------------------------------------------------------------------------
# Boundary fix tests (storage-root / predecessor mapping / resolution validation)
# ---------------------------------------------------------------------------


def test_prepare_threads_separate_world_root_to_projection(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft)
    world_root = tmp_path / "separate-world-graph"
    world_root.mkdir()
    projection = _projection_for(_node("threat:1", label="One"))
    captured: dict[str, Path | None] = {}

    def capture(_request, *, root=None):
        captured["root"] = root
        return projection

    with patch.object(identity_svc, "project_world_graph", side_effect=capture):
        outcome = identity_svc.prepare_identity_candidates(
            tmp_path,
            draft.draft_id,
            op_id,
            PrepareThreatIdentityCandidatesRequestV1.model_validate({}),
            world_root=world_root,
        )

    assert outcome.response.result_label == "publication_identity_candidates_ready"
    assert captured["root"] == world_root


def test_decide_threads_separate_world_root_to_projection(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    world_root = tmp_path / "separate-world-graph"
    world_root.mkdir()
    projection = _projection_for(_node("threat:1", label="One"))
    captured: dict[str, Path | None] = {}

    def capture(_request, *, root=None):
        captured["root"] = root
        return projection

    with patch.object(identity_svc, "project_world_graph", side_effect=capture):
        prepared = identity_svc.prepare_identity_candidates(
            tmp_path,
            draft.draft_id,
            op_id,
            PrepareThreatIdentityCandidatesRequestV1.model_validate({"query_text": "One"}),
            world_root=world_root,
        )
        cs = prepared.response.candidate_set
        assert cs is not None
        identity_svc.decide_identity_resolution(
            tmp_path,
            draft.draft_id,
            op_id,
            CreateThreatIdentityResolutionRequestV1.model_validate(
                {
                    "resolution_id": str(uuid.uuid4()),
                    "matching_profile": MATCHING_PROFILE_V1,
                    "candidate_query": cs.candidate_query,
                    "candidate_set_digest": cs.candidate_set_digest,
                    "decision": "refuse",
                    "rejected_candidate_node_ids": [],
                    "actor": "gm",
                    "reason": "no",
                }
            ),
            world_root=world_root,
        )

    assert captured["root"] == world_root


def _predecessor_outcome(
    draft_id: str, result_label: str, *, operation=None
) -> PublicationOperationOutcome:
    return PublicationOperationOutcome(
        ThreatPublicationOperationResponseV1(
            draft_id=draft_id,
            result_label=result_label,
            operation=operation,
            message=result_label,
        ),
        created=False,
    )


@pytest.mark.parametrize(
    ("predecessor_label", "expected_label"),
    [
        ("publication_not_found", "publication_identity_not_found"),
        ("publication_storage_unavailable", "publication_identity_storage_unavailable"),
        ("publication_draft_unavailable", "publication_identity_storage_unavailable"),
        ("publication_integrity_failure", "publication_identity_integrity_failure"),
        ("publication_graph_unavailable", "publication_identity_graph_unavailable"),
        ("publication_stale", "publication_identity_operation_not_ready"),
        ("publication_cancelled", "publication_identity_operation_not_ready"),
    ],
)
def test_prepare_maps_typed_predecessor_failures(
    tmp_path: Path,
    monkeypatch,
    predecessor_label: str,
    expected_label: str,
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft)
    with patch.object(
        identity_svc,
        "refresh_publication_operation",
        return_value=_predecessor_outcome(draft.draft_id, predecessor_label),
    ):
        outcome = _prepare(tmp_path, draft.draft_id, op_id)
    assert outcome.response.result_label == expected_label
    assert identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


@pytest.mark.parametrize(
    ("predecessor_label", "expected_label"),
    [
        ("publication_not_found", "publication_identity_not_found"),
        ("publication_storage_unavailable", "publication_identity_storage_unavailable"),
        ("publication_integrity_failure", "publication_identity_integrity_failure"),
        ("publication_graph_unavailable", "publication_identity_graph_unavailable"),
        ("publication_stale", "publication_identity_operation_not_ready"),
    ],
)
def test_decide_maps_typed_predecessor_failures(
    tmp_path: Path,
    monkeypatch,
    predecessor_label: str,
    expected_label: str,
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique")
    op_id, _op = _begin_operation(tmp_path, draft)
    projection = _projection_for(_node("threat:1", label="One"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
    cs = prepared.response.candidate_set
    assert cs is not None
    with patch.object(
        identity_svc,
        "refresh_publication_operation",
        return_value=_predecessor_outcome(draft.draft_id, predecessor_label),
    ):
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=str(uuid.uuid4()),
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="no",
        )
    assert outcome.response.result_label == expected_label
    assert identity_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


@pytest.mark.parametrize(
    ("predecessor_label", "expected_label"),
    [
        ("publication_not_found", "publication_identity_not_found"),
        ("publication_storage_unavailable", "publication_identity_storage_unavailable"),
        ("publication_integrity_failure", "publication_identity_integrity_failure"),
        ("publication_graph_unavailable", "publication_identity_graph_unavailable"),
    ],
)
def test_read_maps_typed_predecessor_failures_when_operation_missing(
    tmp_path: Path,
    monkeypatch,
    predecessor_label: str,
    expected_label: str,
) -> None:
    draft, op_id, resolution_id = _persisted_refuse_resolution(tmp_path, monkeypatch)
    with patch.object(
        identity_svc,
        "read_publication_operation",
        return_value=_predecessor_outcome(draft.draft_id, predecessor_label),
    ):
        outcome = identity_svc.read_identity_resolution(
            tmp_path, draft.draft_id, op_id, resolution_id
        )
    assert outcome.response.result_label == expected_label


def test_tampered_historical_resolution_blocks_supersession_without_rewrite(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, name="Unique Create")
    op_id, _op = _begin_operation(tmp_path, draft)
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())
    projection = _projection_for(_node("threat:other", label="Other"))
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Other")
        cs = prepared.response.candidate_set
        assert cs is not None
        _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=first_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="new threat",
        )

    before_bytes = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()
    ledger = _identity_ledger_json(tmp_path, draft.draft_id, op_id)
    ledger["resolutions"][0]["created_node_id"] = "threat:authored:" + "f" * 32
    _write_identity_ledger_json(tmp_path, draft.draft_id, op_id, ledger)
    tampered_bytes = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()

    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=second_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            actor="gm",
            reason="replace",
            supersedes_resolution_id=first_id,
        )

    assert outcome.response.result_label == "publication_identity_integrity_failure"
    after_bytes = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()
    assert after_bytes == tampered_bytes
    assert after_bytes != before_bytes

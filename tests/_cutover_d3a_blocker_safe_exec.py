"""D.3A owning-workflow execution under the legacy import blocker.


Imported only from the fresh-interpreter witness body after the blocker is armed.
"""


from __future__ import annotations


import os
import tempfile
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch


from tests._cutover_d3a_blocker_safe_fixtures import (
    COMMIT_URL,
    DEFAULT_WORLD_ID,
    FIRST_WORLD_CONFIRM_URL,
    FIRST_WORLD_PREPARE_URL,
    GLASS_ORCHARD_WORLD_ID,
    PREPARE_URL,
    FakeWorldGraphAuthority,
    _empty_parent,
    _write_bld08_reviewable_run,
    authoring_body,
    ensure_migrated,
    first_world_confirm_body,
    first_world_decisions,
    first_world_prepare_body,
    object_proposal,
    require_test_dsn,
    truncate_dungeonmind,
    write_glass_orchard_bld08_run,
    write_post_genesis_graph_review_run,
)


def _assert_no_forbidden_loaded() -> None:
    import sys


    forbidden = (
        "graph_memory.kernel",
        "graph_memory.world_supergraph",
        "graph_memory.union_supergraph",
        "apps.live_control_server.integrations.buddy_files",
        "apps.live_control_server.integrations.dungeonmind_kernel",
    )
    loaded = [
        name
        for name in sys.modules
        if any(name == f or name.startswith(f + ".") for f in forbidden)
    ]
    assert loaded == [], f"forbidden modules loaded: {loaded}"


def _patch_repo_root(repo: Path) -> list[Any]:
    import apps.live_control_server.config as live_config
    import apps.live_control_server.services.extract_promote as promote_svc
    import apps.live_control_server.services.promotable_ingest_run as promotable_mod


    originals = [
        (live_config, "repo_root", live_config.repo_root),
        (promote_svc, "repo_root", promote_svc.repo_root),
        (promotable_mod, "repo_root", promotable_mod.repo_root),
    ]
    live_config.repo_root = lambda: repo  # type: ignore[assignment]
    promote_svc.repo_root = lambda: repo  # type: ignore[assignment]
    promotable_mod.repo_root = lambda: repo  # type: ignore[assignment]
    return originals


def _restore_patches(originals: list[Any]) -> None:
    for owner, name, value in originals:
        setattr(owner, name, value)


def _snapshot_authority_factories() -> list[tuple[object, str, object]]:
    """Capture get_world_graph_authority bindings that fake-authority installs mutate."""
    from apps.live_control_server.ports import world_graph_authority_access as access
    from apps.live_control_server.services import threat_publication_commits as commit_svc
    from apps.live_control_server.services import threat_publication_identity as identity_svc
    from apps.live_control_server.services import threat_publication_operations as ops_svc
    from apps.live_control_server.services import threat_publication_proposals as proposal_svc
    from apps.live_control_server.services import worldbuilding_graph_publication as wb_svc


    targets = (
        (access, "get_world_graph_authority"),
        (ops_svc, "get_world_graph_authority"),
        (identity_svc, "get_world_graph_authority"),
        (proposal_svc, "get_world_graph_authority"),
        (commit_svc, "get_world_graph_authority"),
        (wb_svc, "get_world_graph_authority"),
    )
    return [(owner, name, getattr(owner, name)) for owner, name in targets]


def _restore_authority_factories(snapshot: list[tuple[object, str, object]]) -> None:
    for owner, name, value in snapshot:
        setattr(owner, name, value)


def exercise_threat_publish_recover(base: Path) -> None:
    """Threat begin → identity → proposal → confirm → exact retry under blocker."""
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
        MechanicsLocatorV1,
    )
    from apps.live_control_server.models.threat_draft import (
        CreateThreatDraftRequest,
        GenerationIntentV1,
        GraphContextSnapshotV1,
        RulesetRefV1,
    )
    from apps.live_control_server.models.threat_publication import (
        BeginThreatPublicationOperationRequestV1,
    )
    from apps.live_control_server.models.threat_publication_commit import (
        ConfirmThreatPublicationRequestV1,
    )
    from apps.live_control_server.models.threat_publication_identity import (
        MATCHING_PROFILE_V1,
        CreateThreatIdentityResolutionRequestV1,
        PrepareThreatIdentityCandidatesRequestV1,
    )
    from apps.live_control_server.models.threat_publication_proposal import (
        PrepareThreatPublicationProposalRequestV1,
    )
    from apps.live_control_server.ports.world_graph_authority import (
        WorldGraphRevisionView,
    )
    from apps.live_control_server.services import threat_publication_commits as commit_svc
    from apps.live_control_server.services import threat_publication_identity as identity_svc
    from apps.live_control_server.services import threat_publication_operations as ops_svc
    from apps.live_control_server.services import threat_publication_proposals as proposal_svc
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
        create_threat_draft,
    )
    from graph_memory.projection.world_projection import WorldGraphProjectionNodeView
    from tests.test_cutover_threat_authority_port import (
        FakeWorldGraphAuthority as ThreatFake,
        _install_fake_authority,
    )


    tmp_path = base / "threat-workspace"
    tmp_path.mkdir(parents=True, exist_ok=True)
    absent = base / "buddy-world-graph-absent-threat"
    parent = "rev:d-a"
    fake = ThreatFake()
    fake.heads["world_1"] = parent
    fake.revisions[("world_1", parent)] = WorldGraphRevisionView(
        world_id="world_1",
        revision_id=parent,
        parent_revision_id=None,
        objects={},
        relationships={},
    )


    class _MP:
        def setattr(self, target, name=None, value=None):  # noqa: A003
            if isinstance(target, str) and value is None and name is not None:
                # pytest form: setattr("module.path.attr", value)
                value = name
                module_path, attr = target.rsplit(".", 1)
                import importlib


                mod = importlib.import_module(module_path)
                setattr(mod, attr, value)
                return
            if isinstance(target, str):
                module_path, attr = target.rsplit(".", 1)
                import importlib


                mod = importlib.import_module(module_path)
                setattr(mod, attr, name if value is None else value)
                return
            setattr(target, name, value)


        def setenv(self, key: str, value: str) -> None:
            os.environ[key] = value


    monkeypatch = _MP()
    from apps.live_control_server import config as live_config


    monkeypatch.setenv(
        live_config.WORLD_GRAPH_AUTHORITY_ENV,
        live_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
    )
    monkeypatch.setattr(
        "apps.live_control_server.config.world_graph_root", lambda: absent
    )
    for mod in (ops_svc, identity_svc, proposal_svc, commit_svc):
        monkeypatch.setattr(mod, "world_graph_root", lambda: absent)
    authority_snapshot = _snapshot_authority_factories()
    _install_fake_authority(monkeypatch, fake)


    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest.model_validate(
            {
                "world_id": "world_1",
                "campaign_id": "campaign_1",
                "name": "Ironhide Brute",
                "description": "A brutal enforcer.",
                "threat_kind": "creature",
                "generation_intent": GenerationIntentV1(
                    ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
                    target_cr="3",
                ),
                "graph_context_snapshot": GraphContextSnapshotV1(
                    graph_revision_id="rev:aaa"
                ),
                "created_by": "gm",
            }
        ),
    )
    locator = MechanicsLocatorV1.model_validate(
        {
            "provider": "dungeonmind",
            "statblock_id": "sb_1",
            "revision_id": "rev_1",
            "contract": "dungeonmind.dungeonbuddy-statblocks",
            "contract_version": "1.0.0",
            "definition_digest": "sha256:" + ("a" * 64),
        }
    )
    ref = AcceptedMechanicsRefV1.from_locator(
        locator,
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    draft = attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=draft.version,
        locator=ref,
    )
    op_id = str(uuid.uuid4())
    begin = ops_svc.begin_publication_operation(
        tmp_path,
        draft.draft_id,
        BeginThreatPublicationOperationRequestV1.model_validate(
            {
                "operation_id": op_id,
                "expected_draft_version": draft.version,
                "expected_parent_revision_id": parent,
                "actor": "gm",
            }
        ),
    )
    assert begin.response.result_label == "publication_ready"
    assert not absent.exists()


    projection = identity_svc.build_projection_fixture(
        revision_id=parent,
        nodes=[
            WorldGraphProjectionNodeView(
                node_id="threat:visible",
                label="Visible",
                kind="Threat",
                role="antagonist",
                aliases=[],
                source_domains=["worldbuilding"],
            )
        ],
    )
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        with patch.object(
            identity_svc,
            "_exact_revision_contains_node_id",
            side_effect=lambda *_a, **_k: False,
        ):
            prepared_id = identity_svc.prepare_identity_candidates(
                tmp_path,
                draft.draft_id,
                op_id,
                PrepareThreatIdentityCandidatesRequestV1.model_validate(
                    {"query_text": "Visible"}
                ),
            )
            cs = prepared_id.response.candidate_set
            assert cs is not None
            rejected = [c.node_id for c in cs.candidates if c.exact_name_collision]
            resolution = identity_svc.decide_identity_resolution(
                tmp_path,
                draft.draft_id,
                op_id,
                CreateThreatIdentityResolutionRequestV1.model_validate(
                    {
                        "resolution_id": str(uuid.uuid4()),
                        "matching_profile": MATCHING_PROFILE_V1,
                        "candidate_query": cs.candidate_query,
                        "candidate_set_digest": cs.candidate_set_digest,
                        "decision": "create_new",
                        "rejected_candidate_node_ids": rejected,
                        "actor": "gm",
                        "reason": "new",
                    }
                ),
            )
    assert resolution.response.result_label == "publication_identity_created_new"
    resolution_id = resolution.response.resolution.resolution_id


    prepared = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        PrepareThreatPublicationProposalRequestV1.model_validate(
            {"proposal_id": str(uuid.uuid4()), "actor": "gm"}
        ),
        world_root=absent,
    )
    assert prepared.response.result_label == "publication_proposal_ready"
    proposal = prepared.response.proposal
    assert proposal is not None


    first = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal.proposal_id,
        ConfirmThreatPublicationRequestV1.model_validate(
            {
                "commit_id": str(uuid.uuid4()),
                "sealed_proposal_digest": proposal.sealed_proposal_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "actor": "gm",
            }
        ),
        world_root=absent,
    )
    assert first.response.commit is not None
    assert first.response.result_label in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }
    child = first.response.commit.committed_revision_id
    assert child
    assert fake.publish_calls == 1


    retry = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal.proposal_id,
        ConfirmThreatPublicationRequestV1.model_validate(
            {
                "commit_id": first.response.commit.commit_id,
                "sealed_proposal_digest": proposal.sealed_proposal_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "actor": "gm",
            }
        ),
        world_root=absent,
    )
    assert retry.response.commit is not None
    assert retry.response.commit.committed_revision_id == child
    assert fake.publish_calls == 1
    assert not absent.exists()
    _restore_authority_factories(authority_snapshot)
    _assert_no_forbidden_loaded()


def exercise_worldbuilding_publish_recover(base: Path) -> None:
    """Worldbuilding prepare → confirm → exact retry under blocker."""
    from apps.live_control_server import config as live_config
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.ports import world_graph_authority_access as access
    from apps.live_control_server.services import worldbuilding_graph_publication as wb_svc
    from apps.live_control_server.services.graph_ingest_run_registry import (
        GRAPH_INGEST_RUNS_ENV,
    )


    repo = base / "wb-repo"
    repo.mkdir(parents=True, exist_ok=True)
    absent = base / "buddy-world-graph-absent-wb"
    parent = "rev:d-a"
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)


    os.environ[live_config.WORLD_GRAPH_AUTHORITY_ENV] = (
        live_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    os.environ["DUNGEONMIND_WORLD_GRAPH_ROOT"] = str(absent)
    os.environ[GRAPH_INGEST_RUNS_ENV] = "out/graph_memory/runs"
    originals = _patch_repo_root(repo)
    authority_snapshot = _snapshot_authority_factories()
    wb_svc.get_world_graph_authority = lambda **_kwargs: fake  # type: ignore[assignment]
    access.get_world_graph_authority = lambda **_kwargs: fake  # type: ignore[assignment]
    try:
        run_id, _source = _write_bld08_reviewable_run(repo)
        plan = wb_svc.prepare_worldbuilding(
            WorldbuildingWritePlanPrepareRequest.model_validate(
                {
                    "runId": run_id,
                    "expectedParentRevisionId": parent,
                    "dispositions": [
                        {"assertionId": "obj_session22_vial", "decision": "create_new"},
                        {"assertionId": "mystery_puddles", "decision": "create_new"},
                        {"assertionId": "e33", "decision": "accept"},
                    ],
                }
            )
        )
        first = wb_svc.confirm_worldbuilding(
            WorldbuildingWritePlanConfirmRequest(plan=plan)
        )
        assert first.outcome == "committed"
        retry = wb_svc.confirm_worldbuilding(
            WorldbuildingWritePlanConfirmRequest(plan=plan)
        )
        assert retry.outcome == "already_applied"
        assert retry.committed_revision_id == first.committed_revision_id
        assert fake.publish_calls == 1
        assert not absent.exists()
    finally:
        _restore_authority_factories(authority_snapshot)
        _restore_patches(originals)
    _assert_no_forbidden_loaded()


def exercise_hermes_graph_query(base: Path) -> None:
    """Hermes owning boundary: run_hermes_graph_query with FakeHost under blocker."""
    from apps.live_control_server.services.agent_runtime import (
        HERMES_RUNTIME_DESCRIPTOR,
        AgentRuntimeResult,
        AgentRuntimeToolEvent,
    )
    from apps.live_control_server.services.hermes_graph_query import run_hermes_graph_query


    class FakeHost:
        descriptor = HERMES_RUNTIME_DESCRIPTOR


        def __init__(self, result: AgentRuntimeResult) -> None:
            self._result = result
            self.calls: list[Any] = []


        def run(self, invocation: Any) -> AgentRuntimeResult:
            self.calls.append(invocation)
            return self._result


    ready_envelope = {
        "schema": "dmb_agent_world_graph_query_context_v1",
        "status": "ready",
        "world_id": "world:eldyrwild",
        "campaign_id": "campaign:c1",
        "revision_id": "revision:resolved-server",
        "head_revision_id": "revision:resolved-server",
        "is_head": True,
        "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
        "admissibility": "gm",
        "query_text": "Where is Tripod?",
        "matched_node_ids": ["threat:tripod-null-calf"],
        "nodes": [],
        "relationships": [],
        "attributes": [],
        "projection_truncated": False,
        "diagnostics": [],
        "warning_codes": [],
        "trust_boundary": {
            "graph_role": "structured_campaign_memory_and_navigation",
            "citation_authority": "corpus_source_evidence",
            "graph_citations_permitted": False,
        },
    }
    events = [
        AgentRuntimeToolEvent(
            tool_name="expand_graph_retrieval",
            state="start",
            duration_ms=1.0,
            attributes={
                "world_id": "world:eldyrwild",
                "campaign_id": "campaign:c1",
                "focus": {"kind": "session", "sessionId": "session-21"},
                "admissibility": "gm",
                "revision_pin": "revision:resolved-server",
                "bounded_ids": {},
                "retrieval_schema": "dmb_world_graph_retrieval_result_v1",
                "outcome": "enough",
                "matched_node_ids": ["threat:tripod-null-calf"],
                "relationship_ids": [],
                "source_anchor_ids": [],
                "diagnostic_codes": [],
            },
        ),
        AgentRuntimeToolEvent(
            tool_name="expand_graph_retrieval",
            state="completion",
            duration_ms=12.0,
            attributes={
                "world_id": "world:eldyrwild",
                "campaign_id": "campaign:c1",
                "focus": {"kind": "session", "sessionId": "session-21"},
                "admissibility": "gm",
                "revision_pin": "revision:resolved-server",
                "bounded_ids": {},
                "retrieval_schema": "dmb_world_graph_retrieval_result_v1",
                "outcome": "enough",
                "matched_node_ids": ["threat:tripod-null-calf"],
                "relationship_ids": [],
                "source_anchor_ids": ["anchor:a1", "anchor:a2"],
                "diagnostic_codes": [],
            },
        ),
    ]
    host = FakeHost(
        AgentRuntimeResult(
            status="ok",
            final_text="Tripod stands at the North Gate.",
            messages=[],
            runtime_session_id="hermes-sess-obs-only",
            tool_events=events,
            error_code=None,
            error_message=None,
            answer_scope=None,
            model_calls=[],
            telemetry_warnings=[],
            observed_model_call_count=None,
            context_updates={},
            runtime_metadata={"process_isolation": "process_exclusive"},
        )
    )
    root = base / "hermes-root"
    root.mkdir(parents=True, exist_ok=True)
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet={"campaign_id": "campaign:c1", "session": 22},
        graph_envelope=ready_envelope,
        agent_thread_id="agent-thread-d3a",
        turn_id="agent-turn-d3a",
        root=root,
        session_base=root / "live-session",
        agent_runtime=host,
    )
    assert len(host.calls) == 1
    assert response["mode"] == "hermes_graph_agent"
    assert response["status"] == "ok"
    assert response["grounding"]["state"] == "grounded"
    assert [c["anchor_id"] for c in response["citations"]] == ["anchor:a1", "anchor:a2"]
    _assert_no_forbidden_loaded()


def exercise_first_world_and_graph_review(client, base: Path) -> None:
    """Native first-world D_0 then D.2C4 Graph Review prepare/commit/retry under blocker."""
    from apps.live_control_server import config as live_config
    from apps.live_control_server.services.graph_authoring_overlay_projection import (
        authored_object_node_id,
    )
    from apps.live_control_server.services.graph_ingest_run_registry import (
        GRAPH_INGEST_RUNS_ENV,
    )
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from fastapi.testclient import TestClient


    dsn = require_test_dsn()
    ensure_migrated(dsn)
    truncate_dungeonmind(dsn)


    repo = base / "fw-gr-repo"
    world_root = base / "fw-gr-world"
    repo.mkdir(parents=True, exist_ok=True)
    world_root.mkdir(parents=True, exist_ok=True)


    os.environ[live_config.WORLD_GRAPH_AUTHORITY_ENV] = (
        live_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = dsn
    os.environ["DUNGEONMIND_WORLD_GRAPH_ROOT"] = str(world_root)
    os.environ["DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT"] = str(base / "_designated_live_unused")
    os.environ.pop("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", None)
    os.environ[GRAPH_INGEST_RUNS_ENV] = "out/graph_memory/runs"
    os.environ[GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV] = "d3a-owning-witness-key"


    originals = _patch_repo_root(repo)
    try:
        run_id, _source = write_glass_orchard_bld08_run(repo)
        prepare = client.post(
            FIRST_WORLD_PREPARE_URL,
            json=first_world_prepare_body(run_id, first_world_decisions()),
        )
        assert prepare.status_code == 200, prepare.text
        plan = prepare.json()
        confirm = client.post(
            FIRST_WORLD_CONFIRM_URL, json=first_world_confirm_body(plan)
        )
        assert confirm.status_code == 200, confirm.text
        d0 = confirm.json()["committedRevisionId"]
        assert d0
        glass_dir = world_root / "graph_memory" / "worlds" / GLASS_ORCHARD_WORLD_ID
        assert not glass_dir.exists()


        review_run_id = write_post_genesis_graph_review_run(repo)
        resolved = resolve_promotable_ingest_run(review_run_id, root=repo)
        buddy_artifact_id = resolved.source_artifact_id


        object_prepare = client.post(
            PREPARE_URL, json=authoring_body(review_run_id, [object_proposal()])
        )
        assert object_prepare.status_code == 200, object_prepare.text
        prepared = object_prepare.json()
        assert prepared["expressibility"] == "EXPRESSIBLE"
        assert prepared["expected_parent_revision_id"] == d0
        assert prepared["source_artifact_id"] == buddy_artifact_id


        object_commit = client.post(
            COMMIT_URL,
            json=authoring_body(
                review_run_id,
                [object_proposal()],
                confirmToken=prepared["confirm_token"],
                currentOverlayToken=prepared.get("current_overlay_token"),
            ),
        )
        assert object_commit.status_code == 200, object_commit.text
        body = object_commit.json()
        d1 = body["published_revision_id"]
        reviewed_node_id = authored_object_node_id(
            prepared["assertions_preview"][0]["assertion_id"]
        )
        assert d1 != d0
        assert body["idempotency_status"] == "published"
        assert body.get("overlay_path") is None


        retry = client.post(
            COMMIT_URL,
            json=authoring_body(
                review_run_id,
                [object_proposal()],
                confirmToken=prepared["confirm_token"],
                currentOverlayToken=prepared.get("current_overlay_token"),
            ),
        )
        assert retry.status_code == 200, retry.text
        assert retry.json()["published_revision_id"] == d1
        assert retry.json()["idempotency_status"] == "already_applied"


        # Recovery across a fresh client (lost in-memory state).
        fresh = TestClient(client.app)
        recovered = fresh.post(
            COMMIT_URL,
            json=authoring_body(
                review_run_id,
                [object_proposal()],
                confirmToken=prepared["confirm_token"],
                currentOverlayToken=prepared.get("current_overlay_token"),
            ),
        )
        assert recovered.status_code == 200, recovered.text
        assert recovered.json()["published_revision_id"] == d1
        assert recovered.json()["idempotency_status"] == "already_applied"


        from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
            DungeonMindWorldGraphAuthorityAdapter,
        )


        adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
        d1_view = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d1)
        assert reviewed_node_id in d1_view.objects
        init = adapter  # keep adapter import exercised
        del init
        assert not glass_dir.exists()
    finally:
        _restore_patches(originals)
    _assert_no_forbidden_loaded()


def exercise_all_owning_workflows(client, witness_root: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix="d3a-exec-", dir=str(witness_root)))
    exercise_threat_publish_recover(work)
    exercise_worldbuilding_publish_recover(work)
    exercise_hermes_graph_query(work)
    exercise_first_world_and_graph_review(client, work)
    _assert_no_forbidden_loaded()

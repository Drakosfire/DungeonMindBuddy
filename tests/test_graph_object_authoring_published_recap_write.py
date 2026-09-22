"""Disposable recap → governed World publication acceptance witnesses."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from apps.live_control_server.ports.world_graph_authority import (
    AuthorityObject,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
    WorldGraphRevisionView,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    AdmittedSourceIdentity,
)
from apps.live_control_server.services.graph_object_authoring_commit import (
    commit_graph_object_authoring_write,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringPrepareRequest,
    prepare_graph_object_authoring_write,
)
from apps.live_control_server.services.recap_artifacts import (
    RecapArtifactRecord,
    upsert_recap_artifact_record,
)
from graph_memory.projection.markdown_mentions import MentionBinding, project_markdown_mentions
from tests.test_graph_object_authoring_prepare import object_proposal


CAMPAIGN_ID = "longmont-c1"
WORLD_ID = "eldyrwild"
SESSION_ID = "session-2"
CAMPAIGN_REL = "Test Campaign/A5"


@dataclass
class DurableTestAuthority:
    revision_id: str = "rev:root"
    revisions: dict[str, WorldGraphRevisionView] = field(default_factory=dict)
    receipts: dict[str, WorldGraphPublicationReceipt] = field(default_factory=dict)
    publish_calls: int = 0

    def __post_init__(self) -> None:
        self.revisions[self.revision_id] = WorldGraphRevisionView(
            world_id=WORLD_ID,
            revision_id=self.revision_id,
            parent_revision_id=None,
            objects={},
            relationships={},
        )

    def current_head(self, world_id: str) -> WorldGraphHead:
        return WorldGraphHead(world_id=world_id, revision_id=self.revision_id)

    def read_revision(self, world_id: str, revision_id: str) -> WorldGraphRevisionView:
        assert world_id == WORLD_ID
        return self.revisions[revision_id]

    def recover(self, world_id: str, authority_operation_id: str, **kwargs):
        del world_id, kwargs
        return self.receipts.get(authority_operation_id)

    def publish(self, request) -> WorldGraphPublicationReceipt:
        parent = self.revisions[request.expected_parent_revision_id]
        objects = dict(parent.objects)
        for assertion in request.contribution.accepted_assertions:
            if assertion.assertion_kind != "node":
                continue
            value = assertion.value
            objects[assertion.subject_node_id] = AuthorityObject(
                object_id=assertion.subject_node_id,
                label=assertion.label or "",
                kind=str(value.get("kind") or "unknown"),
                role=str(value.get("role") or "unknown"),
                aliases=tuple(value.get("aliases") or ()),
                source_domains=tuple(value.get("source_domains") or ()),
                campaign_scope=assertion.campaign_scope,
                summary=value.get("summary"),
            )
        self.publish_calls += 1
        child_id = f"rev:{self.publish_calls}"
        child = WorldGraphRevisionView(
            world_id=WORLD_ID,
            revision_id=child_id,
            parent_revision_id=parent.revision_id,
            objects=objects,
            relationships=parent.relationships,
        )
        self.revisions[child_id] = child
        self.revision_id = child_id
        receipt = WorldGraphPublicationReceipt(
            world_id=WORLD_ID,
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=parent.revision_id,
            published_revision_id=child_id,
            reviewed_contribution_id=f"contrib:{self.publish_calls}",
            accepted_assertion_ids=tuple(
                assertion.assertion_id
                for assertion in request.contribution.accepted_assertions
            ),
            published=True,
            outcome="published",
        )
        self.receipts[request.authority_operation_id] = receipt
        return receipt


@dataclass
class RecapSourceAdmission:
    def prove_or_admit(self, request) -> AdmittedSourceIdentity:
        artifact = request.source_artifact
        assert request.world_id == WORLD_ID
        assert artifact.world_id == WORLD_ID
        return AdmittedSourceIdentity(
            source_artifact_id=artifact.source_artifact_id,
            source_revision_id=request.source_revision_token,
            content_sha256=artifact.content_sha256 or "",
            buddy_source_revision_id=request.source_revision_token,
        )

    def prove(self, *, source_artifact_id: str, source_revision_id: str, source_revision_token: str | None = None, **kwargs):
        del kwargs
        return AdmittedSourceIdentity(
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            content_sha256="",
            buddy_source_revision_id=source_revision_token or source_revision_id,
        )


def _recap_request(*, local_id: str, label: str) -> GraphObjectAuthoringPrepareRequest:
    proposal = object_proposal(
        localProposalId=local_id,
        objectRef={"label": label, "kind": "party", "aliases": [label]},
    )
    return GraphObjectAuthoringPrepareRequest.model_validate(
        {
            "campaignId": CAMPAIGN_ID,
            "campaignRel": CAMPAIGN_REL,
            "sessionId": SESSION_ID,
            "worldId": WORLD_ID,
            "recapArtifactId": f"{CAMPAIGN_ID}/{SESSION_ID}",
            "proposals": [proposal],
        }
    )


def _commit_request(prepare, request: GraphObjectAuthoringPrepareRequest):
    return GraphObjectAuthoringCommitRequest.model_validate(
        {
            **request.model_dump(by_alias=True),
            "confirmToken": prepare.confirm_token,
            "currentOverlayToken": prepare.current_overlay_token,
        }
    )


@pytest.fixture
def recap_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    recap_path = root / "recaps" / "session-2.md"
    recap_path.parent.mkdir(parents=True)
    recap_path.write_text("# Published recap\nA duplicate label appears.\n", encoding="utf-8")
    digest = hashlib.sha256(recap_path.read_bytes()).hexdigest()
    upsert_recap_artifact_record(
        root,
        RecapArtifactRecord(
            artifact_id=f"{CAMPAIGN_ID}/{SESSION_ID}",
            campaign_id=CAMPAIGN_ID,
            session_id=SESSION_ID,
            source_recap_path="recaps/session-2.md",
            run_bundle_uri="",
            run_manifest_uri="",
            source_span_index_uri="",
            source_sha256=digest,
            registered_at="1970-01-01T00:00:00Z",
            updated_at="1970-01-01T00:00:00Z",
        ),
    )
    return root


def _prepare_and_commit(
    *,
    root: Path,
    authority: DurableTestAuthority,
    local_id: str,
    label: str,
):
    request = _recap_request(local_id=local_id, label=label)
    prepare = prepare_graph_object_authoring_write(
        request,
        corpus_root=root,
        authority=authority,
        source_admission=RecapSourceAdmission(),
    )
    commit = commit_graph_object_authoring_write(
        _commit_request(prepare, request),
        corpus_root=root,
        authority=authority,
        source_admission=RecapSourceAdmission(),
    )
    return request, prepare, commit


def test_published_recap_write_reads_back_and_preserves_same_label_identity(
    recap_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "published-recap-test-key")
    authority = DurableTestAuthority()

    first_request, first_prepare, first_commit = _prepare_and_commit(
        root=recap_root,
        authority=authority,
        local_id="local-first",
        label="Duplicate object",
    )
    first_id = first_commit.created_node_ids["local-first"]
    first_revision = authority.read_revision(WORLD_ID, first_commit.published_revision_id)
    assert first_revision.objects[first_id].label == "Duplicate object"
    assert first_prepare.expected_parent_revision_id == "rev:root"
    assert first_commit.published_revision_id == "rev:1"

    second_request, second_prepare, second_commit = _prepare_and_commit(
        root=recap_root,
        authority=authority,
        local_id="local-second",
        label="Duplicate object",
    )
    second_id = second_commit.created_node_ids["local-second"]
    second_revision = authority.read_revision(WORLD_ID, second_commit.published_revision_id)
    assert second_id != first_id
    assert second_revision.objects[first_id].label == second_revision.objects[second_id].label
    assert second_request.recap_artifact_id == first_request.recap_artifact_id
    assert second_prepare.expected_parent_revision_id == "rev:1"
    assert authority.publish_calls == 2

    _, mentions, diagnostics = project_markdown_mentions(
        "Duplicate object",
        [
            MentionBinding(surface="Duplicate object", node_id=first_id),
            MentionBinding(surface="Duplicate object", node_id=second_id),
        ],
    )
    assert mentions == []
    assert any(item.code == "ambiguous_mention_surface" for item in diagnostics)


@pytest.fixture
def real_dungeonmind_recap_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
):
    """Provision a disposable real DungeonMind World for the topology witness."""
    if not os.environ.get("DMB_CUTOVER_TEST_DATABASE_URL", "").strip():
        pytest.skip("DMB_CUTOVER_TEST_DATABASE_URL is required for the PostgreSQL witness")

    from fastapi.testclient import TestClient

    import apps.live_control_server.config as live_config
    import apps.live_control_server.services.extract_promote as promote_svc
    import apps.live_control_server.services.promotable_ingest_run as promotable_mod
    from apps.live_control_server.main import create_app
    from apps.live_control_server.services.graph_ingest_run_registry import GRAPH_INGEST_RUNS_ENV
    from tests._cutover_d3a_blocker_safe_fixtures import (
        FIRST_WORLD_CONFIRM_URL,
        FIRST_WORLD_PREPARE_URL,
        TRUNCATE_SQL,
        _write_bld08_reviewable_run,
        ensure_migrated,
        first_world_confirm_body,
        first_world_decisions,
        first_world_prepare_body,
        require_test_dsn,
    )
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    dsn = require_test_dsn()
    ensure_migrated(dsn)
    with PostgresDatabase(dsn).connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()

    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn)
    monkeypatch.setenv(live_config.WORLD_GRAPH_AUTHORITY_ENV, live_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setenv("DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT", str(tmp_path / "_unused_live_root"))
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "published-recap-real-witness-key")
    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)

    from apps.live_control_server.services.world_container_registry import create_world_container

    create_world_container(repo, name="Eldyrwild")
    client = TestClient(create_app())
    run_id, _ = _write_bld08_reviewable_run(
        repo,
        campaign_id=WORLD_ID,
        world_id=WORLD_ID,
    )
    first_prepare = client.post(
        FIRST_WORLD_PREPARE_URL,
        json=first_world_prepare_body(run_id, first_world_decisions()),
    )
    assert first_prepare.status_code == 200, first_prepare.text
    first_confirm = client.post(
        FIRST_WORLD_CONFIRM_URL,
        json=first_world_confirm_body(first_prepare.json()),
    )
    assert first_confirm.status_code == 200, first_confirm.text
    return repo, dsn


@pytest.mark.integration
def test_published_recap_write_uses_setting_world_for_campaign_scope(
    real_dungeonmind_recap_authority,
) -> None:
    """Prove the real authority receives eldyrwild for a Longmont C1 recap."""
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )

    repo, dsn = real_dungeonmind_recap_authority
    recap_path = repo / "recaps" / "session-2.md"
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text("# C1 Session 2\nEphanna is present.\n", encoding="utf-8")
    digest = hashlib.sha256(recap_path.read_bytes()).hexdigest()
    upsert_recap_artifact_record(
        repo,
        RecapArtifactRecord(
            artifact_id=f"{CAMPAIGN_ID}/{SESSION_ID}",
            campaign_id=CAMPAIGN_ID,
            session_id=SESSION_ID,
            source_recap_path="recaps/session-2.md",
            run_bundle_uri="",
            run_manifest_uri="",
            source_span_index_uri="",
            source_sha256=digest,
            registered_at="1970-01-01T00:00:00Z",
            updated_at="1970-01-01T00:00:00Z",
        ),
    )

    authority = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    source_admission = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn)
    request = _recap_request(local_id="real-world-id", label="C1 durable witness")
    prepare = prepare_graph_object_authoring_write(
        request,
        corpus_root=repo,
        authority=authority,
        source_admission=source_admission,
    )
    assert prepare.world_id == WORLD_ID
    assert prepare.campaign_id == CAMPAIGN_ID

    commit = commit_graph_object_authoring_write(
        _commit_request(prepare, request),
        corpus_root=repo,
        authority=authority,
        source_admission=source_admission,
    )
    assert commit.committed is True
    assert commit.world_id == WORLD_ID
    assert commit.published_revision_id
    node_id = commit.created_node_ids["real-world-id"]
    revision = authority.read_revision(WORLD_ID, commit.published_revision_id)
    assert revision.world_id == WORLD_ID
    assert revision.objects[node_id].label == "C1 durable witness"
    assert authority.current_head(WORLD_ID).revision_id == commit.published_revision_id

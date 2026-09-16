"""Governed recap writes must admit snapshot-provable source provenance."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    _map_contribution_evidence_ref,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
    DungeonMindWorldGraphSourceAdmissionAdapter,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    _EmptyEvidenceView,
    _recap_extraction_evidence_view,
    bind_identity_ledger_to_package,
)
from apps.live_control_server.models.candidate_graph_admission import (
    CandidateAdmissionIntegrityError,
    CandidateAdmissionNotConfirmableError,
)
from apps.live_control_server.models.world_graph_mutation_context import (
    WorldGraphMutationContext,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    AdmittedSourceIdentity,
    WorldGraphSourceAdmissionError,
)
from apps.live_control_server.services.candidate_graph_admission import (
    confirm_candidate_graph_admission,
    prepare_candidate_graph_admission,
)
from dungeonmind.contracts.evidence import SourceDomain
from dungeonmind.infrastructure.memory.repositories import InMemorySourceRepository
from tests.test_candidate_graph_admission_contract import _candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ID = "artifact:recap:longmont-c2:session-9"
WORLD_ID = "world:recap-provenance"
CAMPAIGN_ID = "longmont-c2"

pytest_plugins = ("tests.application_state.conftest",)


@dataclass
class RecordingAdmission:
    sources: InMemorySourceRepository = field(default_factory=InMemorySourceRepository)
    calls: list[str] = field(default_factory=list)
    fail_code: str | None = None

    def _adapter(self) -> DungeonMindWorldGraphSourceAdmissionAdapter:
        return DungeonMindWorldGraphSourceAdmissionAdapter(sources=self.sources)

    def prove_or_admit(self, request) -> AdmittedSourceIdentity:
        self.calls.append("prove_or_admit")
        if self.fail_code:
            raise WorldGraphSourceAdmissionError(
                "injected source admission failure",
                code=self.fail_code,  # type: ignore[arg-type]
            )
        return self._adapter().prove_or_admit(request)

    def prove(
        self,
        *,
        world_id: str,
        source_artifact_id: str,
        source_revision_id: str,
        source_revision_token: str | None = None,
    ) -> AdmittedSourceIdentity:
        self.calls.append("prove")
        if self.fail_code:
            raise WorldGraphSourceAdmissionError(
                "injected source proof failure",
                code=self.fail_code,  # type: ignore[arg-type]
            )
        return self._adapter().prove(
            world_id=world_id,
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            source_revision_token=source_revision_token,
        )


def _source_file(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "session-9.md"
    source.write_text("Brin visits the Medical Wing.\n", encoding="utf-8")
    revision = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    return source, revision


def _prepare(
    tmp_path: Path,
    *,
    source_admission: Any | None,
    campaign_scope: str = CAMPAIGN_ID,
    source_revision_id: str | None = None,
    candidate: dict | None = None,
    mutation_context: WorldGraphMutationContext | None = None,
):
    source, revision = _source_file(tmp_path)
    context = mutation_context or WorldGraphMutationContext(
        world_id=WORLD_ID,
        revision_id="rev:d0",
        head_revision_id="rev:d0",
        objects={},
    )
    return prepare_candidate_graph_admission(
        candidate_graph=candidate or _candidate(),
        source_uri=str(source),
        source_revision_id=source_revision_id or revision,
        prepared_by="gm@test",
        world_id=WORLD_ID,
        source_artifact_id=ARTIFACT_ID,
        campaign_scope=campaign_scope,
        candidate_graph_path=str(tmp_path / "candidate_graph.json"),
        repo_root=tmp_path,
        mutation_context=context,
        source_admission=source_admission,
    )


def test_confirmable_prepare_requires_source_admission(tmp_path: Path) -> None:
    admission = RecordingAdmission(fail_code="source_not_admitted")
    with pytest.raises(CandidateAdmissionNotConfirmableError):
        _prepare(tmp_path, source_admission=admission)
    assert admission.calls == ["prove_or_admit"]


def test_successful_prepare_admits_snapshot_provable_pair(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    result = _prepare(tmp_path, source_admission=admission)
    assert result.confirmable is True
    sealed = result.review_package["effect"]["source_admission"]
    assert sealed["source_artifact_id"] == ARTIFACT_ID
    assert sealed["buddy_source_revision_id"].startswith("sha256:")
    snapshot = admission.sources.get_provenance_snapshot(
        artifact_ids=[sealed["source_artifact_id"]],
        revision_ids=[sealed["source_revision_id"]],
    )
    assert snapshot.get_artifact(sealed["source_artifact_id"]) is not None
    assert snapshot.get_revision(sealed["source_revision_id"]) is not None
    admitted_artifact = snapshot.get_artifact(sealed["source_artifact_id"])
    assert str(getattr(admitted_artifact, "source_domain_key", "")) == "session_recap"
    assert admitted_artifact.source_domain == SourceDomain.SESSION_RECAP
    assert admission.calls == ["prove_or_admit"]


def test_nonconfirmable_prepare_does_not_admit(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    candidate = _candidate()
    candidate["nodes"] = []
    candidate["edges"] = []
    result = _prepare(tmp_path, source_admission=admission, candidate=candidate)
    assert result.confirmable is False
    assert "source_admission" not in result.review_package["effect"]
    assert admission.calls == []


def test_foreign_campaign_fails_before_admission(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    artifact = SimpleNamespace(
        source_artifact_id=ARTIFACT_ID,
        source_domain="recap",
        campaign_id="foreign-campaign",
        session_id="session-9",
        uri="file://session-9.md",
        content_sha256="ab" * 32,
        artifact_kind="markdown",
        document_class="recap",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=WORLD_ID,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )
    source, revision = _source_file(tmp_path)
    with pytest.raises(CandidateAdmissionNotConfirmableError, match="different campaign"):
        prepare_candidate_graph_admission(
            candidate_graph=_candidate(),
            source_uri=str(source),
            source_revision_id=revision,
            prepared_by="gm@test",
            world_id=WORLD_ID,
            source_artifact_id=ARTIFACT_ID,
            source_artifact=artifact,
            campaign_scope=CAMPAIGN_ID,
            candidate_graph_path=str(tmp_path / "candidate_graph.json"),
            repo_root=tmp_path,
            mutation_context=WorldGraphMutationContext(
                world_id=WORLD_ID,
                revision_id="rev:d0",
                head_revision_id="rev:d0",
                objects={},
            ),
            source_admission=admission,
        )
    assert admission.calls == []


def test_fingerprint_conflict_fails_closed(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    first = _prepare(tmp_path, source_admission=admission)
    sealed = first.review_package["effect"]["source_admission"]
    other = tmp_path / "other.md"
    other.write_text("Different recap bytes.\n", encoding="utf-8")
    other_revision = f"sha256:{hashlib.sha256(other.read_bytes()).hexdigest()}"
    colliding = SimpleNamespace(
        source_artifact_id=ARTIFACT_ID,
        source_domain="recap",
        campaign_id=CAMPAIGN_ID,
        session_id="session-9",
        uri=str(other),
        content_sha256=other_revision.removeprefix("sha256:"),
        artifact_kind="markdown",
        document_class="recap",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=WORLD_ID,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )
    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        prepare_candidate_graph_admission(
            candidate_graph=_candidate(),
            source_uri=str(other),
            source_revision_id=other_revision,
            prepared_by="gm@test",
            world_id=WORLD_ID,
            source_artifact_id=ARTIFACT_ID,
            source_artifact=colliding,
            campaign_scope=CAMPAIGN_ID,
            candidate_graph_path=str(tmp_path / "candidate_graph.json"),
            repo_root=tmp_path,
            mutation_context=WorldGraphMutationContext(
                world_id=WORLD_ID,
                revision_id="rev:d0",
                head_revision_id="rev:d0",
                objects={},
            ),
            source_admission=admission,
        )
    assert [item.code for item in excinfo.value.diagnostics] == ["source_identity_conflict"]
    still = admission.sources.get_provenance_snapshot(
        artifact_ids=[sealed["source_artifact_id"]],
        revision_ids=[sealed["source_revision_id"]],
    )
    assert still.get_revision(sealed["source_revision_id"]) is not None


def test_confirm_rejects_missing_sealed_source_admission(tmp_path: Path) -> None:
    from graph_memory.extract_promote_proposal import compute_proposal_digest

    admission = RecordingAdmission()
    result = _prepare(tmp_path, source_admission=admission)
    package = dict(result.review_package)
    effect = dict(package["effect"])
    effect.pop("source_admission")
    package["effect"] = effect
    package["proposal_digest"] = compute_proposal_digest(effect)
    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        confirm_candidate_graph_admission(
            review_package=package,
            candidate_graph=_candidate(),
            governed_confirm=lambda: "nope",
        )
    assert [item.code for item in excinfo.value.diagnostics] == ["source_admission_missing"]


def test_recap_evidence_view_maps_session_recap_not_other() -> None:
    token = "sha256:" + ("ab" * 32)
    contribution = SimpleNamespace(
        accepted_assertions=[
            SimpleNamespace(
                source_artifact_id=ARTIFACT_ID,
                source_revision_id=token,
                evidence_ref_ids=["ev:mireward"],
            )
        ],
        candidate_assertions=[],
        rejected_assertions=[],
    )
    empty = _map_contribution_evidence_ref(
        _EmptyEvidenceView(),
        "ev:mireward",
        fallback_source_artifact_id=ARTIFACT_ID,
        source_revision_id=token,
    )
    assert empty.source_domain == SourceDomain.OTHER
    recap_view = _recap_extraction_evidence_view(
        contribution,
        pair_to_dm={(ARTIFACT_ID, token): token},
    )
    recap = _map_contribution_evidence_ref(
        recap_view,
        "ev:mireward",
        fallback_source_artifact_id=ARTIFACT_ID,
        source_revision_id=token,
    )
    assert recap.source_domain == SourceDomain.SESSION_RECAP
    assert recap.source_artifact_id == ARTIFACT_ID


def test_unknown_object_id_is_not_prefix_guessed(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    result = _prepare(tmp_path, source_admission=admission)
    snapshot = admission.sources.get_provenance_snapshot(
        artifact_ids=["artifact:recap:unknown"],
        revision_ids=["sha256:" + ("cd" * 32)],
    )
    assert snapshot.get_artifact("artifact:recap:unknown") is None
    assert result.confirmable is True


@pytest.mark.integration
def test_fresh_recap_publication_survives_native_scoped_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        build_direct_world_graph_read_services,
        get_evidence_direct,
        get_neighborhood_direct,
        get_object_direct,
        project_world_graph_direct,
        search_world_graph_direct,
    )
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from graph_memory.projection.world_projection import WorldGraphProjectionRequest
    from graph_memory.retrieval.models import (
        RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
        RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
        RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        RETRIEVAL_SEARCH_REQUEST_SCHEMA,
        WorldGraphEvidenceRequest,
        WorldGraphNeighborhoodRequest,
        WorldGraphObjectRequest,
        WorldGraphSearchRequest,
    )
    from apps.live_control_server.ports.world_graph_authority import WorldGraphPublishRequest
    from apps.live_control_server.services.recap_world_genesis import (
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
    from tests._cutover_d3a_blocker_safe_fixtures import (
        TRUNCATE_SQL,
        ensure_migrated,
        require_test_dsn,
    )
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn
    )
    dsn = require_test_dsn()
    ensure_migrated(dsn)
    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()

    from apps.live_control_server import config as wg_config

    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    monkeypatch.setenv(
        wg_config.WORLD_GRAPH_AUTHORITY_ENV,
        wg_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))

    registry = repo / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
    registry.parent.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json",
        registry,
    )
    world_id = "world:recap-provenance-pg"
    genesis_authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
    genesis_plan = prepare_recap_world_genesis(
        RecapWorldGenesisPrepareRequest(
            world_id=world_id,
            campaign_id="longmont-c1",
            baseline_roster_key="1",
            requested_by="recap-provenance-test",
        ),
        repo=repo,
        authority=genesis_authority,
    )
    genesis = confirm_recap_world_genesis(
        RecapWorldGenesisConfirmRequest(
            plan=genesis_plan, confirming_principal="recap-provenance-test"
        ),
        repo=repo,
        authority=genesis_authority,
    )
    d0 = genesis.published_revision_id
    source = repo / "session-9.md"
    source.write_text("Brin visits the Medical Wing.\n", encoding="utf-8")
    source_revision = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    graph_authority = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    context = graph_authority.mutation_context(world_id, d0)
    result = prepare_candidate_graph_admission(
        candidate_graph=_candidate(),
        source_uri=str(source),
        source_revision_id=source_revision,
        prepared_by="recap-provenance-test",
        world_id=world_id,
        source_artifact_id=ARTIFACT_ID,
        campaign_scope=CAMPAIGN_ID,
        repo_root=repo,
        mutation_context=context,
        candidate_graph_path=str(tmp_path / "candidate_graph.json"),
    )
    assert result.confirmable is True
    assert graph_authority.current_head(world_id).revision_id == d0
    sealed = result.review_package["effect"]["source_admission"]
    services = build_direct_world_graph_read_services(dsn, world_id)
    assert services.bundle.sources.get_artifact(sealed["source_artifact_id"]) is not None
    assert services.bundle.sources.get_revision(sealed["source_revision_id"]) is not None
    package = bind_identity_ledger_to_package(result.review_package, context)
    _verified, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal="recap-provenance-test",
        world_id_hint=world_id,
        expected_parent_revision_id=context.revision_id,
        assertion_ids=None,
        mutation_context=context,
        verify_source=True,
        repo_root=repo,
    )
    published = confirm_candidate_graph_admission(
        review_package=package,
        candidate_graph=_candidate(),
        governed_confirm=lambda: graph_authority.publish(
            WorldGraphPublishRequest(
                world_id=world_id,
                expected_parent_revision_id=context.revision_id,
                authority_operation_id=contribution.contribution_id,
                actor="recap-provenance-test",
                contribution=contribution,
                accepted_assertion_ids=tuple(
                    item.assertion_id for item in contribution.accepted_assertions
                ),
                decision="create_new",
                threat_node_id="candidate:brin",
                operation_namespace="threat",
            )
        ),
    )
    child = published.published_revision_id
    assert child != d0
    retry = confirm_candidate_graph_admission(
        review_package=package,
        candidate_graph=_candidate(),
        governed_confirm=lambda: graph_authority.publish(
            WorldGraphPublishRequest(
                world_id=world_id,
                expected_parent_revision_id=context.revision_id,
                authority_operation_id=contribution.contribution_id,
                actor="recap-provenance-test",
                contribution=contribution,
                accepted_assertion_ids=tuple(
                    item.assertion_id for item in contribution.accepted_assertions
                ),
                decision="create_new",
                threat_node_id="candidate:brin",
                operation_namespace="threat",
            )
        ),
    )
    assert retry.published_revision_id == child
    assert graph_authority.current_head(world_id).revision_id == child

    services = build_direct_world_graph_read_services(dsn, world_id)
    child_view = graph_authority.read_revision(world_id, child)
    assert "candidate:brin" in child_view.objects
    projection = project_world_graph_direct(
        services,
        WorldGraphProjectionRequest(
            schema_="dmb_world_graph_projection_request_v1",
            world_id=world_id,
            campaign_id=CAMPAIGN_ID,
            revision_pin=child,
            scope_mode="world",
        ),
    )
    node_ids = [item.node_id for item in projection.nodes]
    assert "candidate:brin" in node_ids
    found = get_object_direct(
        services,
        WorldGraphObjectRequest.model_validate(
            {
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": CAMPAIGN_ID,
                "revisionPin": child,
                "scopeMode": "world",
                "nodeId": "candidate:brin",
            }
        ),
    )
    assert found.outcome != "empty"
    assert found.resolved_node_id == "candidate:brin"
    search = search_world_graph_direct(
        services,
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": CAMPAIGN_ID,
                "revisionPin": child,
                "scopeMode": "world",
                "queryText": "Brin",
            }
        ),
    )
    assert "candidate:brin" in search.matched_node_ids
    neighborhood = get_neighborhood_direct(
        services,
        WorldGraphNeighborhoodRequest.model_validate(
            {
                "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": CAMPAIGN_ID,
                "revisionPin": child,
                "scopeMode": "world",
                "seedNodeIds": ["candidate:brin"],
            }
        ),
    )
    assert neighborhood.outcome != "empty"
    assert "candidate:brin" in [item.node_id for item in neighborhood.nodes]
    evidence = get_evidence_direct(
        services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": CAMPAIGN_ID,
                "revisionPin": child,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "candidate:brin"},
            }
        ),
    )
    assert evidence.outcome != "empty"
    recap_domain = SourceDomain.SESSION_RECAP.value
    assert recap_domain in {anchor.source_domain for anchor in evidence.source_anchors}
    missing = get_object_direct(
        services,
        WorldGraphObjectRequest.model_validate(
            {
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": CAMPAIGN_ID,
                "revisionPin": child,
                "scopeMode": "world",
                "nodeId": "node:location:unknown-mireward",
            }
        ),
    )
    assert missing.outcome == "empty"

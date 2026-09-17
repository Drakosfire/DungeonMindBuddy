"""Governed recap writes must admit snapshot-provable source provenance."""

from __future__ import annotations

import copy
import hashlib
import json
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
    catalog_aware_source_revision_ids,
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


def _candidate_bound_to(artifact_id: str) -> dict:
    candidate = copy.deepcopy(_candidate())
    candidate["source_artifact_ids"] = [artifact_id]
    for node in candidate.get("nodes") or []:
        for ref in node.get("evidence_refs") or []:
            ref["source_artifact_id"] = artifact_id
    for edge in candidate.get("edges") or []:
        for ref in edge.get("evidence_refs") or []:
            ref["source_artifact_id"] = artifact_id
    return candidate


def _source_file(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "session-9.md"
    source.write_text("Brin visits the Medical Wing.\n", encoding="utf-8")
    revision = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    return source, revision


def _artifact(
    *,
    uri: str,
    content_sha256: str,
    source_artifact_id: str = ARTIFACT_ID,
    source_domain: str = "recap",
    campaign_id: str = CAMPAIGN_ID,
    session_id: str = "session-9",
    world_id: str = WORLD_ID,
) -> SimpleNamespace:
    recap_family = source_domain in {"recap", "session_recap"}
    return SimpleNamespace(
        source_artifact_id=source_artifact_id,
        source_domain=source_domain,
        campaign_id=campaign_id,
        session_id=session_id,
        uri=uri,
        content_sha256=content_sha256,
        artifact_kind="markdown",
        document_class="recap" if recap_family else source_domain,
        authority_state="reviewed",
        visibility_state="internal",
        world_id=world_id,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


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
    token = source_revision_id or revision
    artifact = _artifact(
        uri=str(source),
        content_sha256=token.removeprefix("sha256:"),
    )
    context = mutation_context or WorldGraphMutationContext(
        world_id=WORLD_ID,
        revision_id="rev:d0",
        head_revision_id="rev:d0",
        objects={},
    )
    return prepare_candidate_graph_admission(
        candidate_graph=candidate or _candidate(),
        source_uri=str(source),
        source_revision_id=token,
        prepared_by="gm@test",
        world_id=WORLD_ID,
        source_artifact_id=ARTIFACT_ID,
        source_artifact=artifact,
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


def test_confirmable_prepare_requires_canonical_source_artifact(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    source, revision = _source_file(tmp_path)
    with pytest.raises(
        CandidateAdmissionNotConfirmableError,
        match="canonical source artifact",
    ):
        prepare_candidate_graph_admission(
            candidate_graph=_candidate(),
            source_uri=str(source),
            source_revision_id=revision,
            prepared_by="gm@test",
            world_id=WORLD_ID,
            source_artifact_id=ARTIFACT_ID,
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
    assert admission.calls == ["prove_or_admit", "prove_or_admit"]
    still = admission.sources.get_provenance_snapshot(
        artifact_ids=[sealed["source_artifact_id"]],
        revision_ids=[sealed["source_revision_id"]],
    )
    assert still.get_revision(sealed["source_revision_id"]) is not None


def test_same_token_divergent_artifact_fingerprint_fails_closed(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    first = _prepare(tmp_path, source_admission=admission)
    sealed = first.review_package["effect"]["source_admission"]
    token = sealed["buddy_source_revision_id"]
    relocated = tmp_path / "relocated-session-9.md"
    relocated.write_text((tmp_path / "session-9.md").read_text(encoding="utf-8"), encoding="utf-8")
    colliding = _artifact(
        uri=str(relocated),
        content_sha256=token.removeprefix("sha256:"),
    )
    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        prepare_candidate_graph_admission(
            candidate_graph=_candidate(),
            source_uri=str(relocated),
            source_revision_id=token,
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
    assert admission.calls == ["prove_or_admit", "prove_or_admit"]
    still = admission.sources.get_provenance_snapshot(
        artifact_ids=[sealed["source_artifact_id"]],
        revision_ids=[sealed["source_revision_id"]],
    )
    stored = still.get_artifact(sealed["source_artifact_id"])
    assert stored is not None
    assert str(stored.uri) != str(relocated)


def test_non_recap_source_domain_rejected_before_admission(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    source, revision = _source_file(tmp_path)
    artifact = _artifact(
        uri=str(source),
        content_sha256=revision.removeprefix("sha256:"),
        source_domain="worldbuilding",
    )
    with pytest.raises(
        CandidateAdmissionNotConfirmableError,
        match="recap source artifact",
    ):
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
    snapshot = admission.sources.get_provenance_snapshot(
        artifact_ids=[ARTIFACT_ID],
        revision_ids=[revision],
    )
    assert snapshot.get_artifact(ARTIFACT_ID) is None


def test_same_token_different_artifacts_collision_safe_through_prepare(
    tmp_path: Path,
) -> None:
    admission = RecordingAdmission()
    first = _prepare(tmp_path, source_admission=admission)
    token = first.review_package["effect"]["source_admission"]["buddy_source_revision_id"]
    first_dm = first.review_package["effect"]["source_admission"]["source_revision_id"]
    other_id = "artifact:recap:longmont-c2:session-9-copy"
    source = tmp_path / "session-9.md"
    other = _artifact(
        uri=str(source),
        content_sha256=token.removeprefix("sha256:"),
        source_artifact_id=other_id,
        source_domain="session_recap",
    )
    second = prepare_candidate_graph_admission(
        candidate_graph=_candidate_bound_to(other_id),
        source_uri=str(source),
        source_revision_id=token,
        prepared_by="gm@test",
        world_id=WORLD_ID,
        source_artifact_id=other_id,
        source_artifact=other,
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
    second_dm = second.review_package["effect"]["source_admission"]["source_revision_id"]
    assert first_dm == token
    assert second_dm == f"{token}::{other_id}"
    mapped = catalog_aware_source_revision_ids(
        admission.sources,
        WORLD_ID,
        {(ARTIFACT_ID, token), (other_id, token)},
    )
    assert mapped[(ARTIFACT_ID, token)] == first_dm
    assert mapped[(other_id, token)] == second_dm
    snapshot = admission.sources.get_provenance_snapshot(
        artifact_ids=[ARTIFACT_ID, other_id],
        revision_ids=[first_dm, second_dm],
    )
    assert snapshot.get_revision(first_dm) is not None
    assert snapshot.get_revision(second_dm) is not None


@pytest.mark.parametrize("graph_review_first", [True, False])
def test_graph_review_and_candidate_admission_share_recap_fingerprint(
    tmp_path: Path, graph_review_first: bool
) -> None:
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        prove_or_admit_graph_review_source,
    )

    admission = RecordingAdmission()
    source, revision = _source_file(tmp_path)
    recap = _artifact(
        uri=str(source),
        content_sha256=revision.removeprefix("sha256:"),
        source_domain="recap",
    )
    resolved = SimpleNamespace(
        source_artifact=recap,
        source_artifact_id=ARTIFACT_ID,
        source_revision_id=revision,
        sealed_source_uri=str(source),
    )

    def via_graph_review() -> tuple[str, str]:
        return prove_or_admit_graph_review_source(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            resolved_source=resolved,
            source_admission=admission,
        )

    def via_candidate() -> tuple[str, str]:
        result = prepare_candidate_graph_admission(
            candidate_graph=_candidate(),
            source_uri=str(source),
            source_revision_id=revision,
            prepared_by="gm@test",
            world_id=WORLD_ID,
            source_artifact_id=ARTIFACT_ID,
            source_artifact=recap,
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
        sealed = result.review_package["effect"]["source_admission"]
        return sealed["source_artifact_id"], sealed["source_revision_id"]

    first, second = (
        (via_graph_review, via_candidate)
        if graph_review_first
        else (via_candidate, via_graph_review)
    )
    first_id, first_rev = first()
    second_id, second_rev = second()
    assert (first_id, first_rev) == (second_id, second_rev)
    snapshot = admission.sources.get_provenance_snapshot(
        artifact_ids=[first_id],
        revision_ids=[first_rev],
    )
    stored = snapshot.get_artifact(first_id)
    assert stored is not None
    assert str(stored.source_domain_key) == "session_recap"
    assert stored.source_domain == SourceDomain.SESSION_RECAP
    assert admission.calls == ["prove_or_admit", "prove_or_admit"]


def test_product_prepare_fails_closed_when_canonical_source_artifact_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.models.extract_promote import (
        ExtractPromotePrepareRequest,
    )
    from apps.live_control_server.services import extract_promote as extract_promote_service
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
    )

    source, revision = _source_file(tmp_path)
    candidate_path = tmp_path / "candidate_graph.json"
    candidate_path.write_text(json.dumps(_candidate()), encoding="utf-8")
    resolved = SimpleNamespace(
        run_id="run:missing-source",
        campaign_id=CAMPAIGN_ID,
        session_id="session-9",
        status="ready",
        extraction_profile="current_default",
        source_artifact_id=ARTIFACT_ID,
        source_revision_id=revision,
        normalized_recap_path=source,
        candidate_graph_path=candidate_path,
        preview_union_store_path=tmp_path / "union.json",
        manifest_path=tmp_path / "manifest.json",
        run_dir=tmp_path,
        registry_root=tmp_path,
        sealed_source_uri=str(source),
        registry_context_graph_path=None,
        diagnostics=[],
        source_domain="recap",
        world_id=WORLD_ID,
        source_span_index_path=None,
    )
    monkeypatch.setattr(
        extract_promote_service,
        "resolve_promotable_ingest_run",
        lambda *_args, **_kwargs: resolved,
    )
    monkeypatch.setattr(
        extract_promote_service,
        "assert_sealed_source_uri_allowed",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.source_artifact_registry.get_source_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SourceArtifactRegistryError(f"source artifact not found: {ARTIFACT_ID}")
        ),
    )
    with pytest.raises(ExtractPromoteError) as excinfo:
        extract_promote_service.prepare(ExtractPromotePrepareRequest(run_id="run:missing-source"))
    assert excinfo.value.code == "invalid_request"
    assert "source_artifact_missing" in {item.code for item in excinfo.value.diagnostics}


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


def test_confirm_skips_write_when_sealed_source_goes_missing(tmp_path: Path) -> None:
    admission = RecordingAdmission()
    result = _prepare(tmp_path, source_admission=admission)
    published = {"ran": False}
    admission.fail_code = "source_not_admitted"
    with pytest.raises(CandidateAdmissionNotConfirmableError):
        confirm_candidate_graph_admission(
            review_package=result.review_package,
            candidate_graph=_candidate(),
            source_admission=admission,
            governed_confirm=lambda: published.__setitem__("ran", True) or "published",
        )
    assert published["ran"] is False
    assert admission.calls[-1] == "prove"
    sealed = result.review_package["effect"]["source_admission"]
    still = admission.sources.get_provenance_snapshot(
        artifact_ids=[sealed["source_artifact_id"]],
        revision_ids=[sealed["source_revision_id"]],
    )
    assert still.get_revision(sealed["source_revision_id"]) is not None


def test_confirm_skips_write_when_sealed_source_fingerprint_drifts(
    tmp_path: Path,
) -> None:
    admission = RecordingAdmission()
    result = _prepare(tmp_path, source_admission=admission)
    sealed = result.review_package["effect"]["source_admission"]
    stored = admission.sources.get_revision(sealed["source_revision_id"])
    assert stored is not None
    admission.sources._revisions[sealed["source_revision_id"]] = stored.model_copy(
        update={"content_sha256": "00" * 32}
    )
    published = {"ran": False}
    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        confirm_candidate_graph_admission(
            review_package=result.review_package,
            candidate_graph=_candidate(),
            source_admission=admission,
            governed_confirm=lambda: published.__setitem__("ran", True) or "published",
        )
    assert [item.code for item in excinfo.value.diagnostics] == ["source_identity_conflict"]
    assert published["ran"] is False
    assert admission.calls[-1] == "prove"


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


def _prepared_native_recap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
):
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from apps.live_control_server.services.recap_world_genesis import (
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )
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
    candidate = _candidate()
    candidate_path = tmp_path / "candidate_graph.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    recap = _artifact(
        uri=str(source),
        content_sha256=source_revision.removeprefix("sha256:"),
        world_id=world_id,
    )
    result = prepare_candidate_graph_admission(
        candidate_graph=candidate,
        source_uri=str(source),
        source_revision_id=source_revision,
        prepared_by="recap-provenance-test",
        world_id=world_id,
        source_artifact_id=ARTIFACT_ID,
        source_artifact=recap,
        campaign_scope=CAMPAIGN_ID,
        repo_root=repo,
        mutation_context=context,
        candidate_graph_path=str(candidate_path),
        source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn),
    )
    package = bind_identity_ledger_to_package(result.review_package, context)
    return SimpleNamespace(
        dsn=dsn,
        database=database,
        world_id=world_id,
        d0=d0,
        repo=repo,
        graph_authority=graph_authority,
        context=context,
        candidate=candidate,
        candidate_path=candidate_path,
        result=result,
        package=package,
    )


def _confirm_via_product_seam(prepared) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        confirm_extract_promote_via_dungeonmind,
    )
    from apps.live_control_server.models.extract_promote import (
        ExtractPromoteConfirmRequest,
    )

    assertion_ids = [
        str(item["assertion_id"])
        for item in (prepared.package.get("effect") or {}).get("accepted_proposals")
        or []
        if item.get("assertion_id")
    ]
    request = ExtractPromoteConfirmRequest(
        review_package=prepared.package,
        assertion_ids=assertion_ids,
    )
    return confirm_candidate_graph_admission(
        review_package=prepared.package,
        candidate_graph=prepared.candidate,
        source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(
            database_url=prepared.dsn
        ),
        governed_confirm=lambda: confirm_extract_promote_via_dungeonmind(
            request,
            database_url=prepared.dsn,
            confirming_principal="recap-provenance-test",
            assertion_ids=tuple(assertion_ids),
            repo_root=prepared.repo,
        ),
    )


@pytest.mark.integration
def test_fresh_recap_publication_survives_native_scoped_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        build_direct_world_graph_read_services,
        get_evidence_direct,
        get_neighborhood_direct,
        get_object_direct,
        project_world_graph_direct,
        search_world_graph_direct,
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

    prepared = _prepared_native_recap(tmp_path, monkeypatch, application_state_dsn)
    result = prepared.result
    world_id = prepared.world_id
    d0 = prepared.d0
    dsn = prepared.dsn
    graph_authority = prepared.graph_authority
    assert result.confirmable is True
    assert graph_authority.current_head(world_id).revision_id == d0
    sealed = result.review_package["effect"]["source_admission"]
    services = build_direct_world_graph_read_services(dsn, world_id)
    assert services.bundle.sources.get_artifact(sealed["source_artifact_id"]) is not None
    assert services.bundle.sources.get_revision(sealed["source_revision_id"]) is not None

    published = _confirm_via_product_seam(prepared)
    child = published["committed_revision_id"]
    assert child != d0
    retry = _confirm_via_product_seam(prepared)
    assert retry["committed_revision_id"] == child
    assert retry["outcome"] == "already_applied"
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


@pytest.mark.integration
def test_confirm_fails_closed_when_admitted_source_disappears(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    import psycopg

    prepared = _prepared_native_recap(tmp_path, monkeypatch, application_state_dsn)
    sealed = prepared.result.review_package["effect"]["source_admission"]
    artifact_id = sealed["source_artifact_id"]
    with psycopg.connect(prepared.dsn) as conn:
        conn.execute(
            "DELETE FROM dungeonmind.source_revisions WHERE source_artifact_id = %s",
            (artifact_id,),
        )
        conn.execute(
            "DELETE FROM dungeonmind.source_artifacts WHERE source_artifact_id = %s",
            (artifact_id,),
        )
        conn.commit()
    with pytest.raises(CandidateAdmissionNotConfirmableError):
        _confirm_via_product_seam(prepared)
    assert prepared.graph_authority.current_head(prepared.world_id).revision_id == prepared.d0


@pytest.mark.integration
def test_confirm_fails_closed_when_admitted_source_fingerprint_drifts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    import psycopg

    prepared = _prepared_native_recap(tmp_path, monkeypatch, application_state_dsn)
    sealed = prepared.result.review_package["effect"]["source_admission"]
    with psycopg.connect(prepared.dsn) as conn:
        conn.execute(
            "UPDATE dungeonmind.source_revisions SET content_sha256 = %s "
            "WHERE source_revision_id = %s",
            ("00" * 32, sealed["source_revision_id"]),
        )
        conn.commit()
    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        _confirm_via_product_seam(prepared)
    assert [item.code for item in excinfo.value.diagnostics] == ["source_identity_conflict"]
    assert prepared.graph_authority.current_head(prepared.world_id).revision_id == prepared.d0

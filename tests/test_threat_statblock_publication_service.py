from __future__ import annotations

import threading
import uuid
from pathlib import Path

import graph_memory.kernel as kernel
import pytest

from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    PROVIDER_DUNGEONMIND,
    same_mechanics_locator,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptedMechanicsRefV1,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.models.threat_statblock_publication import (
    BeginThreatStatblockPublicationRequestV1,
    CancelThreatStatblockPublicationRequestV1,
    ReconcileThreatStatblockPublicationRequestV1,
)
from apps.live_control_server.services.threat_draft_store import (
    attach_accepted_mechanics_ref,
    create_threat_draft,
    get_threat_draft,
    threat_drafts_root,
    update_threat_draft,
)
from apps.live_control_server.services.threat_statblock_publication import (
    ThreatStatblockPublicationError,
    begin_or_resume_publication_operation,
    cancel_publication_operation,
    read_publication_operation,
    reconcile_publication_operation,
)
from apps.live_control_server.services.threat_statblock_publication_store import (
    publication_root,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPO_ROOT / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
WORLD_ID = "eldyrwild"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


def _initialize_world(world_root: Path) -> str:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    ordered_contributions = [
        WorldInitializationContribution(
            contribution_id=contribution_id,
            payload_sha256=kernel.compute_contribution_payload_sha256(
                by_id[contribution_id]
            ),
        )
        for contribution_id in ORDERED_CONTRIBUTION_IDS
    ]
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id="longmont-c2",
        focus_session_id="session-23",
        ordered_contributions=ordered_contributions,
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id=BUNDLE_ID,
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha="65ae001e0852d827ecd680200a965a576c705b1d",
        ),
    )
    initialize_world_from_contributions(
        world_root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )
    return kernel.open_world_graph_head(world_root, WORLD_ID).head_revision_id


def _create_draft(tmp_path: Path, *, world_id: str = WORLD_ID):
    return create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id=world_id,
            campaign_id="longmont-c2",
            name="Ironhide Brute",
            description="A brutal enforcer.",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_g1"),
            created_by="gm",
        ),
    )


def _mark_mechanics_saved(tmp_path: Path, draft) -> AcceptedMechanicsRefV1:
    current = get_threat_draft(tmp_path, draft.draft_id)
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_saved01",
            revision_id="rev_saved01",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64,
        ),
        accepted_from_draft_version=current.version,
        accepted_at="2020-01-01T00:00:00Z",
        accepted_from_candidate_id="cand_abc123",
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=current.version,
        locator=ref,
    )
    return ref


def _begin_request(
    draft,
    *,
    operation_id: str | None = None,
    parent_revision_id: str,
    expected_version: int | None = None,
) -> BeginThreatStatblockPublicationRequestV1:
    return BeginThreatStatblockPublicationRequestV1(
        operation_id=operation_id or str(uuid.uuid4()),
        expected_draft_version=expected_version or draft.version,
        expected_parent_revision_id=parent_revision_id,
    )


def test_new_claim_freezes_snapshot_and_requires_current_parent(
    tmp_path: Path,
) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())

    response = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )
    assert response.result_label == "publication_claimed"
    assert response.operation.authority_state == "awaiting_identity_resolution"
    snap = response.operation.source_snapshot
    assert snap.name == saved.name
    assert snap.accepted_mechanics_ref.statblock_id == "sb_saved01"
    assert same_mechanics_locator(
        snap.accepted_mechanics_ref.to_mechanics_locator(),
        saved.accepted_mechanics_ref.to_mechanics_locator(),
    )
    assert (publication_root(tmp_path) / saved.draft_id / f"{op_id}.json").is_file()


def test_stale_parent_creates_no_record(tmp_path: Path) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)

    with pytest.raises(ThreatStatblockPublicationError) as exc:
        begin_or_resume_publication_operation(
            tmp_path,
            draft_id=saved.draft_id,
            request=_begin_request(saved, parent_revision_id="rev:wrong"),
            graph_root=world_root,
        )
    assert exc.value.code == "stale_parent_revision"
    assert not list((publication_root(tmp_path) / saved.draft_id).glob("*.json"))


def test_replay_uses_stored_snapshot_after_draft_edit_and_deletion(
    tmp_path: Path,
) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())
    first = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )
    original_snapshot = first.operation.source_snapshot.model_dump(mode="json")

    update_threat_draft(
        tmp_path,
        saved.draft_id,
        UpdateThreatDraftRequest(
            expected_version=saved.version,
            name="Renamed Threat",
            description="Changed description.",
            threat_kind=saved.threat_kind,
            generation_intent=saved.generation_intent,
            graph_context_snapshot=saved.graph_context_snapshot,
        ),
    )

    replay = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(
            get_threat_draft(tmp_path, saved.draft_id),
            operation_id=op_id,
            parent_revision_id=head,
            expected_version=saved.version,
        ),
        graph_root=world_root,
    )
    assert replay.result_label == "publication_resumed"
    assert replay.operation.source_snapshot.model_dump(mode="json") == original_snapshot

    draft_path = threat_drafts_root(tmp_path) / f"{saved.draft_id}.json"
    draft_path.unlink()
    reloaded = read_publication_operation(
        tmp_path, draft_id=saved.draft_id, operation_id=op_id
    )
    assert reloaded.operation.source_snapshot.model_dump(mode="json") == original_snapshot


def test_changed_begin_request_conflicts_without_mutation(tmp_path: Path) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())
    first = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )
    before_bytes = (
        publication_root(tmp_path) / saved.draft_id / f"{op_id}.json"
    ).read_bytes()

    with pytest.raises(ThreatStatblockPublicationError) as exc:
        begin_or_resume_publication_operation(
            tmp_path,
            draft_id=saved.draft_id,
            request=_begin_request(
                saved,
                operation_id=op_id,
                parent_revision_id="rev:other",
                expected_version=saved.version,
            ),
            graph_root=world_root,
        )
    assert exc.value.code == "operation_input_conflict"
    after_bytes = (
        publication_root(tmp_path) / saved.draft_id / f"{op_id}.json"
    ).read_bytes()
    assert after_bytes == before_bytes
    assert first.operation.model_dump(mode="json") == read_publication_operation(
        tmp_path, draft_id=saved.draft_id, operation_id=op_id
    ).operation.model_dump(mode="json")


def test_reconcile_marks_stale_without_rebase(tmp_path: Path) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())
    claimed = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )
    draft_before = get_threat_draft(tmp_path, saved.draft_id).model_dump(mode="json")

    head_path = world_root / "graph_memory" / "worlds" / WORLD_ID / "head.json"
    head_path.write_text(
        head_path.read_text(encoding="utf-8").replace(head, "rev:advanced"),
        encoding="utf-8",
    )

    reconciled = reconcile_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        operation_id=op_id,
        request=ReconcileThreatStatblockPublicationRequestV1(
            expected_operation_version=claimed.operation.operation_version,
        ),
        graph_root=world_root,
    )
    assert reconciled.result_label == "publication_stale"
    assert reconciled.operation.authority_state == "stale"
    assert reconciled.operation.expected_parent_revision_id == head
    assert reconciled.operation.last_observed_head_revision_id == "rev:advanced"
    assert get_threat_draft(tmp_path, saved.draft_id).model_dump(mode="json") == draft_before


def test_cancel_is_cas_safe_and_idempotent(tmp_path: Path) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())
    claimed = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )
    draft_before = get_threat_draft(tmp_path, saved.draft_id).model_dump(mode="json")

    cancelled = cancel_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        operation_id=op_id,
        request=CancelThreatStatblockPublicationRequestV1(
            expected_operation_version=claimed.operation.operation_version,
        ),
    )
    assert cancelled.result_label == "publication_cancelled"
    assert cancelled.operation.operation_version == 2
    again = cancel_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        operation_id=op_id,
        request=CancelThreatStatblockPublicationRequestV1(expected_operation_version=999),
    )
    assert again.result_label == "publication_cancelled"
    assert get_threat_draft(tmp_path, saved.draft_id).model_dump(mode="json") == draft_before


def test_replay_never_reads_mutable_draft(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())
    begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )

    import apps.live_control_server.services.threat_statblock_publication as pub_svc

    def _forbidden_draft_read(*_args, **_kwargs):
        raise AssertionError("mutable ThreatDraft read forbidden on exact replay")

    monkeypatch.setattr(pub_svc, "get_threat_draft", _forbidden_draft_read)

    replay = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(
            saved,
            operation_id=op_id,
            parent_revision_id=head,
            expected_version=saved.version,
        ),
        graph_root=world_root,
    )
    assert replay.result_label == "publication_resumed"


def test_new_claim_uses_draft_observed_under_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)

    update_threat_draft(
        tmp_path,
        saved.draft_id,
        UpdateThreatDraftRequest(
            expected_version=saved.version,
            name="Locked Observation Name",
            description="Locked observation description.",
            threat_kind=saved.threat_kind,
            generation_intent=saved.generation_intent,
            graph_context_snapshot=saved.graph_context_snapshot,
        ),
    )
    updated = get_threat_draft(tmp_path, saved.draft_id)

    import apps.live_control_server.services.threat_statblock_publication as pub_svc

    builder_entered = threading.Event()
    real_get = pub_svc.get_threat_draft

    def _observe_get(root: Path, draft_id: str):
        builder_entered.set()
        return real_get(root, draft_id)

    monkeypatch.setattr(pub_svc, "get_threat_draft", _observe_get)

    response = begin_or_resume_publication_operation(
        tmp_path,
        draft_id=updated.draft_id,
        request=_begin_request(
            updated,
            operation_id=str(uuid.uuid4()),
            parent_revision_id=head,
            expected_version=updated.version,
        ),
        graph_root=world_root,
    )
    assert builder_entered.is_set()
    assert response.result_label == "publication_claimed"
    assert response.operation.source_snapshot.name == "Locked Observation Name"
    assert response.operation.source_snapshot.source_draft_version == updated.version


def test_invalid_route_draft_id_returns_invalid_request(tmp_path: Path) -> None:
    with pytest.raises(ThreatStatblockPublicationError) as exc:
        read_publication_operation(
            tmp_path,
            draft_id="not-a-uuid",
            operation_id=str(uuid.uuid4()),
        )
    assert exc.value.code == "invalid_request"
    assert exc.value.status_code == 422


def test_invalid_route_operation_id_returns_invalid_request(tmp_path: Path) -> None:
    with pytest.raises(ThreatStatblockPublicationError) as exc:
        read_publication_operation(
            tmp_path,
            draft_id=str(uuid.uuid4()),
            operation_id="not-valid",
        )
    assert exc.value.code == "invalid_request"
    assert exc.value.status_code == 422


def test_read_missing_operation_maps_to_not_found(tmp_path: Path) -> None:
    with pytest.raises(ThreatStatblockPublicationError) as exc:
        read_publication_operation(
            tmp_path,
            draft_id=str(uuid.uuid4()),
            operation_id=str(uuid.uuid4()),
        )
    assert exc.value.code == "operation_not_found"
    assert exc.value.status_code == 404


def test_cancel_version_mismatch_maps_typed_conflict(tmp_path: Path) -> None:
    world_root = tmp_path / "world"
    world_root.mkdir()
    head = _initialize_world(world_root)
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    op_id = str(uuid.uuid4())
    begin_or_resume_publication_operation(
        tmp_path,
        draft_id=saved.draft_id,
        request=_begin_request(saved, operation_id=op_id, parent_revision_id=head),
        graph_root=world_root,
    )
    with pytest.raises(ThreatStatblockPublicationError) as exc:
        cancel_publication_operation(
            tmp_path,
            draft_id=saved.draft_id,
            operation_id=op_id,
            request=CancelThreatStatblockPublicationRequestV1(expected_operation_version=999),
        )
    assert exc.value.code == "operation_version_mismatch"
    assert exc.value.status_code == 409

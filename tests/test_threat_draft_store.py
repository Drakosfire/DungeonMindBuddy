from __future__ import annotations

import threading
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    _draft_path,
    _index_path,
    create_threat_draft,
    get_threat_draft,
    list_threat_drafts,
    update_threat_draft,
)
from src.live_play.live_store import write_json


def _create_request(**overrides: object) -> CreateThreatDraftRequest:
    payload = {
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
            graph_revision_id="rev_graph_1",
            selected_node_ids=["node_a"],
            admitted_source_anchor_ids=["anchor_1"],
        ),
        "created_by": "gm",
    }
    payload.update(overrides)
    return CreateThreatDraftRequest.model_validate(payload)


def _update_request(created, *, description: str, expected_version: int = 1):
    return UpdateThreatDraftRequest(
        expected_version=expected_version,
        name=created.name,
        description=description,
        threat_kind=created.threat_kind,
        generation_intent=created.generation_intent,
        encounter_context=created.encounter_context,
        graph_context_snapshot=created.graph_context_snapshot,
    )


def test_create_read_list_round_trip(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.draft_id == created.draft_id
    assert loaded.version == 1
    assert loaded.description == "A brutal enforcer."
    assert loaded.workflow_state == "drafting"
    assert loaded.candidate_refs == []
    summaries, total = list_threat_drafts(tmp_path, campaign_id="campaign_1")
    assert total == 1
    assert len(summaries) == 1
    assert summaries[0].draft_id == created.draft_id


def test_graph_revision_id_accepts_world_graph_colon_form(tmp_path: Path) -> None:
    created = create_threat_draft(
        tmp_path,
        _create_request(
            graph_context_snapshot=GraphContextSnapshotV1(
                graph_revision_id="rev:5cadc9798562862cdde22350d8a3b56c",
                selected_node_ids=["node_a"],
                admitted_source_anchor_ids=["anchor_1"],
            ),
        ),
    )
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.graph_context_snapshot.graph_revision_id == (
        "rev:5cadc9798562862cdde22350d8a3b56c"
    )


def test_graph_revision_id_rejects_whitespace_and_slash() -> None:
    with pytest.raises(ValidationError):
        GraphContextSnapshotV1(graph_revision_id="rev: bad")
    with pytest.raises(ValidationError):
        GraphContextSnapshotV1(graph_revision_id="rev:../escape")


def test_update_increments_version_once(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    updated = update_threat_draft(
        tmp_path,
        created.draft_id,
        _update_request(created, description="Updated description."),
    )
    assert updated.version == 2
    assert updated.draft_id == created.draft_id
    assert updated.description == "Updated description."


def test_stale_update_writes_nothing(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    update_threat_draft(
        tmp_path,
        created.draft_id,
        _update_request(created, description="First update."),
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        update_threat_draft(
            tmp_path,
            created.draft_id,
            _update_request(created, description="Stale update."),
        )
    assert exc_info.value.status_code == 409
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.version == 2
    assert loaded.description == "First update."


def test_names_do_not_resolve_identity(tmp_path: Path) -> None:
    first = create_threat_draft(tmp_path, _create_request(name="Same Name"))
    second = create_threat_draft(tmp_path, _create_request(name="Same Name"))
    assert first.draft_id != second.draft_id


def test_create_uuid_collision_preserves_committed_draft(
    tmp_path: Path, monkeypatch
) -> None:
    existing = create_threat_draft(
        tmp_path,
        _create_request(name="Original", description="Keep me"),
    )
    original = get_threat_draft(tmp_path, existing.draft_id)
    monkeypatch.setattr(
        "apps.live_control_server.services.threat_draft_store.uuid.uuid4",
        lambda: uuid.UUID(existing.draft_id),
    )

    with pytest.raises(ThreatDraftStoreError) as exc_info:
        create_threat_draft(
            tmp_path,
            _create_request(name="Colliding", description="Must not overwrite"),
        )
    assert exc_info.value.status_code == 500
    assert "collision" in str(exc_info.value)

    loaded = get_threat_draft(tmp_path, existing.draft_id)
    assert loaded.model_dump(by_alias=True) == original.model_dump(by_alias=True)
    assert loaded.description == "Keep me"
    assert loaded.name == "Original"
    assert loaded.version == 1
    summaries, total = list_threat_drafts(tmp_path, limit=100)
    assert total == 1
    assert summaries[0].draft_id == existing.draft_id


def test_concurrent_updates_only_one_succeeds(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    barrier = threading.Barrier(2)
    successes: list[str] = []
    failures: list[int] = []
    guard = threading.Lock()

    def worker(description: str) -> None:
        barrier.wait()
        try:
            updated = update_threat_draft(
                tmp_path,
                created.draft_id,
                _update_request(created, description=description),
            )
            with guard:
                successes.append(updated.description)
        except ThreatDraftStoreError as exc:
            with guard:
                failures.append(exc.status_code)

    threads = [
        threading.Thread(target=worker, args=("Author A",)),
        threading.Thread(target=worker, args=("Author B",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(successes) == 1
    assert failures == [409]
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.version == 2
    assert loaded.description == successes[0]
    assert loaded.description in {"Author A", "Author B"}


def test_concurrent_creates_all_indexed(tmp_path: Path) -> None:
    barrier = threading.Barrier(8)
    created_ids: list[str] = []
    guard = threading.Lock()

    def worker(index: int) -> None:
        barrier.wait()
        draft = create_threat_draft(
            tmp_path,
            _create_request(name=f"Threat {index}", description=f"Body {index}"),
        )
        with guard:
            created_ids.append(draft.draft_id)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(created_ids) == 8
    assert len(set(created_ids)) == 8
    summaries, total = list_threat_drafts(tmp_path, limit=100)
    assert total == 8
    assert {item.draft_id for item in summaries} == set(created_ids)


def test_create_index_failure_leaves_no_orphan(tmp_path: Path, monkeypatch) -> None:
    real_write_json = write_json
    index_path = _index_path(tmp_path)

    def boom_write(path: Path, data: dict) -> None:
        if Path(path) == index_path:
            raise OSError("disk full")
        real_write_json(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.threat_draft_store.write_json",
        boom_write,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        create_threat_draft(tmp_path, _create_request())
    assert exc_info.value.status_code == 500
    assert "storage unavailable" in str(exc_info.value)

    store_root = tmp_path / "out" / "threat_drafts"
    draft_files = list(store_root.glob("*.json")) if store_root.is_dir() else []
    assert draft_files == []
    assert not index_path.is_file()


def test_update_write_failure_preserves_prior_version(
    tmp_path: Path, monkeypatch
) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    draft_path = _draft_path(tmp_path, created.draft_id)
    real_write_json = write_json

    def boom_write(path: Path, data: dict) -> None:
        if Path(path) == draft_path:
            raise OSError("disk full")
        real_write_json(path, data)

    monkeypatch.setattr(
        "apps.live_control_server.services.threat_draft_store.write_json",
        boom_write,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        update_threat_draft(
            tmp_path,
            created.draft_id,
            _update_request(created, description="Should not persist."),
        )
    assert exc_info.value.status_code == 500
    assert "storage unavailable" in str(exc_info.value)

    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.version == 1
    assert loaded.description == created.description


def test_index_rejects_duplicate_ids(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    index_path = _index_path(tmp_path)
    write_json(
        index_path,
        {
            "schema": "dmb_threat_draft_index_v1",
            "draft_ids": [created.draft_id, created.draft_id],
        },
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        list_threat_drafts(tmp_path)
    assert exc_info.value.status_code == 500
    assert "corrupt threat draft index" in str(exc_info.value)


def test_index_rejects_traversal_ids(tmp_path: Path) -> None:
    index_path = _index_path(tmp_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        index_path,
        {
            "schema": "dmb_threat_draft_index_v1",
            "draft_ids": ["../../etc/passwd"],
        },
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        list_threat_drafts(tmp_path)
    assert exc_info.value.status_code == 500
    assert "corrupt threat draft index" in str(exc_info.value)


def test_index_rejects_unknown_schema(tmp_path: Path) -> None:
    index_path = _index_path(tmp_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        index_path,
        {
            "schema": "dmb_threat_draft_index_v0",
            "draft_ids": [],
        },
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        list_threat_drafts(tmp_path)
    assert exc_info.value.status_code == 500


def test_missing_indexed_file_is_integrity_failure(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    _draft_path(tmp_path, created.draft_id).unlink()
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        list_threat_drafts(tmp_path)
    assert exc_info.value.status_code == 500
    assert "integrity failure" in str(exc_info.value)


def test_uncommitted_orphan_is_not_directly_readable(
    tmp_path: Path, monkeypatch
) -> None:
    real_write_json = write_json
    index_path = _index_path(tmp_path)

    def boom_write(path: Path, data: dict) -> None:
        if Path(path) == index_path:
            raise OSError("disk full")
        real_write_json(path, data)

    def boom_remove(root: Path, draft_id: str) -> None:
        raise ThreatDraftStoreError(
            "threat draft storage unavailable",
            status_code=500,
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.threat_draft_store.write_json",
        boom_write,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.threat_draft_store._remove_draft_file",
        boom_remove,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        create_threat_draft(tmp_path, _create_request())
    assert exc_info.value.status_code == 500

    store_root = tmp_path / "out" / "threat_drafts"
    orphan_files = [
        path
        for path in store_root.glob("*.json")
        if path.name != "index.json"
    ]
    assert len(orphan_files) == 1
    orphan_id = orphan_files[0].stem

    monkeypatch.undo()
    with pytest.raises(ThreatDraftStoreError) as get_exc:
        get_threat_draft(tmp_path, orphan_id)
    assert get_exc.value.status_code == 404

    seed = _create_request()
    with pytest.raises(ThreatDraftStoreError) as update_exc:
        update_threat_draft(
            tmp_path,
            orphan_id,
            UpdateThreatDraftRequest(
                expected_version=1,
                name=seed.name,
                description="must not write",
                threat_kind=seed.threat_kind,
                generation_intent=seed.generation_intent,
                encounter_context=seed.encounter_context,
                graph_context_snapshot=seed.graph_context_snapshot,
            ),
        )
    assert update_exc.value.status_code == 404


def test_embedded_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    alpha = create_threat_draft(tmp_path, _create_request(name="Alpha", description="A"))
    beta = create_threat_draft(tmp_path, _create_request(name="Beta", description="B"))
    # Place beta's payload under alpha's filename while index still commits alpha.
    write_json(
        _draft_path(tmp_path, alpha.draft_id),
        beta.model_dump(mode="json", by_alias=True),
    )

    with pytest.raises(ThreatDraftStoreError) as get_exc:
        get_threat_draft(tmp_path, alpha.draft_id)
    assert get_exc.value.status_code == 500
    assert "identity mismatch" in str(get_exc.value)

    with pytest.raises(ThreatDraftStoreError) as update_exc:
        update_threat_draft(
            tmp_path,
            alpha.draft_id,
            _update_request(alpha, description="must not escape to beta"),
        )
    assert update_exc.value.status_code == 500
    assert "identity mismatch" in str(update_exc.value)

    # Beta remains the committed prior revision; alpha's path was not rewritten onto beta.
    loaded_beta = get_threat_draft(tmp_path, beta.draft_id)
    assert loaded_beta.version == 1
    assert loaded_beta.description == "B"
    assert loaded_beta.draft_id == beta.draft_id

    with pytest.raises(ThreatDraftStoreError) as list_exc:
        list_threat_drafts(tmp_path)
    assert list_exc.value.status_code == 500
    assert "identity mismatch" in str(list_exc.value)


def test_path_escape_rejected_for_draft_id(tmp_path: Path) -> None:
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        get_threat_draft(tmp_path, "../escape")
    assert exc_info.value.status_code == 422


def test_list_is_bounded(tmp_path: Path) -> None:
    for index in range(5):
        create_threat_draft(
            tmp_path,
            _create_request(name=f"Threat {index}", description=f"Body {index}"),
        )
    page, total = list_threat_drafts(tmp_path, limit=2, offset=1)
    assert total == 5
    assert len(page) == 2
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        list_threat_drafts(tmp_path, limit=101)
    assert exc_info.value.status_code == 422


def test_reload_after_store_restart(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    # New process equivalent: only durable files are consulted.
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.model_dump(by_alias=True) == created.model_dump(by_alias=True)
    updated = update_threat_draft(
        tmp_path,
        created.draft_id,
        _update_request(created, description="After reload."),
    )
    assert updated.version == 2
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        update_threat_draft(
            tmp_path,
            created.draft_id,
            _update_request(created, description="Stale after reload."),
        )
    assert exc_info.value.status_code == 409


def test_request_fields_are_bounded() -> None:
    with pytest.raises(ValidationError):
        _create_request(description="x" * 20_001)
    with pytest.raises(ValidationError):
        CreateThreatDraftRequest.model_validate(
            {
                **_create_request().model_dump(),
                "generation_intent": {
                    "ruleset": {"system": "dnd5e", "edition": "2024"},
                    "target_cr": "c" * 33,
                    "must_include": [],
                    "must_avoid": [],
                },
            }
        )
    with pytest.raises(ValidationError):
        CreateThreatDraftRequest.model_validate(
            {
                **_create_request().model_dump(),
                "intended_roles": ["r" * 501],
            }
        )
    with pytest.raises(ValidationError):
        CreateThreatDraftRequest.model_validate(
            {
                **_create_request().model_dump(),
                "generation_intent": {
                    "ruleset": {
                        "system": "dnd5e",
                        "edition": "2024",
                        "house_ruleset_id": "h" * 65,
                    },
                    "must_include": ["instruction " + ("x" * 500)],
                    "must_avoid": [],
                },
            }
        )


def test_store_exposes_candidate_ref_append_for_sbw03() -> None:
    import apps.live_control_server.services.threat_draft_store as store

    assert hasattr(store, "append_candidate_ref")


def test_attach_accepted_mechanics_ref_cas_and_conflict(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        AcceptedMechanicsRefConflictError,
        attach_accepted_mechanics_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())

    def _ref(rev: str, *, accepted_at: str = "2020-01-01T00:00:00Z") -> AcceptedMechanicsRefV1:
        loc = MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_a",
            revision_id=rev,
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64,
        )
        return AcceptedMechanicsRefV1.from_locator(
            loc,
            accepted_from_draft_version=1,
            accepted_at=accepted_at,
            accepted_from_candidate_id=None,
        )

    updated = attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        locator=_ref("rev_one"),
    )
    assert updated.workflow_state == "mechanics_saved"
    assert updated.version == 2

    with pytest.raises(AcceptedMechanicsRefConflictError):
        attach_accepted_mechanics_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=2,
            locator=_ref("rev_two"),
        )

    idempotent = attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=2,
        locator=_ref("rev_one", accepted_at="2099-01-01T00:00:00Z"),
    )
    assert idempotent.version == 2
    assert idempotent.accepted_mechanics_ref is not None
    assert idempotent.accepted_mechanics_ref.accepted_at == "2020-01-01T00:00:00Z"


def test_threat_draft_rejects_contradictory_accepted_ref_workflow(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.models.threat_draft import ThreatDraftV1

    created = create_threat_draft(tmp_path, _create_request())
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_a",
            revision_id="rev_one",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64,
        ),
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
    )
    payload = created.model_dump(mode="json", by_alias=True)
    payload["accepted_mechanics_ref"] = ref.model_dump(mode="json")
    payload["workflow_state"] = "candidate_ready"
    with pytest.raises(ValidationError):
        ThreatDraftV1.model_validate(payload)

    payload["workflow_state"] = "mechanics_saved"
    payload["accepted_mechanics_ref"] = None
    with pytest.raises(ValidationError):
        ThreatDraftV1.model_validate(payload)


def test_append_candidate_ref_does_not_regress_mechanics_saved(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.models.threat_draft import ThreatDraftCandidateRefV1
    from apps.live_control_server.services.threat_draft_store import (
        append_candidate_ref,
        attach_accepted_mechanics_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_a",
            revision_id="rev_one",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64,
        ),
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
    )
    saved = attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        locator=ref,
    )
    assert saved.workflow_state == "mechanics_saved"

    candidate = ThreatDraftCandidateRefV1(
        candidate_id="cand_recovery01",
        generated_from_draft_version=saved.version,
        request_id="req_recovery01",
        created_at="2020-01-02T00:00:00Z",
    )
    after = append_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=saved.version,
        candidate_ref=candidate,
        workflow_state="candidate_ready",
    )
    assert after.workflow_state == "mechanics_saved"
    assert after.accepted_mechanics_ref is not None
    assert len(after.candidate_refs) == 1


def test_find_threat_draft_for_candidate_by_ref(tmp_path: Path) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        append_candidate_ref,
        create_threat_draft,
        find_threat_draft_for_candidate,
    )
    from apps.live_control_server.models.threat_draft import ThreatDraftCandidateRefV1

    draft = create_threat_draft(tmp_path, _create_request(name="Latchling"))
    ref = ThreatDraftCandidateRefV1(
        candidate_id="cand_findme123",
        generated_from_draft_version=1,
        request_id="req_find_1",
        created_at="2026-07-26T00:00:00Z",
        status="active",
    )
    append_candidate_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=1,
        candidate_ref=ref,
    )
    found = find_threat_draft_for_candidate(tmp_path, "cand_findme123")
    assert found is not None
    found_draft, found_ref = found
    assert found_draft.draft_id == draft.draft_id
    assert found_ref.candidate_id == "cand_findme123"
    assert find_threat_draft_for_candidate(tmp_path, "cand_missing999") is None


def _sample_revise_lineage(
    *,
    request_id: str = "req_revise_1",
    draft_id: str,
    source_draft_version: int = 1,
) -> dict:
    return {
        "schema": "dmb_candidate_lineage_v1",
        "revise_request_id": request_id,
        "source_origin_kind": "edited_working_copy",
        "instruction_options_digest": "sha256:" + "b" * 64,
        "created_at": "2026-07-27T00:00:00Z",
        "edited_working_copy": {
            "draft_id": draft_id,
            "source_draft_version": source_draft_version,
            "editor_state_revision": "editor-1",
            "source_definition_digest": "sha256:" + "c" * 64,
        },
    }


def _revise_candidate_ref(
    *,
    candidate_id: str = "cand_revise01",
    request_id: str = "req_revise_1",
    draft_id: str,
    generated_from_draft_version: int = 1,
    source_draft_version: int | None = None,
    status: str = "active",
    lineage_draft_id: str | None = None,
):
    from apps.live_control_server.models.threat_draft import (
        CandidateLineageV1,
        ThreatDraftCandidateRefV1,
    )

    lineage_version = (
        source_draft_version
        if source_draft_version is not None
        else generated_from_draft_version
    )
    return ThreatDraftCandidateRefV1(
        candidate_id=candidate_id,
        generated_from_draft_version=generated_from_draft_version,
        request_id=request_id,
        created_at="2026-07-27T00:00:00Z",
        status=status,  # type: ignore[arg-type]
        lineage=CandidateLineageV1.model_validate(
            _sample_revise_lineage(
                request_id=request_id,
                draft_id=lineage_draft_id or draft_id,
                source_draft_version=lineage_version,
            )
        ),
    )


def test_legacy_candidate_ref_without_lineage_loads(tmp_path: Path) -> None:
    from apps.live_control_server.models.threat_draft import ThreatDraftCandidateRefV1

    created = create_threat_draft(tmp_path, _create_request())
    ref = ThreatDraftCandidateRefV1(
        candidate_id="cand_legacy01",
        generated_from_draft_version=1,
        request_id="req_legacy_1",
        created_at="2026-07-27T00:00:00Z",
    )
    payload = get_threat_draft(tmp_path, created.draft_id).model_dump(mode="json", by_alias=True)
    payload["candidate_refs"] = [ref.model_dump(mode="json")]
    from apps.live_control_server.models.threat_draft import ThreatDraftV1

    ThreatDraftV1.model_validate(payload)
    loaded = ThreatDraftCandidateRefV1.model_validate(ref.model_dump(mode="json"))
    assert loaded.lineage is None


def test_reconcile_revise_candidate_ref_fresh_attach_bumps_version_once(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = _revise_candidate_ref(draft_id=created.draft_id)
    updated = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        candidate_ref=ref,
    )
    assert updated.version == 2
    assert len(updated.candidate_refs) == 1
    assert updated.candidate_refs[0].lineage is not None
    assert updated.workflow_state == "candidate_ready"

    again = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=2,
        candidate_ref=ref,
    )
    assert again.version == 2
    assert len(again.candidate_refs) == 1


def test_reconcile_rejects_missing_lineage(tmp_path: Path) -> None:
    from apps.live_control_server.models.threat_draft import ThreatDraftCandidateRefV1
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = ThreatDraftCandidateRefV1(
        candidate_id="cand_nolineage",
        generated_from_draft_version=1,
        request_id="req_nolineage",
        created_at="2026-07-27T00:00:00Z",
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=1,
            candidate_ref=ref,
        )
    assert exc_info.value.status_code == 422
    assert get_threat_draft(tmp_path, created.draft_id).version == 1


def test_reconcile_stale_version_writes_nothing(tmp_path: Path) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = _revise_candidate_ref(draft_id=created.draft_id)
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=99,
            candidate_ref=ref,
        )
    assert exc_info.value.status_code == 409
    assert get_threat_draft(tmp_path, created.draft_id).candidate_refs == []


def test_reconcile_identity_conflict_same_candidate_different_request(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    first = _revise_candidate_ref(draft_id=created.draft_id, request_id="req_a")
    reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        candidate_ref=first,
    )
    conflict = _revise_candidate_ref(
        candidate_id="cand_revise01",
        draft_id=created.draft_id,
        request_id="req_b",
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=2,
            candidate_ref=conflict,
        )
    assert exc_info.value.status_code == 409


def test_reconcile_active_to_superseded_with_idempotent_replay(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.models.threat_draft import (
        RequestedSourceStatusTransitionV1,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        append_candidate_ref,
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    source = ThreatDraftCandidateRefV1(
        candidate_id="cand_source01",
        generated_from_draft_version=1,
        request_id="req_source",
        created_at="2026-07-26T00:00:00Z",
        status="active",
    )
    draft = append_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        candidate_ref=source,
    )
    revise_ref = _revise_candidate_ref(
        candidate_id="cand_revise02",
        request_id="req_revise_2",
        draft_id=created.draft_id,
    )
    transition = RequestedSourceStatusTransitionV1(
        source_candidate_id="cand_source01",
        to_status="superseded",
    )
    after = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=draft.version,
        candidate_ref=revise_ref,
        requested_source_transition=transition,
    )
    source_ref = next(
        ref for ref in after.candidate_refs if ref.candidate_id == "cand_source01"
    )
    assert source_ref.status == "superseded"
    version_after = after.version
    replay = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=version_after,
        candidate_ref=revise_ref,
        requested_source_transition=transition,
    )
    assert replay.version == version_after


def test_reconcile_preserves_mechanics_saved(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_a",
            revision_id="rev_one",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64,
        ),
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
    )
    saved = attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        locator=ref,
    )
    revise_ref = _revise_candidate_ref(draft_id=created.draft_id)
    after = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=saved.version,
        candidate_ref=revise_ref,
    )
    assert after.workflow_state == "mechanics_saved"
    assert after.accepted_mechanics_ref is not None


def test_reconcile_rejects_cross_draft_lineage(tmp_path: Path) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    target = create_threat_draft(tmp_path, _create_request(name="Target"))
    other = create_threat_draft(tmp_path, _create_request(name="Other"))
    ref = _revise_candidate_ref(
        draft_id=target.draft_id,
        lineage_draft_id=other.draft_id,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=target.draft_id,
            expected_version=1,
            candidate_ref=ref,
        )
    assert exc_info.value.status_code == 422
    assert get_threat_draft(tmp_path, target.draft_id).candidate_refs == []


def test_reconcile_rejects_source_version_mismatch(tmp_path: Path) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = _revise_candidate_ref(
        draft_id=created.draft_id,
        generated_from_draft_version=1,
        source_draft_version=2,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=1,
            candidate_ref=ref,
        )
    assert exc_info.value.status_code == 422
    assert get_threat_draft(tmp_path, created.draft_id).version == 1


def test_reconcile_rejects_terminal_incoming_status(tmp_path: Path) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = _revise_candidate_ref(draft_id=created.draft_id, status="superseded")
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=1,
            candidate_ref=ref,
        )
    assert exc_info.value.status_code == 422
    assert get_threat_draft(tmp_path, created.draft_id).candidate_refs == []


def test_append_candidate_ref_rejects_revise_lineage(tmp_path: Path) -> None:
    from apps.live_control_server.services.threat_draft_store import (
        append_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    ref = _revise_candidate_ref(draft_id=created.draft_id)
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        append_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=1,
            candidate_ref=ref,
        )
    assert exc_info.value.status_code == 422
    assert "lineage" in str(exc_info.value).lower()
    assert get_threat_draft(tmp_path, created.draft_id).candidate_refs == []


def test_reconcile_expired_requires_exact_expires_at_evidence(tmp_path: Path) -> None:
    from apps.live_control_server.models.threat_draft import (
        RequestedSourceStatusTransitionV1,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        append_candidate_ref,
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    source = ThreatDraftCandidateRefV1(
        candidate_id="cand_sourceexp1",
        generated_from_draft_version=1,
        request_id="req_source_exp",
        created_at="2026-07-26T00:00:00Z",
        expires_at="2026-07-01T00:00:00Z",
        status="active",
    )
    draft = append_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        candidate_ref=source,
    )
    revise_ref = _revise_candidate_ref(
        candidate_id="cand_reviseexp1",
        request_id="req_revise_exp",
        draft_id=created.draft_id,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=draft.version,
            candidate_ref=revise_ref,
            requested_source_transition=RequestedSourceStatusTransitionV1(
                source_candidate_id="cand_sourceexp1",
                to_status="expired",
            ),
        )
    assert exc_info.value.status_code == 409

    after = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=draft.version,
        candidate_ref=revise_ref,
        requested_source_transition=RequestedSourceStatusTransitionV1(
            source_candidate_id="cand_sourceexp1",
            to_status="expired",
            exact_expires_at="2026-07-01T00:00:00Z",
        ),
    )
    source_ref = next(
        ref for ref in after.candidate_refs if ref.candidate_id == "cand_sourceexp1"
    )
    assert source_ref.status == "expired"


def test_reconcile_active_to_rejected_and_terminal_cannot_transition(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.models.threat_draft import (
        RequestedSourceStatusTransitionV1,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        append_candidate_ref,
        reconcile_revise_candidate_ref,
    )

    created = create_threat_draft(tmp_path, _create_request())
    source = ThreatDraftCandidateRefV1(
        candidate_id="cand_sourcerej1",
        generated_from_draft_version=1,
        request_id="req_source_rej",
        created_at="2026-07-26T00:00:00Z",
        status="active",
    )
    draft = append_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=1,
        candidate_ref=source,
    )
    revise_ref = _revise_candidate_ref(
        candidate_id="cand_reviserej1",
        request_id="req_revise_rej",
        draft_id=created.draft_id,
    )
    after = reconcile_revise_candidate_ref(
        tmp_path,
        draft_id=created.draft_id,
        expected_version=draft.version,
        candidate_ref=revise_ref,
        requested_source_transition=RequestedSourceStatusTransitionV1(
            source_candidate_id="cand_sourcerej1",
            to_status="rejected",
        ),
    )
    source_ref = next(
        ref for ref in after.candidate_refs if ref.candidate_id == "cand_sourcerej1"
    )
    assert source_ref.status == "rejected"

    second = _revise_candidate_ref(
        candidate_id="cand_reviserej2",
        request_id="req_revise_rej2",
        draft_id=created.draft_id,
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        reconcile_revise_candidate_ref(
            tmp_path,
            draft_id=created.draft_id,
            expected_version=after.version,
            candidate_ref=second,
            requested_source_transition=RequestedSourceStatusTransitionV1(
                source_candidate_id="cand_sourcerej1",
                to_status="active",
            ),
        )
    assert exc_info.value.status_code == 409


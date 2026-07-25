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

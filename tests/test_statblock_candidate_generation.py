from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    downstream_expired,
    downstream_not_found,
    downstream_timeout,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.statblock_candidate_workflow import (
    GenerateThreatDraftCandidateRequestV1,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    ThreatDraftCandidateRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.services.statblock_candidate_cache import (
    CandidateCacheError,
    store_candidate_payload,
)
from apps.live_control_server.services.statblock_candidate_generation import (
    generate_candidate_from_draft,
    map_draft_to_generate_request,
    read_candidate,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    append_candidate_ref,
    create_threat_draft,
    get_threat_draft,
    update_threat_draft,
)

FIXTURE_RAW = json.loads(
    (Path(__file__).parent / "fixtures" / "statblocks" / "v1" / "candidate-response.json").read_text(
        encoding="utf-8"
    )
)


def _candidate_payload(*, request_id: str = "req-fixed", candidate_id: str = "cand_fixture1"):
    payload = dict(FIXTURE_RAW)
    payload["candidate_id"] = candidate_id
    payload["expires_at"] = "2099-01-01T00:00:00Z"
    receipt = dict(payload["generation_receipt"])
    receipt["request_id"] = request_id
    payload["generation_receipt"] = receipt
    return GeneratedStatblockCandidateV1.model_validate(payload)


def _create_draft(tmp_path: Path):
    return create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Ironhide Brute",
            description="A brutal enforcer.",
            threat_kind="creature",
            intended_roles=["brute"],
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
                target_cr="3",
                must_include=["reach"],
            ),
            graph_context_snapshot=GraphContextSnapshotV1(
                graph_revision_id="rev_graph_1",
                selected_node_ids=["node_a"],
                admitted_source_anchor_ids=["anchor_1"],
            ),
            created_by="gm",
        ),
    )


def _advance_draft(tmp_path: Path, draft) -> None:
    update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description=draft.description + " (edited)",
            threat_kind=draft.threat_kind,
            intended_roles=list(draft.intended_roles),
            tags=list(draft.tags),
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
            focus=draft.focus,
        ),
    )


class FakeClient:
    def __init__(self, *, payload=None, error=None, delay_event: threading.Event | None = None):
        self.payload = payload
        self.error = error
        self.delay_event = delay_event
        self.calls: list[dict] = []
        self.lock = threading.Lock()

    def generate_candidate(self, body: dict):
        with self.lock:
            self.calls.append(body)
        if self.delay_event is not None:
            self.delay_event.wait(timeout=2.0)
        if self.error is not None:
            raise self.error
        assert self.payload is not None
        return self.payload

    def get_candidate(self, candidate_id: str):
        if self.error is not None:
            raise self.error
        assert self.payload is not None
        return self.payload


def test_request_mapping_disables_images(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    body = map_draft_to_generate_request(draft, request_id="req-1")
    assert body["asset_options"]["generate_images"] is False
    assert body["source"]["description"] == "A brutal enforcer."
    assert body["intent"]["target_cr"] == "3"
    assert body["intent"]["roles"] == ["brute"]


def test_stale_version_blocks_downstream(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload())
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(expected_draft_version=99),
            client=client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 409
    assert client.calls == []


def test_success_stores_ref_and_cache(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-fixed"))
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-fixed",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.candidate_ref is not None
    assert result.candidate_ref.candidate_id == "cand_fixture1"
    assert result.candidate_ref.generated_from_draft_version == 1
    assert result.request_id == "req-fixed"
    assert result.cache_status == "stored"
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.version == 1
    assert reloaded.description == draft.description
    assert len(reloaded.candidate_refs) == 1
    read = read_candidate(tmp_path, candidate_id="cand_fixture1")
    assert read.status == "active"
    assert read.candidate is not None
    assert read.candidate.candidate_id == "cand_fixture1"


def test_replay_same_request_id_does_not_regenerate(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-replay"))
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-replay",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"
    assert len(client.calls) == 1

    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-replay",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.candidate_id == first.candidate_ref.candidate_id
    assert len(client.calls) == 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1


def test_concurrent_identical_requests_generate_once(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    release = threading.Event()
    client = FakeClient(
        payload=_candidate_payload(request_id="req-concurrent"),
        delay_event=release,
    )
    results: list = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def worker() -> None:
        barrier.wait(timeout=2.0)
        try:
            results.append(
                generate_candidate_from_draft(
                    tmp_path,
                    draft_id=draft.draft_id,
                    request=GenerateThreatDraftCandidateRequestV1(
                        expected_draft_version=1,
                        client_request_id="req-concurrent",
                    ),
                    client=client,  # type: ignore[arg-type]
                )
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    # Let both threads race into claim/generate before releasing the provider.
    threading.Event().wait(0.05)
    release.set()
    for thread in threads:
        thread.join(timeout=3.0)

    assert errors == []
    assert len(results) == 2
    assert len(client.calls) == 1
    successes = [result for result in results if result.outcome == "success"]
    incompletes = [
        result
        for result in results
        if result.outcome == "failure"
        and result.failure_category == "generation_incomplete"
    ]
    # One caller owns generate; the other either waits for completion via a
    # later claim observation or receives the pending claim signal.
    assert len(successes) + len(incompletes) == 2
    assert len(successes) >= 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1


def test_timeout_after_claim_blocks_duplicate_generate(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-timeout",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "failure"
    assert first.failure_category == "downstream_timeout"
    assert len(client.calls) == 1

    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-timeout",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "failure"
    assert second.failure_category == "generation_incomplete"
    assert len(client.calls) == 1


def test_replay_digest_conflict_is_rejected(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-conflict"))
    generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-conflict",
        ),
        client=client,  # type: ignore[arg-type]
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-conflict",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["request_digest"] = "sha256:" + ("b" * 64)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ThreatDraftStoreError) as exc_info:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=1,
                client_request_id="req-conflict",
            ),
            client=client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 409
    assert len(client.calls) == 1


def test_lineage_survives_draft_advance_on_partial_ref(tmp_path: Path, monkeypatch) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-lineage"))

    original_append = append_candidate_ref
    calls = {"count": 0}

    def flaky_append(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ThreatDraftStoreError("expected_version mismatch", status_code=409)
        return original_append(*args, **kwargs)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.append_candidate_ref",
        flaky_append,
    )
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-lineage",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"
    assert first.cache_status == "partial_ref"
    assert len(client.calls) == 1

    monkeypatch.undo()
    _advance_draft(tmp_path, draft)
    advanced = get_threat_draft(tmp_path, draft.draft_id)
    assert advanced.version == 2

    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-lineage",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.generated_from_draft_version == 1
    assert len(client.calls) == 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.version == 2
    assert len(reloaded.candidate_refs) == 1
    assert reloaded.candidate_refs[0].generated_from_draft_version == 1


def test_capacity_checked_before_provider_call(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    for index in range(64):
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
    client = FakeClient(payload=_candidate_payload(request_id="req-overflow"))
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=1,
                client_request_id="req-overflow",
            ),
            client=client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 422
    assert client.calls == []


def test_failure_preserves_draft(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(expected_draft_version=1),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "downstream_timeout"
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.version == 1
    assert reloaded.candidate_refs == []


def test_missing_and_expired_mapping(tmp_path: Path) -> None:
    missing_client = FakeClient(error=downstream_not_found(status_code=404))
    missing = read_candidate(
        tmp_path,
        candidate_id="cand_missing1",
        client=missing_client,  # type: ignore[arg-type]
    )
    assert missing.status == "missing"
    assert missing.failure_category == "downstream_not_found"

    expired_client = FakeClient(error=downstream_expired(status_code=410))
    expired = read_candidate(
        tmp_path,
        candidate_id="cand_expired1",
        client=expired_client,  # type: ignore[arg-type]
    )
    assert expired.status == "expired"
    assert expired.failure_category == "downstream_expired"


def test_cached_expiry_uses_datetime_not_lexicographic(tmp_path: Path) -> None:
    # Lexicographic comparison of these timestamps is inverted vs datetime order
    # when timezone offsets differ; datetime comparison must classify as expired.
    payload = dict(FIXTURE_RAW)
    payload["candidate_id"] = "cand_expired2"
    payload["created_at"] = "2020-01-01T00:00:00Z"
    payload["expires_at"] = "2020-06-01T00:00:00+00:00"
    receipt = dict(payload["generation_receipt"])
    receipt["request_id"] = "req-expired"
    payload["generation_receipt"] = receipt
    candidate = GeneratedStatblockCandidateV1.model_validate(payload)
    store_candidate_payload(tmp_path, candidate)
    read = read_candidate(tmp_path, candidate_id="cand_expired2")
    assert read.status == "expired"


def test_cache_rejects_conflicting_payload(tmp_path: Path) -> None:
    first = _candidate_payload(candidate_id="cand_cache1", request_id="req-a")
    store_candidate_payload(tmp_path, first)
    second = _candidate_payload(candidate_id="cand_cache1", request_id="req-b")
    with pytest.raises(CandidateCacheError) as exc_info:
        store_candidate_payload(tmp_path, second)
    assert exc_info.value.status_code == 409


def test_corrupt_cache_on_replay_is_typed_integrity_failure(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-corrupt"))
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-corrupt",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"

    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-corrupt",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_payload"] = {"not": "a candidate"}
    path.write_text(json.dumps(payload), encoding="utf-8")

    def boom_read(root, candidate_id):
        raise CandidateCacheError("corrupt candidate cache record", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.read_candidate_payload_or_none",
        boom_read,
    )
    client.error = downstream_not_found(status_code=404)
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-corrupt",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "failure"
    assert second.failure_category == "integrity_failure"
    assert len(client.calls) == 1


def test_append_ref_enforces_source_version_and_limit(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    with pytest.raises(ThreatDraftStoreError) as mismatch:
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id="cand_a",
                generated_from_draft_version=2,
                request_id="req-a",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
    assert mismatch.value.status_code == 422

    for index in range(64):
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
    with pytest.raises(ThreatDraftStoreError) as limit_exc:
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id="cand_overflow",
                generated_from_draft_version=1,
                request_id="req-overflow",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
    assert limit_exc.value.status_code == 422
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 64


def test_append_ref_conflict_on_reused_candidate_id(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    append_candidate_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=1,
        candidate_ref=ThreatDraftCandidateRefV1(
            candidate_id="cand_same",
            generated_from_draft_version=1,
            request_id="req-1",
            created_at="2026-01-01T00:00:00Z",
        ),
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id="cand_same",
                generated_from_draft_version=1,
                request_id="req-2",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
    assert exc_info.value.status_code == 409


def test_partial_cache_is_recoverable_on_replay(tmp_path: Path, monkeypatch) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-partial"))

    def boom_store(root, candidate):
        raise CandidateCacheError("disk full", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.store_candidate_payload",
        boom_store,
    )
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-partial",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"
    assert first.cache_status == "partial_cache"
    assert len(first.persistence_failures) == 1
    assert first.persistence_failures[0].component == "cache"
    assert len(client.calls) == 1

    monkeypatch.undo()
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-partial",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.candidate_id == "cand_fixture1"
    assert len(client.calls) == 1


def test_partial_both_reports_cache_and_ref_failures(tmp_path: Path, monkeypatch) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-both"))

    def boom_store(root, candidate):
        raise CandidateCacheError("disk full", status_code=500)

    def boom_append(*args, **kwargs):
        raise ThreatDraftStoreError("ref write failed", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.store_candidate_payload",
        boom_store,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.append_candidate_ref",
        boom_append,
    )
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-both",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.cache_status == "partial_both"
    assert {item.component for item in result.persistence_failures} == {
        "cache",
        "candidate_ref",
    }
    assert result.failure_category == "cache_failure"
    assert "cache:" in (result.failure_message or "")
    assert "candidate_ref:" in (result.failure_message or "")
    assert result.candidate is not None
    assert result.candidate_ref is not None


def test_received_locator_recovers_without_regenerate(tmp_path: Path, monkeypatch) -> None:
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        GenerationReconciliationError,
        record_generation_received,
    )

    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-received"))

    def received_then_crash(*args, **kwargs):
        record_generation_received(*args, **kwargs)
        raise GenerationReconciliationError("crash after received", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.record_generation_received",
        received_then_crash,
    )
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-received",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "failure"
    assert first.candidate_ref is not None
    assert first.candidate is not None
    assert len(client.calls) == 1

    monkeypatch.undo()
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-received",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.candidate_id == "cand_fixture1"
    assert len(client.calls) == 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1


def test_expired_pending_claim_does_not_retry_provider(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-expire",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "failure"
    assert first.failure_category == "downstream_timeout"

    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-expire",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["claim_expires_at"] = "2000-01-01T00:00:00Z"
    path.write_text(json.dumps(payload), encoding="utf-8")

    client.error = None
    client.payload = _candidate_payload(request_id="req-expire", candidate_id="cand_retry1")
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-expire",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "failure"
    assert second.failure_category == "generation_incomplete"
    assert "not retryable" in (second.failure_message or "")
    assert len(client.calls) == 1
    abandoned = json.loads(path.read_text(encoding="utf-8"))
    assert abandoned["status"] == "abandoned"


def test_abandoned_records_count_toward_physical_storage_bound(tmp_path: Path) -> None:
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    for index in range(rec.MAX_RECORDS_PER_DRAFT):
        request_id = f"req-abandoned-{index}"
        path = rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=request_id,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        record = rec.GenerationReconciliationRecordV1(
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=request_id,
            request_digest=f"sha256:{'a' * 64}",
            status="abandoned",
            candidate_id=None,
            candidate_payload=None,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            claim_expires_at=None,
        )
        path.write_text(
            json.dumps(record.model_dump(mode="json", by_alias=True)),
            encoding="utf-8",
        )

    client = FakeClient(payload=_candidate_payload(request_id="req-overflow"))
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-overflow",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "integrity_failure"
    assert "storage bound" in (result.failure_message or "")
    assert len(client.calls) == 0

    directory = rec._draft_directory(tmp_path, draft.draft_id)
    assert len(list(directory.glob("v*__*.json"))) == rec.MAX_RECORDS_PER_DRAFT
    listed = rec._list_draft_records_unlocked(tmp_path, draft_id=draft.draft_id)
    assert len(listed) == rec.MAX_RECORDS_PER_DRAFT


def test_finalize_failure_reports_reconciliation_component(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-finalize"))

    def boom_finalize(*args, **kwargs):
        from apps.live_control_server.services.statblock_generation_reconciliation import (
            GenerationReconciliationError,
        )

        raise GenerationReconciliationError(
            "finalize write failed",
            status_code=500,
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.finalize_generation_request",
        boom_finalize,
    )
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-finalize",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.cache_status == "partial_reconciliation"
    assert len(result.persistence_failures) == 1
    assert result.persistence_failures[0].component == "reconciliation"
    assert result.failure_category == "integrity_failure"
    assert "reconciliation:" in (result.failure_message or "")
    assert result.candidate_ref is not None
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1


def test_received_with_existing_ref_does_not_double_count_capacity(
    tmp_path: Path, monkeypatch
) -> None:
    """Finalize failure leaves received+ref; that pair must use one capacity slot."""
    draft = _create_draft(tmp_path)
    for index in range(62):
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )

    def boom_finalize(*args, **kwargs):
        from apps.live_control_server.services.statblock_generation_reconciliation import (
            GenerationReconciliationError,
        )

        raise GenerationReconciliationError("finalize write failed", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.finalize_generation_request",
        boom_finalize,
    )
    first_client = FakeClient(
        payload=_candidate_payload(request_id="req-slot62", candidate_id="cand_slot62")
    )
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-slot62",
        ),
        client=first_client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"
    assert first.cache_status == "partial_reconciliation"
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 63

    # With double-counting, received+ref would look like 64 and block this final slot.
    final_client = FakeClient(
        payload=_candidate_payload(request_id="req-final", candidate_id="cand_final")
    )
    final = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-final",
        ),
        client=final_client,  # type: ignore[arg-type]
    )
    assert final.outcome == "success"
    assert final.cache_status == "partial_reconciliation"
    assert len(final_client.calls) == 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 64


def test_bulk_reconciliation_scan_fails_closed_on_identity_mismatch(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-corrupt",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    # Shape-valid Pydantic payload, but embedded identity disagrees with path.
    corrupt = {
        "schema": "dmb_statblock_generation_request_v1",
        "draft_id": draft.draft_id,
        "draft_version": 2,
        "request_id": "req-corrupt",
        "request_digest": f"sha256:{'b' * 64}",
        "status": "pending",
        "candidate_id": None,
        "candidate_payload": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "claim_expires_at": "2099-01-01T00:00:00Z",
    }
    path.write_text(json.dumps(corrupt), encoding="utf-8")

    client = FakeClient(payload=_candidate_payload(request_id="req-new"))
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-new",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "integrity_failure"
    assert "identity mismatch" in (result.failure_message or "")
    assert len(client.calls) == 0


def test_bulk_reconciliation_scan_fails_closed_on_status_invariant(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-bad-status",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    # Abandoned records must not retain a locator — shape-valid but invariant-breaking.
    corrupt = {
        "schema": "dmb_statblock_generation_request_v1",
        "draft_id": draft.draft_id,
        "draft_version": 1,
        "request_id": "req-bad-status",
        "request_digest": f"sha256:{'c' * 64}",
        "status": "abandoned",
        "candidate_id": "cand_orphan1",
        "candidate_payload": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "claim_expires_at": None,
    }
    path.write_text(json.dumps(corrupt), encoding="utf-8")

    with pytest.raises(rec.GenerationReconciliationError) as exc_info:
        rec._list_draft_records_unlocked(tmp_path, draft_id=draft.draft_id)
    assert exc_info.value.status_code == 500
    assert "corrupt" in str(exc_info.value)


def test_capacity_reservation_blocks_second_request_before_provider(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    for index in range(63):
        append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=1,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )

    release = threading.Event()
    client_a = FakeClient(
        payload=_candidate_payload(request_id="req-a", candidate_id="cand_slota"),
        delay_event=release,
    )
    client_b = FakeClient(
        payload=_candidate_payload(request_id="req-b", candidate_id="cand_slotb"),
    )
    results: dict[str, object] = {}
    barrier = threading.Barrier(2)

    def worker_a() -> None:
        barrier.wait(timeout=2.0)
        try:
            results["a"] = generate_candidate_from_draft(
                tmp_path,
                draft_id=draft.draft_id,
                request=GenerateThreatDraftCandidateRequestV1(
                    expected_draft_version=1,
                    client_request_id="req-a",
                ),
                client=client_a,  # type: ignore[arg-type]
            )
        except ThreatDraftStoreError as exc:
            results["a"] = exc

    def worker_b() -> None:
        barrier.wait(timeout=2.0)
        threading.Event().wait(0.05)
        try:
            results["b"] = generate_candidate_from_draft(
                tmp_path,
                draft_id=draft.draft_id,
                request=GenerateThreatDraftCandidateRequestV1(
                    expected_draft_version=1,
                    client_request_id="req-b",
                ),
                client=client_b,  # type: ignore[arg-type]
            )
        except ThreatDraftStoreError as exc:
            results["b"] = exc

    threads = [
        threading.Thread(target=worker_a),
        threading.Thread(target=worker_b),
    ]
    for thread in threads:
        thread.start()
    threading.Event().wait(0.05)
    release.set()
    for thread in threads:
        thread.join(timeout=3.0)

    assert len(client_a.calls) + len(client_b.calls) == 1
    winner = results["a"] if len(client_a.calls) == 1 else results["b"]
    loser = results["b"] if len(client_a.calls) == 1 else results["a"]
    assert getattr(winner, "outcome", None) == "success"
    assert isinstance(loser, ThreatDraftStoreError)
    assert loser.status_code == 422

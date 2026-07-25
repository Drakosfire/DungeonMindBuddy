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
    """Test double for StatblockV1Client.

    When a generate is already in flight on this instance, a concurrent
    generate raises generation_in_progress (Server PR23 semantics).
    """

    def __init__(self, *, payload=None, error=None, delay_event: threading.Event | None = None):
        self.payload = payload
        self.error = error
        self.delay_event = delay_event
        self.calls: list[dict] = []
        self.get_calls: list[str] = []
        self.lock = threading.Lock()
        self._in_flight = 0

    def generate_candidate(self, body: dict):
        with self.lock:
            self.calls.append(body)
            if self._in_flight > 0 and self.error is None:
                from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
                    downstream_conflict,
                )

                raise downstream_conflict(
                    "Candidate generation is already in progress for this request",
                    status_code=409,
                    error_code="generation_in_progress",
                )
            self._in_flight += 1
        try:
            if self.delay_event is not None:
                self.delay_event.wait(timeout=2.0)
            if self.error is not None:
                raise self.error
            assert self.payload is not None
            return self.payload
        finally:
            with self.lock:
                self._in_flight -= 1

    def get_candidate(self, candidate_id: str):
        self.get_calls.append(candidate_id)
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
    # Owner calls generate; concurrent peer probes Server and may receive
    # generation_in_progress (second call) under PR23 semantics.
    assert len(client.calls) in {1, 2}
    successes = [result for result in results if result.outcome == "success"]
    incompletes = [
        result
        for result in results
        if result.outcome == "failure"
        and result.failure_category == "generation_incomplete"
    ]
    assert len(successes) + len(incompletes) == 2
    assert len(successes) >= 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1


def test_timeout_after_claim_recovers_via_server_replay_on_retry(tmp_path: Path) -> None:
    """Uncertain timeout leaves pending; same request_id re-POSTs and recovers."""
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

    client.error = None
    client.payload = _candidate_payload(request_id="req-timeout", candidate_id="cand_recovered")
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-timeout",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.candidate_id == "cand_recovered"
    assert len(client.calls) == 2
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1


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


def test_timeout_pending_recovers_after_draft_advance(tmp_path: Path) -> None:
    """Pending v1 timeout remains recoverable after the draft advances to v2."""
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-advance",
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
        request_id="req-advance",
    )
    pending = json.loads(path.read_text(encoding="utf-8"))
    assert pending["status"] == "dispatched_unknown"
    assert pending["request_body"] is not None
    assert pending["request_digest"].startswith("sha256:")

    _advance_draft(tmp_path, draft)
    advanced = get_threat_draft(tmp_path, draft.draft_id)
    assert advanced.version == 2

    client.error = None
    client.payload = _candidate_payload(
        request_id="req-advance", candidate_id="cand_afteradvance"
    )
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-advance",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.candidate_id == "cand_afteradvance"
    assert second.candidate_ref.generated_from_draft_version == 1
    assert second.candidate_ref.request_id == "req-advance"
    assert len(client.calls) == 2
    assert client.calls[1]["request_id"] == "req-advance"
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.version == 2
    assert len(reloaded.candidate_refs) == 1


def test_recovered_candidate_without_receipt_request_id_fails_closed(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-noreceipt",
        ),
        client=client,  # type: ignore[arg-type]
    )

    payload = _candidate_payload(request_id="req-noreceipt", candidate_id="cand_noreceipt")
    dumped = payload.model_dump(mode="json")
    dumped["generation_receipt"] = None
    client.error = None
    client.payload = GeneratedStatblockCandidateV1.model_validate(dumped)

    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-noreceipt",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "failure"
    assert second.failure_category == "integrity_failure"
    assert "generation_receipt" in (second.failure_message or "")
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.candidate_refs == []


def test_recovered_candidate_mismatched_receipt_request_id_fails_closed(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(error=downstream_timeout())
    generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-mismatch",
        ),
        client=client,  # type: ignore[arg-type]
    )

    client.error = None
    client.payload = _candidate_payload(
        request_id="req-other", candidate_id="cand_mismatch"
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=1,
                client_request_id="req-mismatch",
            ),
            client=client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 409
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.candidate_refs == []


def test_unresolved_operations_are_never_deleted_for_new_requests(
    tmp_path: Path,
) -> None:
    """New request IDs must not destroy dispatched_unknown recovery bodies."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    recover_id = "req-mustkeep"
    recover_body = map_draft_to_generate_request(draft, request_id=recover_id)
    recover_path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id=recover_id,
    )
    recover_path.parent.mkdir(parents=True, exist_ok=True)
    recover_record = rec.GenerationOperationV2(
        draft_id=draft.draft_id,
        draft_version=1,
        request_id=recover_id,
        request_digest=rec.request_digest_for_body(recover_body),
        request_body=recover_body,
        status="dispatched_unknown",
        candidate_id=None,
        candidate_payload=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        claim_expires_at="2099-01-01T00:00:00Z",
    )
    recover_path.write_text(
        json.dumps(recover_record.model_dump(mode="json", by_alias=True)),
        encoding="utf-8",
    )

    # Fill operation capacity with reconciled records that have draft refs.
    for index in range(rec.MAX_OPERATION_RECORDS_PER_DRAFT - 1):
        request_id = f"req-active-{index}"
        candidate_id = f"cand_shared"
        body = {"request_id": request_id, "marker": index}
        path = rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=request_id,
        )
        if index == 0:
            append_candidate_ref(
                tmp_path,
                draft_id=draft.draft_id,
                expected_version=1,
                candidate_ref=ThreatDraftCandidateRefV1(
                    candidate_id=candidate_id,
                    generated_from_draft_version=1,
                    request_id="req-shared",
                    created_at="2026-01-01T00:00:00Z",
                ),
            )
        payload = _candidate_payload(
            request_id=request_id, candidate_id=candidate_id
        ).model_dump(mode="json")
        record = rec.GenerationOperationV2(
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=request_id,
            request_digest=rec.request_digest_for_body(body),
            request_body=body,
            status="reconciled",
            candidate_id=candidate_id,
            candidate_payload=payload,
            materialization=rec.MaterializationV2(cache="stored", draft_ref="attached"),
            created_at="2026-01-01T00:00:00Z",
            updated_at=f"2026-01-01T00:00:{index:02d}Z",
            claim_expires_at=None,
        )
        path.write_text(
            json.dumps(record.model_dump(mode="json", by_alias=True)),
            encoding="utf-8",
        )

    blocked = FakeClient(payload=_candidate_payload(request_id="req-new"))
    blocked_result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-new",
        ),
        client=blocked,  # type: ignore[arg-type]
    )
    # Compaction of reconciled records may free room; unresolved body must remain.
    assert recover_path.is_file()
    assert json.loads(recover_path.read_text(encoding="utf-8"))["status"] == "dispatched_unknown"
    if blocked_result.outcome == "failure":
        assert "storage bound" in (blocked_result.failure_message or "") or (
            "tombstone bound" in (blocked_result.failure_message or "")
        )
        assert blocked.calls == []

    current = get_threat_draft(tmp_path, draft.draft_id)
    _advance_draft(tmp_path, current)
    assert get_threat_draft(tmp_path, draft.draft_id).version == 2

    client = FakeClient(
        payload=_candidate_payload(request_id=recover_id, candidate_id="cand_kept1")
    )
    recovered = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id=recover_id,
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert recovered.outcome == "success"
    assert recovered.candidate_ref is not None
    assert recovered.candidate_ref.candidate_id == "cand_kept1"
    assert len(client.calls) == 1
    listed = rec._list_draft_entries_unlocked(tmp_path, draft_id=draft.draft_id)
    assert any(
        getattr(item, "request_id", None) == recover_id for item in listed
    )


def test_operation_capacity_refuses_new_work_without_deleting_unresolved(
    tmp_path: Path,
) -> None:
    """Full operation capacity blocks new IDs; unresolved evidence stays recoverable."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    append_candidate_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=1,
        candidate_ref=ThreatDraftCandidateRefV1(
            candidate_id="cand_shared",
            generated_from_draft_version=1,
            request_id="req-shared",
            created_at="2026-01-01T00:00:00Z",
        ),
    )
    oldest_id = "req-unknown-0"
    oldest_body = map_draft_to_generate_request(draft, request_id=oldest_id)
    for index in range(rec.MAX_OPERATION_RECORDS_PER_DRAFT):
        request_id = f"req-unknown-{index}"
        path = rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=request_id,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        if request_id == oldest_id:
            body = oldest_body
            record = rec.GenerationOperationV2(
                draft_id=draft.draft_id,
                draft_version=1,
                request_id=request_id,
                request_digest=rec.request_digest_for_body(body),
                request_body=body,
                status="dispatched_unknown",
                candidate_id=None,
                candidate_payload=None,
                created_at="2026-01-01T00:00:00Z",
                updated_at=f"2026-01-01T00:00:{index:02d}Z",
                claim_expires_at="2099-01-01T00:00:00Z",
            )
        else:
            body = {"request_id": request_id, "marker": index}
            payload = _candidate_payload(
                request_id=request_id, candidate_id="cand_shared"
            ).model_dump(mode="json")
            # Already-attached candidate_id does not inflate ref capacity.
            record = rec.GenerationOperationV2(
                draft_id=draft.draft_id,
                draft_version=1,
                request_id=request_id,
                request_digest=rec.request_digest_for_body(body),
                request_body=body,
                status="candidate_received",
                candidate_id="cand_shared",
                candidate_payload=payload,
                materialization=rec.MaterializationV2(cache="stored", draft_ref="missing"),
                created_at="2026-01-01T00:00:00Z",
                updated_at=f"2026-01-01T00:00:{index:02d}Z",
                claim_expires_at=None,
            )
        path.write_text(
            json.dumps(record.model_dump(mode="json", by_alias=True)),
            encoding="utf-8",
        )

    blocked = FakeClient(payload=_candidate_payload(request_id="req-afterbound"))
    blocked_result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-afterbound",
        ),
        client=blocked,  # type: ignore[arg-type]
    )
    assert blocked_result.outcome == "failure"
    assert "storage bound" in (blocked_result.failure_message or "")
    assert blocked.calls == []

    oldest_path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id=oldest_id,
    )
    assert oldest_path.is_file()
    assert json.loads(oldest_path.read_text(encoding="utf-8"))["status"] == "dispatched_unknown"

    current = get_threat_draft(tmp_path, draft.draft_id)
    _advance_draft(tmp_path, current)
    client = FakeClient(
        payload=_candidate_payload(request_id=oldest_id, candidate_id="cand_oldest1")
    )
    recovered = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id=oldest_id,
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert recovered.outcome == "success"
    assert recovered.candidate is not None
    assert recovered.candidate.candidate_id == "cand_oldest1"
    assert len(client.calls) == 1


def test_compaction_preserves_replay_after_draft_advance(tmp_path: Path) -> None:
    """Reconciled+ref compaction leaves a tombstone that replays after advance."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-compact", candidate_id="cand_comp1"))
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-compact",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"
    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-compact",
    )
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["schema"] == rec.TOMBSTONE_SCHEMA
    assert stored["outcome"] == "reconciled"
    assert stored["candidate_id"] == "cand_comp1"

    _advance_draft(tmp_path, draft)
    second = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-compact",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert second.outcome == "success"
    assert second.candidate is not None
    assert second.candidate.candidate_id == "cand_comp1"
    # No regenerate — tombstone replay uses cache/Server get.
    assert len(client.calls) == 1


def test_candidate_received_never_regresses_under_partial_ref(
    tmp_path: Path,
) -> None:
    """Known candidates stay candidate_received when draft ref attach fails."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

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

    recover_id = "req-partial"
    body = map_draft_to_generate_request(draft, request_id=recover_id)
    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id=recover_id,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            rec.GenerationOperationV2(
                draft_id=draft.draft_id,
                draft_version=1,
                request_id=recover_id,
                request_digest=rec.request_digest_for_body(body),
                request_body=body,
                status="dispatched_unknown",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                claim_expires_at="2099-01-01T00:00:00Z",
            ).model_dump(mode="json", by_alias=True)
        ),
        encoding="utf-8",
    )

    client = FakeClient(
        payload=_candidate_payload(request_id=recover_id, candidate_id="cand_partial1")
    )
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id=recover_id,
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.cache_status == "partial_ref"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["status"] == "candidate_received"
    assert stored["candidate_id"] == "cand_partial1"
    assert stored["materialization"]["draft_ref"] == "failed"


def test_dispatched_unknown_recovery_at_ref_capacity_returns_partial_ref(
    tmp_path: Path,
) -> None:
    """Full draft refs must not block Server recovery of a dispatched_unknown request."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

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

    recover_id = "req-atcap"
    body = map_draft_to_generate_request(draft, request_id=recover_id)
    path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id=recover_id,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    record = rec.GenerationOperationV2(
        draft_id=draft.draft_id,
        draft_version=1,
        request_id=recover_id,
        request_digest=rec.request_digest_for_body(body),
        request_body=body,
        status="dispatched_unknown",
        candidate_id=None,
        candidate_payload=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        claim_expires_at="2099-01-01T00:00:00Z",
    )
    path.write_text(
        json.dumps(record.model_dump(mode="json", by_alias=True)),
        encoding="utf-8",
    )

    client = FakeClient(
        payload=_candidate_payload(request_id=recover_id, candidate_id="cand_recoveredcap")
    )
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id=recover_id,
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "success"
    assert result.cache_status == "partial_ref"
    assert result.candidate_ref is not None
    assert result.candidate_ref.candidate_id == "cand_recoveredcap"
    assert any(item.component == "candidate_ref" for item in result.persistence_failures)
    assert len(client.calls) == 1
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 64
    final = json.loads(path.read_text(encoding="utf-8"))
    assert final["status"] == "candidate_received"
    assert final["candidate_id"] == "cand_recoveredcap"


def test_expired_pending_claim_recovers_via_server_replay(tmp_path: Path) -> None:
    """After pending TTL, same request_id reclaims and recovers via Server replay."""
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
    assert second.outcome == "success"
    assert second.candidate_ref is not None
    assert second.candidate_ref.candidate_id == "cand_retry1"
    assert second.candidate_ref.request_id == "req-expire"
    assert len(client.calls) == 2
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert len(reloaded.candidate_refs) == 1
    final = json.loads(path.read_text(encoding="utf-8"))
    assert final.get("schema") == rec.TOMBSTONE_SCHEMA or final.get("status") in {
        "reconciled",
        "candidate_received",
    }
    if final.get("schema") == rec.TOMBSTONE_SCHEMA:
        assert final["outcome"] == "reconciled"
        assert final["candidate_id"] == "cand_retry1"
    else:
        assert final["candidate_id"] == "cand_retry1"
        assert final.get("request_body") is not None


def test_finalize_failure_reports_reconciliation_component(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _create_draft(tmp_path)
    client = FakeClient(payload=_candidate_payload(request_id="req-finalize"))

    def boom_materialize(*args, **kwargs):
        from apps.live_control_server.services.statblock_generation_reconciliation import (
            GenerationReconciliationError,
        )

        raise GenerationReconciliationError(
            "finalize write failed",
            status_code=500,
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.update_materialization",
        boom_materialize,
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
    """Materialization failure leaves candidate_received+ref; one capacity slot."""
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

    def boom_materialize(*args, **kwargs):
        from apps.live_control_server.services.statblock_generation_reconciliation import (
            GenerationReconciliationError,
        )

        raise GenerationReconciliationError("finalize write failed", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation.update_materialization",
        boom_materialize,
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


def test_tombstone_compaction_never_exceeds_bound(tmp_path: Path) -> None:
    """Compaction updates running tombstone count; never writes an unscannable 513th."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    body = map_draft_to_generate_request(draft, request_id="req-seed")
    digest = rec.request_digest_for_body(body)

    # Seed MAX_TOMBSTONES - 1 terminal tombstones.
    for index in range(rec.MAX_TOMBSTONES_PER_DRAFT - 1):
        path = rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=f"req-tomb-{index}",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                rec.GenerationTombstoneV1(
                    draft_id=draft.draft_id,
                    draft_version=1,
                    request_id=f"req-tomb-{index}",
                    request_digest=digest,
                    outcome="terminal_failure",
                    terminal_code="validation_failed",
                    terminal_message="seed",
                    failure_category="downstream_validation_failed",
                    http_status=422,
                    compaction_proof="operation_terminal",
                    compacted_at="2026-01-01T00:00:00Z",
                ).model_dump(mode="json", by_alias=True)
            ),
            encoding="utf-8",
        )

    # Two eligible terminal full operations that would exceed the bound if counted stale.
    for index in range(2):
        req_id = f"req-eligible-{index}"
        op_body = map_draft_to_generate_request(draft, request_id=req_id)
        path = rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id=req_id,
        )
        path.write_text(
            json.dumps(
                rec.GenerationOperationV2(
                    draft_id=draft.draft_id,
                    draft_version=1,
                    request_id=req_id,
                    request_digest=rec.request_digest_for_body(op_body),
                    request_body=op_body,
                    status="terminal_failure",
                    terminal_code="validation_failed",
                    terminal_message="eligible",
                    failure_category="downstream_validation_failed",
                    http_status=422,
                    created_at="2026-01-01T00:00:00Z",
                    updated_at="2026-01-01T00:00:00Z",
                ).model_dump(mode="json", by_alias=True)
            ),
            encoding="utf-8",
        )

    entries = rec._compact_eligible_for_draft_unlocked(
        tmp_path,
        draft_id=draft.draft_id,
        ref_candidate_ids=set(),
        ref_entries=None,
    )
    tombstones = [e for e in entries if isinstance(e, rec.GenerationTombstoneV1)]
    operations = [e for e in entries if isinstance(e, rec.GenerationOperationV2)]
    assert len(tombstones) <= rec.MAX_TOMBSTONES_PER_DRAFT
    assert len(tombstones) == rec.MAX_TOMBSTONES_PER_DRAFT
    assert len(operations) == 1  # one eligible left uncompacted
    # Store remains scannable (list does not raise).
    listed = rec._list_draft_entries_unlocked(tmp_path, draft_id=draft.draft_id)
    assert len(listed) == rec.MAX_TOMBSTONES_PER_DRAFT + 1


def test_finalize_without_ref_entries_does_not_compact(tmp_path: Path) -> None:
    """Omitted lineage evidence must not authorize reconciled compaction."""
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    payload = _candidate_payload(request_id="req-noproof", candidate_id="cand_noproof")
    body = map_draft_to_generate_request(draft, request_id="req-noproof")
    digest = rec.request_digest_for_body(body)
    rec.claim_generation_request(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-noproof",
        request_digest=digest,
        request_body=body,
        ref_candidate_ids=set(),
    )
    rec.record_candidate_received(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-noproof",
        request_digest=digest,
        candidate=payload,
    )
    # Attach draft ref externally so materialization can become reconciled.
    append_candidate_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=1,
        candidate_ref=ThreatDraftCandidateRefV1(
            candidate_id="cand_noproof",
            generated_from_draft_version=1,
            request_id="req-noproof",
            created_at="2026-01-01T00:00:00Z",
        ),
    )
    result = rec.finalize_generation_request(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-noproof",
        request_digest=digest,
        candidate_id="cand_noproof",
        # intentionally omit ref_entries
    )
    assert isinstance(result, rec.GenerationOperationV2)
    assert result.status == "reconciled"
    stored = json.loads(
        rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id="req-noproof",
        ).read_text(encoding="utf-8")
    )
    assert stored["schema"] == rec.OPERATION_SCHEMA


def test_auth_failure_does_not_terminalize_or_compact(tmp_path: Path) -> None:
    """401/403 are pre-route auth; they must not create operation_terminal tombstones."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_authentication_failed,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    auth_client = FakeClient(
        error=downstream_authentication_failed(status_code=401)
    )
    auth = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-auth",
        ),
        client=auth_client,  # type: ignore[arg-type]
    )
    assert auth.outcome == "failure"
    assert auth.failure_category == "downstream_authentication_failed"
    auth_stored = json.loads(
        rec._record_path(
            tmp_path, draft_id=draft.draft_id, draft_version=1, request_id="req-auth"
        ).read_text(encoding="utf-8")
    )
    assert auth_stored["schema"] == rec.OPERATION_SCHEMA
    assert auth_stored["status"] == "dispatched_unknown"
    assert auth_stored["request_body"] is not None


def test_timeout_then_auth_failure_preserves_recovery_until_auth_repair(
    tmp_path: Path,
) -> None:
    """Timeout may hide Server success; later 401 must not compact away recovery."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_authentication_failed,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    timed_out = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-auth-repair",
        ),
        client=FakeClient(error=downstream_timeout()),  # type: ignore[arg-type]
    )
    assert timed_out.outcome == "failure"
    assert timed_out.failure_category == "downstream_timeout"

    auth_blocked = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-auth-repair",
        ),
        client=FakeClient(error=downstream_authentication_failed(status_code=401)),  # type: ignore[arg-type]
    )
    assert auth_blocked.outcome == "failure"
    assert auth_blocked.failure_category == "downstream_authentication_failed"
    mid = json.loads(
        rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id="req-auth-repair",
        ).read_text(encoding="utf-8")
    )
    assert mid["schema"] == rec.OPERATION_SCHEMA
    assert mid["status"] == "dispatched_unknown"
    assert mid["request_body"] is not None

    repaired = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-auth-repair",
        ),
        client=FakeClient(
            payload=_candidate_payload(
                request_id="req-auth-repair", candidate_id="cand_authrepair"
            )
        ),  # type: ignore[arg-type]
    )
    assert repaired.outcome == "success"
    assert repaired.candidate is not None
    assert repaired.candidate.candidate_id == "cand_authrepair"


def test_durable_provider_failure_terminalizes_and_replays(tmp_path: Path) -> None:
    """Server-durable provider outcomes compact and replay without another call."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_rate_limited,
        downstream_unavailable,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    first_client = FakeClient(
        error=downstream_unavailable(
            "provider timed out",
            status_code=504,
            error_code="provider_timeout",
        )
    )
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-prov-timeout",
        ),
        client=first_client,  # type: ignore[arg-type]
    )
    assert first.outcome == "failure"
    assert first.failure_category == "downstream_unavailable"
    stored = json.loads(
        rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id="req-prov-timeout",
        ).read_text(encoding="utf-8")
    )
    assert stored["schema"] == rec.TOMBSTONE_SCHEMA
    assert stored["outcome"] == "terminal_failure"
    assert stored["terminal_code"] == "provider_timeout"
    assert stored["compaction_proof"] == "operation_terminal"
    assert stored["http_status"] == 504

    replay_client = FakeClient(
        payload=_candidate_payload(request_id="req-prov-timeout")
    )
    replay = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-prov-timeout",
        ),
        client=replay_client,  # type: ignore[arg-type]
    )
    assert replay.outcome == "failure"
    assert replay.failure_category == "downstream_unavailable"
    assert len(replay_client.calls) == 0

    rate_client = FakeClient(
        error=downstream_rate_limited(
            "slow",
            status_code=429,
            error_code="rate_limited",
        )
    )
    rate = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-rate",
        ),
        client=rate_client,  # type: ignore[arg-type]
    )
    assert rate.outcome == "failure"
    assert rate.failure_category == "downstream_rate_limited"
    rate_stored = json.loads(
        rec._record_path(
            tmp_path, draft_id=draft.draft_id, draft_version=1, request_id="req-rate"
        ).read_text(encoding="utf-8")
    )
    assert rate_stored["terminal_code"] == "rate_limited"
    assert rate_stored["compaction_proof"] == "operation_terminal"


def test_server_expired_operation_codes_terminalize_and_replay(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_expired,
        downstream_validation_failed,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    expired_client = FakeClient(
        error=downstream_expired(
            "candidate expired",
            status_code=410,
            error_code="candidate_expired",
        )
    )
    expired = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-exp",
        ),
        client=expired_client,  # type: ignore[arg-type]
    )
    assert expired.outcome == "failure"
    assert expired.failure_category == "downstream_expired"
    exp_stored = json.loads(
        rec._record_path(
            tmp_path, draft_id=draft.draft_id, draft_version=1, request_id="req-exp"
        ).read_text(encoding="utf-8")
    )
    assert exp_stored["outcome"] == "terminal_expired"
    assert exp_stored["terminal_code"] == "candidate_expired"
    assert exp_stored["compaction_proof"] == "operation_terminal"
    assert exp_stored["http_status"] == 410

    expired_replay = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-exp",
        ),
        client=FakeClient(
            error=downstream_validation_failed(
                "should not call", error_code="validation_failed"
            )
        ),  # type: ignore[arg-type]
    )
    assert expired_replay.outcome == "failure"
    assert expired_replay.failure_category == "downstream_expired"


def test_pre_route_validation_without_operation_code_stays_unknown(
    tmp_path: Path,
) -> None:
    """Generic 422 without a Server durable code must not terminalize."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_validation_failed,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    client = FakeClient(
        error=downstream_validation_failed("schema rejected", status_code=422)
    )
    result = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-preroute",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert result.outcome == "failure"
    assert result.failure_category == "downstream_validation_failed"
    stored = json.loads(
        rec._record_path(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=1,
            request_id="req-preroute",
        ).read_text(encoding="utf-8")
    )
    assert stored["schema"] == rec.OPERATION_SCHEMA
    assert stored["status"] == "dispatched_unknown"


def test_idempotency_conflict_tombstone_replays_as_http_409(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_conflict,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    client = FakeClient(
        error=downstream_conflict(
            "idempotency conflict",
            status_code=409,
            error_code="idempotency_conflict",
        )
    )
    with pytest.raises(ThreatDraftStoreError) as first:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=1,
                client_request_id="req-idem",
            ),
            client=client,  # type: ignore[arg-type]
        )
    assert first.value.status_code == 409
    stored = json.loads(
        rec._record_path(
            tmp_path, draft_id=draft.draft_id, draft_version=1, request_id="req-idem"
        ).read_text(encoding="utf-8")
    )
    assert stored["schema"] == rec.TOMBSTONE_SCHEMA
    assert stored["failure_category"] == "idempotency_conflict"
    assert stored["http_status"] == 409

    with pytest.raises(ThreatDraftStoreError) as replay:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=1,
                client_request_id="req-idem",
            ),
            client=FakeClient(payload=_candidate_payload(request_id="req-idem")),  # type: ignore[arg-type]
        )
    assert replay.value.status_code == 409


def test_cold_tombstone_replay_reports_cache_truthfully(tmp_path: Path) -> None:
    """Cache miss + Server GET must not claim cache_status=stored unless written."""
    from apps.live_control_server.services import statblock_candidate_cache as cache
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    client = FakeClient(
        payload=_candidate_payload(request_id="req-cold", candidate_id="cand_cold1")
    )
    first = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-cold",
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert first.outcome == "success"
    assert first.cache_status == "stored"
    stored = json.loads(
        rec._record_path(
            tmp_path, draft_id=draft.draft_id, draft_version=1, request_id="req-cold"
        ).read_text(encoding="utf-8")
    )
    assert stored["schema"] == rec.TOMBSTONE_SCHEMA

    # Evict local cache to force cold tombstone replay.
    cache_path = cache._candidate_path(tmp_path, "cand_cold1")
    assert cache_path.is_file()
    cache_path.unlink()

    cold_client = FakeClient(
        payload=_candidate_payload(request_id="req-cold", candidate_id="cand_cold1")
    )
    replay = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=1,
            client_request_id="req-cold",
        ),
        client=cold_client,  # type: ignore[arg-type]
    )
    assert replay.outcome == "success"
    assert len(cold_client.calls) == 0
    assert cold_client.get_calls == ["cand_cold1"]
    # Write-through succeeded → stored is truthful; never claim stored without write.
    assert replay.cache_status == "stored"
    assert cache_path.is_file()


def test_terminal_journal_write_failure_is_not_swallowed(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
        downstream_validation_failed,
    )
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    client = FakeClient(
        error=downstream_validation_failed(
            "definition invalid",
            status_code=422,
            error_code="validation_failed",
        )
    )

    def boom(*_args, **_kwargs):
        raise rec.GenerationReconciliationError("journal unavailable", status_code=500)

    import apps.live_control_server.services.statblock_candidate_generation as gen

    original = gen.record_terminal
    gen.record_terminal = boom  # type: ignore[assignment]
    try:
        result = generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=1,
                client_request_id="req-jfail",
            ),
            client=client,  # type: ignore[arg-type]
        )
    finally:
        gen.record_terminal = original  # type: ignore[assignment]

    assert result.outcome == "failure"
    assert result.failure_category == "downstream_validation_failed"
    assert any(f.component == "reconciliation" for f in result.persistence_failures)


def _mark_mechanics_saved(tmp_path: Path, draft) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
    )

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
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=current.version,
        locator=ref,
    )


def test_new_generation_rejected_after_mechanics_saved(tmp_path: Path, monkeypatch) -> None:
    draft = _create_draft(tmp_path)
    _mark_mechanics_saved(tmp_path, draft)
    saved = get_threat_draft(tmp_path, draft.draft_id)
    assert saved.workflow_state == "mechanics_saved"
    accepted = saved.accepted_mechanics_ref
    assert accepted is not None

    admit_calls: list[object] = []

    def _boom_admit(*args, **kwargs):
        admit_calls.append(kwargs)
        raise AssertionError("admit must reject before nested claim after mechanics_saved")

    # Patch unlocked claim — admission must reject under the store lock first.
    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_generation."
        "_claim_generation_request_unlocked",
        _boom_admit,
    )
    client = FakeClient(payload=_candidate_payload(request_id="req-new-after-save"))
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        generate_candidate_from_draft(
            tmp_path,
            draft_id=draft.draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=saved.version,
                client_request_id="req-new-after-save",
            ),
            client=client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 409
    assert "mechanics already saved" in str(exc_info.value)
    assert client.calls == []
    assert admit_calls == []
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.workflow_state == "mechanics_saved"
    assert reloaded.accepted_mechanics_ref == accepted


def test_in_flight_generation_recovers_after_mechanics_saved(tmp_path: Path) -> None:
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    recover_id = "req-inflight-after-save"
    recover_body = map_draft_to_generate_request(draft, request_id=recover_id)
    recover_path = rec._record_path(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=draft.version,
        request_id=recover_id,
    )
    recover_path.parent.mkdir(parents=True, exist_ok=True)
    recover_record = rec.GenerationOperationV2(
        draft_id=draft.draft_id,
        draft_version=draft.version,
        request_id=recover_id,
        request_digest=rec.request_digest_for_body(recover_body),
        request_body=recover_body,
        status="dispatched_unknown",
        candidate_id=None,
        candidate_payload=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        claim_expires_at="2099-01-01T00:00:00Z",
    )
    recover_path.write_text(
        json.dumps(recover_record.model_dump(mode="json", by_alias=True)),
        encoding="utf-8",
    )

    _mark_mechanics_saved(tmp_path, draft)
    before = get_threat_draft(tmp_path, draft.draft_id)
    assert before.workflow_state == "mechanics_saved"
    accepted = before.accepted_mechanics_ref
    assert accepted is not None

    client = FakeClient(payload=_candidate_payload(request_id=recover_id))
    recovered = generate_candidate_from_draft(
        tmp_path,
        draft_id=draft.draft_id,
        request=GenerateThreatDraftCandidateRequestV1(
            expected_draft_version=draft.version,
            client_request_id=recover_id,
        ),
        client=client,  # type: ignore[arg-type]
    )
    assert recovered.outcome == "success"
    assert recovered.candidate_ref is not None
    assert len(client.calls) == 1

    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.workflow_state == "mechanics_saved"
    assert after.accepted_mechanics_ref == accepted
    assert any(ref.request_id == recover_id for ref in after.candidate_refs)


def _mp_gen_loses_to_acceptance(
    root_s: str,
    draft_id: str,
    expected_version: int,
    request_id: str,
    observed_s: str,
    go_s: str,
    result_s: str,
) -> None:
    """Observe pre-save draft, pause before admit, then attempt brand-new generation."""
    import time
    from pathlib import Path
    from unittest.mock import patch

    from apps.live_control_server.models.statblock_candidate_workflow import (
        GenerateThreatDraftCandidateRequestV1,
    )
    from apps.live_control_server.services import statblock_candidate_generation as gen
    from apps.live_control_server.services.threat_draft_store import (
        ThreatDraftStoreError,
        get_threat_draft,
    )

    root = Path(root_s)
    observed = Path(observed_s)
    go = Path(go_s)
    result = Path(result_s)

    draft = get_threat_draft(root, draft_id)
    assert draft.workflow_state != "mechanics_saved"
    assert draft.version == expected_version
    observed.write_text("1", encoding="utf-8")

    def _pause_before_admit() -> None:
        deadline = time.time() + 8.0
        while not go.exists() and time.time() < deadline:
            time.sleep(0.01)
        if not go.exists():
            raise TimeoutError("acceptance did not signal go")

    gen._pre_new_generation_admit_hook = _pause_before_admit
    try:
        try:
            with patch.object(
                gen,
                "DungeonMindStatblockV1Client",
                side_effect=AssertionError("Server client must not be constructed"),
            ):
                gen.generate_candidate_from_draft(
                    root,
                    draft_id=draft_id,
                    request=GenerateThreatDraftCandidateRequestV1(
                        expected_draft_version=expected_version,
                        client_request_id=request_id,
                    ),
                    client=None,
                )
            result.write_text(
                json.dumps({"outcome": "unexpected_success"}),
                encoding="utf-8",
            )
        except ThreatDraftStoreError as exc:
            result.write_text(
                json.dumps(
                    {
                        "outcome": "rejected",
                        "status_code": exc.status_code,
                        "message": str(exc),
                    }
                ),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001 — child reports any failure
            result.write_text(
                json.dumps({"outcome": "error", "message": f"{type(exc).__name__}: {exc}"}),
                encoding="utf-8",
            )
    finally:
        gen._pre_new_generation_admit_hook = None


def _mp_acceptance_phase1(
    root_s: str,
    draft_id: str,
    expected_version: int,
    observed_s: str,
    go_s: str,
    result_s: str,
) -> None:
    """Complete acceptance Phase 1 after generation observes pre-save state."""
    import time
    from pathlib import Path

    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
        get_threat_draft,
    )

    root = Path(root_s)
    observed = Path(observed_s)
    go = Path(go_s)
    result = Path(result_s)
    deadline = time.time() + 8.0
    while not observed.exists() and time.time() < deadline:
        time.sleep(0.01)
    if not observed.exists():
        result.write_text(json.dumps({"outcome": "timeout_waiting_observe"}), encoding="utf-8")
        return

    current = get_threat_draft(root, draft_id)
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_race01",
            revision_id="rev_race01",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "b" * 64,
        ),
        accepted_from_draft_version=current.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    updated = attach_accepted_mechanics_ref(
        root,
        draft_id=draft_id,
        expected_version=expected_version,
        locator=ref,
    )
    go.write_text("1", encoding="utf-8")
    result.write_text(
        json.dumps(
            {
                "outcome": "phase1_done",
                "version": updated.version,
                "workflow_state": updated.workflow_state,
            }
        ),
        encoding="utf-8",
    )


def test_generation_versus_acceptance_multiprocess_gen_loses(tmp_path: Path) -> None:
    """Brand-new generation paused before admit loses to Phase 1 → 409, zero side effects."""
    import multiprocessing as mp

    from apps.live_control_server.services import statblock_candidate_cache as cache
    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    request_id = "req-mp-gen-loses"
    barrier = tmp_path / "barrier_gen_loses"
    barrier.mkdir()
    observed = barrier / "observed"
    go = barrier / "go"
    gen_result = barrier / "gen.json"
    accept_result = barrier / "accept.json"

    ctx = mp.get_context("spawn")
    gen_proc = ctx.Process(
        target=_mp_gen_loses_to_acceptance,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            request_id,
            str(observed),
            str(go),
            str(gen_result),
        ),
    )
    accept_proc = ctx.Process(
        target=_mp_acceptance_phase1,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            str(observed),
            str(go),
            str(accept_result),
        ),
    )
    gen_proc.start()
    accept_proc.start()
    gen_proc.join(timeout=15)
    accept_proc.join(timeout=15)
    assert gen_proc.exitcode == 0
    assert accept_proc.exitcode == 0
    assert not gen_proc.is_alive()
    assert not accept_proc.is_alive()

    accepted = json.loads(accept_result.read_text(encoding="utf-8"))
    generated = json.loads(gen_result.read_text(encoding="utf-8"))
    assert accepted["outcome"] == "phase1_done"
    assert accepted["workflow_state"] == "mechanics_saved"
    assert generated["outcome"] == "rejected"
    assert generated["status_code"] == 409
    assert "mechanics already saved" in generated["message"]

    # Losing generation writes no operation/tombstone, cache, or candidate ref.
    entries = list((rec.reconciliation_root(tmp_path) / draft.draft_id).glob("*.json")) if (
        rec.reconciliation_root(tmp_path) / draft.draft_id
    ).is_dir() else []
    assert entries == []
    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.workflow_state == "mechanics_saved"
    assert after.accepted_mechanics_ref is not None
    assert after.candidate_refs == []
    assert list(cache.candidate_cache_root(tmp_path).glob("**/*")) == [] or not any(
        p.is_file() for p in cache.candidate_cache_root(tmp_path).rglob("*")
    )


def _mp_gen_claims_first(
    root_s: str,
    draft_id: str,
    expected_version: int,
    request_id: str,
    claimed_s: str,
    resume_s: str,
    result_s: str,
) -> None:
    """Claim brand-new generation, pause before Server returns, resume after Phase 1."""
    import json
    import time
    from pathlib import Path

    from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
        GeneratedStatblockCandidateV1,
    )
    from apps.live_control_server.models.statblock_candidate_workflow import (
        GenerateThreatDraftCandidateRequestV1,
    )
    from apps.live_control_server.services import statblock_candidate_generation as gen
    from apps.live_control_server.services.threat_draft_store import get_threat_draft

    root = Path(root_s)
    claimed = Path(claimed_s)
    resume = Path(resume_s)
    result = Path(result_s)

    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "statblocks"
        / "v1"
        / "candidate-response.json"
    )
    # When spawned, __file__ may not resolve; fall back via importlib.
    if not fixture_path.is_file():
        import importlib.util

        spec = importlib.util.find_spec("tests.test_statblock_candidate_generation")
        assert spec is not None and spec.origin is not None
        fixture_path = (
            Path(spec.origin).resolve().parent
            / "fixtures"
            / "statblocks"
            / "v1"
            / "candidate-response.json"
        )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    raw = dict(raw)
    raw["candidate_id"] = "cand_mpclaim01"
    raw["expires_at"] = "2099-01-01T00:00:00Z"
    receipt = dict(raw["generation_receipt"])
    receipt["request_id"] = request_id
    raw["generation_receipt"] = receipt
    payload = GeneratedStatblockCandidateV1.model_validate(raw)

    class _CountingClient:
        def __init__(self) -> None:
            self.calls: list[object] = []

        def generate_candidate(self, body):  # noqa: ANN001
            self.calls.append(body)
            claimed.write_text("1", encoding="utf-8")
            deadline = time.time() + 8.0
            while not resume.exists() and time.time() < deadline:
                time.sleep(0.01)
            if not resume.exists():
                raise TimeoutError("acceptance did not signal resume")
            return payload

        def close(self) -> None:
            return None

    client = _CountingClient()
    try:
        outcome = gen.generate_candidate_from_draft(
            root,
            draft_id=draft_id,
            request=GenerateThreatDraftCandidateRequestV1(
                expected_draft_version=expected_version,
                client_request_id=request_id,
            ),
            client=client,  # type: ignore[arg-type]
        )
        after = get_threat_draft(root, draft_id)
        result.write_text(
            json.dumps(
                {
                    "outcome": outcome.outcome,
                    "server_calls": len(client.calls),
                    "workflow_state": after.workflow_state,
                    "accepted_ref": (
                        after.accepted_mechanics_ref.model_dump(mode="json")
                        if after.accepted_mechanics_ref is not None
                        else None
                    ),
                    "candidate_request_ids": [r.request_id for r in after.candidate_refs],
                }
            ),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        result.write_text(
            json.dumps({"outcome": "error", "message": f"{type(exc).__name__}: {exc}"}),
            encoding="utf-8",
        )


def _mp_acceptance_after_claim(
    root_s: str,
    draft_id: str,
    expected_version: int,
    claimed_s: str,
    resume_s: str,
    result_s: str,
) -> None:
    """Phase 1 after generation claim is durable (signaled by Server pause)."""
    import time
    from pathlib import Path

    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
        get_threat_draft,
    )

    root = Path(root_s)
    claimed = Path(claimed_s)
    resume = Path(resume_s)
    result = Path(result_s)
    deadline = time.time() + 8.0
    while not claimed.exists() and time.time() < deadline:
        time.sleep(0.01)
    if not claimed.exists():
        result.write_text(json.dumps({"outcome": "timeout_waiting_claim"}), encoding="utf-8")
        return

    current = get_threat_draft(root, draft_id)
    # Draft version is still the pre-save version; claim keyed to that version.
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_race02",
            revision_id="rev_race02",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "c" * 64,
        ),
        accepted_from_draft_version=current.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    updated = attach_accepted_mechanics_ref(
        root,
        draft_id=draft_id,
        expected_version=expected_version,
        locator=ref,
    )
    locator = updated.accepted_mechanics_ref
    resume.write_text("1", encoding="utf-8")
    result.write_text(
        json.dumps(
            {
                "outcome": "phase1_done",
                "version": updated.version,
                "workflow_state": updated.workflow_state,
                "accepted_ref": locator.model_dump(mode="json") if locator else None,
            }
        ),
        encoding="utf-8",
    )


def test_generation_versus_acceptance_multiprocess_claim_first(tmp_path: Path) -> None:
    """Already-claimed generation remains recoverable after acceptance Phase 1."""
    import multiprocessing as mp

    draft = _create_draft(tmp_path)
    request_id = "req-mp-claim-first"
    barrier = tmp_path / "barrier_claim_first"
    barrier.mkdir()
    claimed = barrier / "claimed"
    resume = barrier / "resume"
    gen_result = barrier / "gen.json"
    accept_result = barrier / "accept.json"

    ctx = mp.get_context("spawn")
    gen_proc = ctx.Process(
        target=_mp_gen_claims_first,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            request_id,
            str(claimed),
            str(resume),
            str(gen_result),
        ),
    )
    accept_proc = ctx.Process(
        target=_mp_acceptance_after_claim,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            str(claimed),
            str(resume),
            str(accept_result),
        ),
    )
    gen_proc.start()
    accept_proc.start()
    gen_proc.join(timeout=20)
    accept_proc.join(timeout=20)
    assert gen_proc.exitcode == 0
    assert accept_proc.exitcode == 0
    assert not gen_proc.is_alive()
    assert not accept_proc.is_alive()

    accepted = json.loads(accept_result.read_text(encoding="utf-8"))
    generated = json.loads(gen_result.read_text(encoding="utf-8"))
    assert accepted["outcome"] == "phase1_done"
    assert accepted["workflow_state"] == "mechanics_saved"
    assert generated["outcome"] == "success"
    assert generated["server_calls"] == 1
    assert generated["workflow_state"] == "mechanics_saved"
    assert generated["accepted_ref"] == accepted["accepted_ref"]
    assert request_id in generated["candidate_request_ids"]

    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.workflow_state == "mechanics_saved"
    assert after.accepted_mechanics_ref is not None
    assert after.accepted_mechanics_ref.model_dump(mode="json") == accepted["accepted_ref"]
    assert any(ref.request_id == request_id for ref in after.candidate_refs)


def _mp_same_key_retry_b(
    root_s: str,
    draft_id: str,
    expected_version: int,
    request_id: str,
    empty_s: str,
    go_s: str,
    result_s: str,
) -> None:
    """Retry B: empty optimistic journal, pause before admit, then same-key recover."""
    import time
    from pathlib import Path

    from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
        GeneratedStatblockCandidateV1,
    )
    from apps.live_control_server.models.statblock_candidate_workflow import (
        GenerateThreatDraftCandidateRequestV1,
    )
    from apps.live_control_server.services import statblock_candidate_generation as gen
    from apps.live_control_server.services.threat_draft_store import (
        ThreatDraftStoreError,
        get_threat_draft,
    )

    root = Path(root_s)
    empty = Path(empty_s)
    go = Path(go_s)
    result = Path(result_s)

    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "statblocks"
        / "v1"
        / "candidate-response.json"
    )
    if not fixture_path.is_file():
        import importlib.util

        spec = importlib.util.find_spec("tests.test_statblock_candidate_generation")
        assert spec is not None and spec.origin is not None
        fixture_path = (
            Path(spec.origin).resolve().parent
            / "fixtures"
            / "statblocks"
            / "v1"
            / "candidate-response.json"
        )
    raw = dict(json.loads(fixture_path.read_text(encoding="utf-8")))
    raw["candidate_id"] = "cand_mpsame01"
    raw["expires_at"] = "2099-01-01T00:00:00Z"
    receipt = dict(raw["generation_receipt"])
    receipt["request_id"] = request_id
    raw["generation_receipt"] = receipt
    payload = GeneratedStatblockCandidateV1.model_validate(raw)

    class _Client:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def generate_candidate(self, body):  # noqa: ANN001
            self.calls.append(body)
            return payload

        def close(self) -> None:
            return None

    def _pause_before_admit() -> None:
        # Reached only after optimistic journal miss; signal before atomic admit.
        empty.write_text("1", encoding="utf-8")
        deadline = time.time() + 10.0
        while not go.exists() and time.time() < deadline:
            time.sleep(0.01)
        if not go.exists():
            raise TimeoutError("acceptance did not signal go")

    client = _Client()
    gen._pre_new_generation_admit_hook = _pause_before_admit
    try:
        try:
            outcome = gen.generate_candidate_from_draft(
                root,
                draft_id=draft_id,
                request=GenerateThreatDraftCandidateRequestV1(
                    expected_draft_version=expected_version,
                    client_request_id=request_id,
                ),
                client=client,  # type: ignore[arg-type]
            )
            after = get_threat_draft(root, draft_id)
            result.write_text(
                json.dumps(
                    {
                        "outcome": outcome.outcome,
                        "status_code": None,
                        "message": None,
                        "server_calls": len(client.calls),
                        "server_bodies": client.calls,
                        "workflow_state": after.workflow_state,
                        "accepted_ref": (
                            after.accepted_mechanics_ref.model_dump(mode="json")
                            if after.accepted_mechanics_ref is not None
                            else None
                        ),
                    }
                ),
                encoding="utf-8",
            )
        except ThreatDraftStoreError as exc:
            result.write_text(
                json.dumps(
                    {
                        "outcome": "rejected",
                        "status_code": exc.status_code,
                        "message": str(exc),
                        "server_calls": len(client.calls),
                        "server_bodies": client.calls,
                    }
                ),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            result.write_text(
                json.dumps({"outcome": "error", "message": f"{type(exc).__name__}: {exc}"}),
                encoding="utf-8",
            )
    finally:
        gen._pre_new_generation_admit_hook = None


def _mp_same_key_claimer_a(
    root_s: str,
    draft_id: str,
    expected_version: int,
    request_id: str,
    empty_s: str,
    claimed_s: str,
    result_s: str,
) -> None:
    """Caller A: after B sees empty journal, durably claim the same key/body."""
    import time
    from pathlib import Path

    from apps.live_control_server.services.statblock_candidate_generation import (
        map_draft_to_generate_request,
    )
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        claim_generation_request,
        request_digest_for_body,
    )
    from apps.live_control_server.services.threat_draft_store import get_threat_draft

    root = Path(root_s)
    empty = Path(empty_s)
    claimed = Path(claimed_s)
    result = Path(result_s)
    deadline = time.time() + 10.0
    while not empty.exists() and time.time() < deadline:
        time.sleep(0.01)
    if not empty.exists():
        result.write_text(json.dumps({"outcome": "timeout_waiting_empty"}), encoding="utf-8")
        return

    draft = get_threat_draft(root, draft_id)
    body = map_draft_to_generate_request(draft, request_id=request_id)
    digest = request_digest_for_body(body)
    status, record = claim_generation_request(
        root,
        draft_id=draft_id,
        draft_version=expected_version,
        request_id=request_id,
        request_digest=digest,
        request_body=body,
        ref_candidate_ids=set(),
        ref_entries=[],
    )
    claimed.write_text("1", encoding="utf-8")
    result.write_text(
        json.dumps(
            {
                "outcome": "claimed",
                "claim_status": status,
                "request_id": record.request_id,
                "draft_id": record.draft_id,
                "draft_version": record.draft_version,
                "request_digest": record.request_digest,
                "request_body": record.request_body,
            }
        ),
        encoding="utf-8",
    )


def _mp_same_key_acceptance(
    root_s: str,
    draft_id: str,
    expected_version: int,
    claimed_s: str,
    go_s: str,
    result_s: str,
) -> None:
    """Phase 1 after A’s same-key claim is durable; then release retry B."""
    import time
    from pathlib import Path

    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
        get_threat_draft,
    )

    root = Path(root_s)
    claimed = Path(claimed_s)
    go = Path(go_s)
    result = Path(result_s)
    deadline = time.time() + 10.0
    while not claimed.exists() and time.time() < deadline:
        time.sleep(0.01)
    if not claimed.exists():
        result.write_text(json.dumps({"outcome": "timeout_waiting_claim"}), encoding="utf-8")
        return

    current = get_threat_draft(root, draft_id)
    ref = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_samekey01",
            revision_id="rev_samekey01",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "d" * 64,
        ),
        accepted_from_draft_version=current.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    updated = attach_accepted_mechanics_ref(
        root,
        draft_id=draft_id,
        expected_version=expected_version,
        locator=ref,
    )
    locator = updated.accepted_mechanics_ref
    go.write_text("1", encoding="utf-8")
    result.write_text(
        json.dumps(
            {
                "outcome": "phase1_done",
                "workflow_state": updated.workflow_state,
                "accepted_ref": locator.model_dump(mode="json") if locator else None,
            }
        ),
        encoding="utf-8",
    )


def test_same_key_retry_recovers_after_peer_claim_and_acceptance(tmp_path: Path) -> None:
    """Optimistic-empty retry must reclassify under locks, not return new-gen 409."""
    import multiprocessing as mp

    from apps.live_control_server.services import statblock_generation_reconciliation as rec

    draft = _create_draft(tmp_path)
    request_id = "req-mp-same-key"
    barrier = tmp_path / "barrier_same_key"
    barrier.mkdir()
    empty = barrier / "empty"
    claimed = barrier / "claimed"
    go = barrier / "go"
    b_result = barrier / "b.json"
    a_result = barrier / "a.json"
    accept_result = barrier / "accept.json"

    ctx = mp.get_context("spawn")
    b_proc = ctx.Process(
        target=_mp_same_key_retry_b,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            request_id,
            str(empty),
            str(go),
            str(b_result),
        ),
    )
    a_proc = ctx.Process(
        target=_mp_same_key_claimer_a,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            request_id,
            str(empty),
            str(claimed),
            str(a_result),
        ),
    )
    accept_proc = ctx.Process(
        target=_mp_same_key_acceptance,
        args=(
            str(tmp_path),
            draft.draft_id,
            draft.version,
            str(claimed),
            str(go),
            str(accept_result),
        ),
    )
    b_proc.start()
    a_proc.start()
    accept_proc.start()
    b_proc.join(timeout=20)
    a_proc.join(timeout=20)
    accept_proc.join(timeout=20)
    assert b_proc.exitcode == 0
    assert a_proc.exitcode == 0
    assert accept_proc.exitcode == 0
    assert not b_proc.is_alive()
    assert not a_proc.is_alive()
    assert not accept_proc.is_alive()

    a = json.loads(a_result.read_text(encoding="utf-8"))
    b = json.loads(b_result.read_text(encoding="utf-8"))
    accepted = json.loads(accept_result.read_text(encoding="utf-8"))

    assert a["outcome"] == "claimed"
    assert a["claim_status"] == "claimed"
    assert accepted["outcome"] == "phase1_done"
    assert accepted["workflow_state"] == "mechanics_saved"
    assert b["outcome"] == "success"
    assert b["status_code"] is None
    assert b["server_calls"] == 1
    assert b["server_bodies"] == [a["request_body"]]
    assert b["workflow_state"] == "mechanics_saved"
    assert b["accepted_ref"] == accepted["accepted_ref"]

    draft_dir = rec.reconciliation_root(tmp_path) / draft.draft_id
    entries = sorted(p for p in draft_dir.glob("*.json") if p.is_file())
    assert len(entries) == 1
    stored = json.loads(entries[0].read_text(encoding="utf-8"))
    assert stored["request_id"] == request_id
    assert stored["draft_id"] == draft.draft_id
    assert stored["draft_version"] == draft.version
    assert stored["request_digest"] == a["request_digest"]
    if "request_body" in stored:
        assert stored["request_body"] == a["request_body"]
    else:
        # Successful recovery may compact to a tombstone; digest/outcome remain.
        assert stored.get("schema") == rec.TOMBSTONE_SCHEMA
        assert stored.get("outcome") in {"reconciled", "terminal_failure", "terminal_expired"}

    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.workflow_state == "mechanics_saved"
    assert after.accepted_mechanics_ref is not None
    assert after.accepted_mechanics_ref.model_dump(mode="json") == accepted["accepted_ref"]

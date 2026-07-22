from __future__ import annotations

import json
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


class FakeClient:
    def __init__(self, *, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls: list[dict] = []

    def generate_candidate(self, body: dict):
        self.calls.append(body)
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
    # Mutate authored fields (version stays 1? No - update increments version.
    # Replay conflict is same version + same request_id + different mapped body.
    # Force by changing only the digest check via a second call after we can't
    # change draft without version bump. Instead, corrupt is not needed:
    # same draft version with same request id always same digest.
    # Conflict path: write a reconciliation with a different digest manually.
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        write_reconciliation,
    )

    write_reconciliation(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=1,
        request_id="req-other",
        request_digest="sha256:" + ("a" * 64),
        candidate_id="cand_fixture1",
    )
    # Overwrite digest in place for req-conflict by writing conflicting record
    # through a second write with different digest is blocked; simulate by
    # reading and replacing file.
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


def test_cache_rejects_conflicting_payload(tmp_path: Path) -> None:
    first = _candidate_payload(candidate_id="cand_cache1", request_id="req-a")
    store_candidate_payload(tmp_path, first)
    second = _candidate_payload(candidate_id="cand_cache1", request_id="req-b")
    with pytest.raises(CandidateCacheError) as exc_info:
        store_candidate_payload(tmp_path, second)
    assert exc_info.value.status_code == 409


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

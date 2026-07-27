"""SBW06a revise journal, adapter, and no-mutation proofs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    ReviseCandidateRequestV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.statblock_candidate_revision import (
    ReviseCandidateFromEditedDefinitionRequestV1,
    instruction_options_digest,
    map_edited_definition_to_revise_server_body,
    normalize_revision_instructions,
    revise_request_digest_for_server_body,
    source_definition_digest_from_body,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
)
from apps.live_control_server.services.statblock_candidate_cache import CandidateCacheError
from apps.live_control_server.services.statblock_candidate_revision import (
    ReviseCandidateRevisionError,
    revise_candidate_from_edited_definition,
)
from apps.live_control_server.services.statblock_revise_reconciliation import (
    ReviseReconciliationError,
    claim_revise_operation,
    get_revise_operation,
    write_ahead_dispatched_unknown,
)
from apps.live_control_server.services.threat_draft_store import (
    create_threat_draft,
    get_threat_draft,
)

FIXTURES = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
REVISE_FIXTURES = FIXTURES / "server_revise_transcripts"


def _revise_request() -> ReviseCandidateRequestV1:
    return ReviseCandidateRequestV1.model_validate(
        json.loads((REVISE_FIXTURES / "revise-request.json").read_text(encoding="utf-8"))
    )


def _revise_response() -> GeneratedStatblockCandidateV1:
    return GeneratedStatblockCandidateV1.model_validate(
        json.loads((REVISE_FIXTURES / "revise-replay-response.json").read_text(encoding="utf-8"))
    )


def _create_draft(tmp_path: Path):
    return create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Test",
            description="Desc",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_g1"),
            created_by="gm",
        ),
    )


def _service_request(
    draft, *, request_id: str = "fixture-revise-source-def-1"
) -> ReviseCandidateFromEditedDefinitionRequestV1:
    typed = _revise_request()
    assert typed.source_definition is not None
    return ReviseCandidateFromEditedDefinitionRequestV1(
        request_id=request_id,
        expected_draft_version=draft.version,
        editor_state_revision="editor-rev-1",
        source_definition=typed.source_definition,
        revision_instructions=list(typed.revision_instructions),
        preserve_element_keys=typed.preserve_element_keys,
        ruleset=typed.ruleset,
        actor=typed.actor,
    )


def _body_and_digests(
    request: ReviseCandidateFromEditedDefinitionRequestV1,
) -> tuple[dict[str, Any], str, str, str]:
    body = map_edited_definition_to_revise_server_body(request)
    normalized = normalize_revision_instructions(request.revision_instructions)
    return (
        body,
        revise_request_digest_for_server_body(body),
        source_definition_digest_from_body(body["source_definition"]),
        instruction_options_digest(normalized, request.preserve_element_keys),
    )


def test_write_ahead_before_dispatch_from_claimed(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    outcome, op = claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    assert outcome == "claimed"
    assert op is not None and op.status == "claimed"
    advanced = write_ahead_dispatched_unknown(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=digest,
    )
    assert advanced.status == "dispatched_unknown"


def test_same_key_input_conflict_zero_mutation(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    mutated = dict(body)
    mutated["revision_instructions"] = ["Different instruction."]
    new_digest = revise_request_digest_for_server_body(mutated)
    outcome, existing = claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=new_digest,
        request_body=mutated,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    assert outcome == "revise_input_conflict"
    assert existing is not None
    assert existing.request_body == body


def test_revise_busy_blocks_second_request_id(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft, request_id="revise-a")
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    req2 = _service_request(draft, request_id="revise-b")
    body2, digest2, src2, instr2 = _body_and_digests(req2)
    outcome, _ = claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req2.request_id,
        request_digest=digest2,
        request_body=body2,
        editor_state_revision=req2.editor_state_revision,
        source_definition_digest=src2,
        instruction_options_digest=instr2,
    )
    assert outcome == "revise_busy"


def test_happy_path_reconciles_with_lineage_and_one_version_bump(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    before = get_threat_draft(tmp_path, draft.draft_id)
    req = _service_request(draft)
    response_fixture = _revise_response()

    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture

    result = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert result.result == "reconciled"
    assert result.operation_status == "reconciled"
    assert result.candidate_id == response_fixture.candidate_id

    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.version == before.version + 1
    assert len(after.candidate_refs) == 1
    attached = after.candidate_refs[0]
    assert attached.candidate_id == response_fixture.candidate_id
    assert attached.lineage is not None
    assert attached.lineage.source_origin_kind == "edited_working_copy"
    assert attached.lineage.revise_request_id == req.request_id

    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "reconciled"
    assert stored.materialization.draft_ref == "attached"
    assert stored.materialization.source_status == "none"
    client.revise_candidate.assert_called_once()


def test_replay_resumes_without_second_post_when_candidate_known(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()

    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture

    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"
    version_after_first = get_threat_draft(tmp_path, draft.draft_id).version
    client.revise_candidate.reset_mock()

    second = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert second.result == "reconciled"
    assert get_threat_draft(tmp_path, draft.draft_id).version == version_after_first
    client.revise_candidate.assert_not_called()


def test_write_ahead_failure_makes_zero_server_posts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )

    def _boom(*_args, **_kwargs):
        raise ReviseReconciliationError("injected write-ahead failure", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_revision.write_ahead_dispatched_unknown",
        _boom,
    )
    client = MagicMock()
    with pytest.raises(ReviseReconciliationError, match="write-ahead"):
        revise_candidate_from_edited_definition(
            tmp_path,
            draft_id=draft.draft_id,
            request=req,
            client=client,
        )
    client.revise_candidate.assert_not_called()
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None and stored.status == "claimed"


def test_lost_response_same_key_replay_posts_stored_body(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.side_effect = [
        StatblockIntegrationError(
            category="timeout",
            message="injected timeout",
            status_code=504,
            retryable=True,
        ),
        response_fixture,
    ]
    client.get_candidate.return_value = response_fixture

    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "dispatched_unknown"
    assert first.candidate_id is None
    assert client.revise_candidate.call_count == 1

    second = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert second.result == "reconciled"
    assert second.candidate_id == response_fixture.candidate_id
    assert client.revise_candidate.call_count == 2
    posted = client.revise_candidate.call_args_list[1].args[0]
    assert posted["request_id"] == req.request_id
    assert posted["revision_instructions"] == list(req.revision_instructions)


def test_cache_failure_leaves_candidate_received_without_draft_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = _create_draft(tmp_path)
    before = get_threat_draft(tmp_path, draft.draft_id)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture

    def _fail_store(*_args, **_kwargs):
        raise CandidateCacheError("injected cache failure", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_revision.store_candidate_payload",
        _fail_store,
    )
    result = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert result.result == "candidate_received"
    assert result.candidate_id == response_fixture.candidate_id
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "candidate_received"
    assert stored.materialization.cache == "failed"
    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.candidate_refs == before.candidate_refs


def test_history_full_when_generation_reservations_saturate(tmp_path: Path) -> None:
    from apps.live_control_server.models.threat_draft import (
        MAX_CANDIDATE_REFS,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services.statblock_candidate_generation import (
        map_draft_to_generate_request,
    )
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        claim_generation_request,
        request_digest_for_body,
    )
    from apps.live_control_server.services.threat_draft_store import append_candidate_ref

    draft = _create_draft(tmp_path)
    version = draft.version
    for index in range(MAX_CANDIDATE_REFS - 1):
        draft = append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=version,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
        version = draft.version

    gen_body = map_draft_to_generate_request(draft, request_id="gen-saturate")
    gen_digest = request_digest_for_body(gen_body)
    ref_ids = {ref.candidate_id for ref in draft.candidate_refs}
    claim_generation_request(
        tmp_path,
        draft_id=draft.draft_id,
        draft_version=draft.version,
        request_id="gen-saturate",
        request_digest=gen_digest,
        request_body=gen_body,
        ref_candidate_ids=ref_ids,
        ref_entries=[],
    )
    req = _service_request(draft)
    result = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=MagicMock(),
    )
    assert result.result == "revise_history_full"
    assert result.operation_status is None
    assert (
        get_revise_operation(tmp_path, draft_id=draft.draft_id, request_id=req.request_id)
        is None
    )


def test_generation_blocked_when_revise_holds_final_slot(tmp_path: Path) -> None:
    from apps.live_control_server.models.threat_draft import (
        MAX_CANDIDATE_REFS,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services.statblock_candidate_generation import (
        map_draft_to_generate_request,
    )
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        GenerationReconciliationError,
        claim_generation_request,
        request_digest_for_body,
    )
    from apps.live_control_server.services.threat_draft_store import append_candidate_ref

    draft = _create_draft(tmp_path)
    version = draft.version
    for index in range(MAX_CANDIDATE_REFS - 1):
        draft = append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=version,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
        version = draft.version

    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    ref_ids = {ref.candidate_id for ref in draft.candidate_refs}
    outcome, _ = claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    assert outcome == "claimed"

    gen_body = map_draft_to_generate_request(draft, request_id="gen-after-revise")
    gen_digest = request_digest_for_body(gen_body)
    with pytest.raises(GenerationReconciliationError, match="candidate_refs limit"):
        claim_generation_request(
            tmp_path,
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id="gen-after-revise",
            request_digest=gen_digest,
            request_body=gen_body,
            ref_candidate_ids=ref_ids,
            ref_entries=[],
        )


def test_concurrent_final_slot_admits_exactly_one(tmp_path: Path) -> None:
    """Race production revise claim vs production generation admission.

    Both paths must take ThreatDraft store → capacity → journal so they cannot
    deadlock or overbook the final slot.
    """
    import threading

    from apps.live_control_server.models.threat_draft import (
        MAX_CANDIDATE_REFS,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services import statblock_candidate_generation as gen_svc
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        GenerationReconciliationError,
    )
    from apps.live_control_server.services.threat_draft_store import (
        ThreatDraftStoreError,
        append_candidate_ref,
    )

    draft = _create_draft(tmp_path)
    version = draft.version
    for index in range(MAX_CANDIDATE_REFS - 1):
        draft = append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=version,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
        version = draft.version

    req = _service_request(draft, request_id="revise-final-slot")
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def claim_revise() -> None:
        barrier.wait(timeout=5)
        try:
            outcome, _ = claim_revise_operation(
                tmp_path,
                draft_id=draft.draft_id,
                expected_draft_version=draft.version,
                request_id=req.request_id,
                request_digest=digest,
                request_body=body,
                editor_state_revision=req.editor_state_revision,
                source_definition_digest=src_digest,
                instruction_options_digest=instr_digest,
            )
            results["revise"] = outcome
        except Exception as exc:  # noqa: BLE001 — surface in assertion
            results["revise"] = f"error:{type(exc).__name__}:{exc}"

    def claim_generation() -> None:
        barrier.wait(timeout=5)
        try:
            gen_svc._admit_and_claim_new_generation(
                tmp_path,
                draft_id=draft.draft_id,
                expected_draft_version=draft.version,
                request_id="gen-final-slot",
            )
            results["generation"] = "claimed"
        except GenerationReconciliationError as exc:
            results["generation"] = f"rejected:{exc}"
        except ThreatDraftStoreError as exc:
            results["generation"] = f"rejected:{exc}"
        except Exception as exc:  # noqa: BLE001
            results["generation"] = f"error:{type(exc).__name__}:{exc}"

    threads = [
        threading.Thread(target=claim_revise),
        threading.Thread(target=claim_generation),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    successes = 0
    if results.get("revise") == "claimed":
        successes += 1
    if results.get("generation") == "claimed":
        successes += 1
    assert successes == 1, results
    assert results.get("revise") in {"claimed", "revise_history_full"}, results
    assert results.get("generation") == "claimed" or (
        isinstance(results.get("generation"), str)
        and "candidate_refs limit exceeded" in results["generation"]
    ), results


def test_revise_admission_sees_ref_appended_under_store_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Candidate refs observed for capacity must be read under the store lock.

    Simulate a ref becoming durable before revise's in-boundary draft load so
    admission cannot decide against a stale pre-claim snapshot.
    """
    from apps.live_control_server.models.threat_draft import (
        MAX_CANDIDATE_REFS,
        ThreatDraftCandidateRefV1,
    )
    from apps.live_control_server.services import statblock_revise_reconciliation as revise_mod
    from apps.live_control_server.services import threat_draft_store as store_mod
    from apps.live_control_server.services.threat_draft_store import append_candidate_ref

    draft = _create_draft(tmp_path)
    version = draft.version
    for index in range(MAX_CANDIDATE_REFS - 1):
        draft = append_candidate_ref(
            tmp_path,
            draft_id=draft.draft_id,
            expected_version=version,
            candidate_ref=ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{index}",
                generated_from_draft_version=1,
                request_id=f"req-{index}",
                created_at="2026-01-01T00:00:00Z",
            ),
        )
        version = draft.version

    original_load = store_mod._load_draft_unlocked
    injected = {"done": False}

    def load_and_inject(root: Path, draft_id: str):
        draft_obj = original_load(root, draft_id)
        if injected["done"] or len(draft_obj.candidate_refs) >= MAX_CANDIDATE_REFS:
            return draft_obj
        refs = list(draft_obj.candidate_refs)
        refs.append(
            ThreatDraftCandidateRefV1(
                candidate_id=f"cand_{MAX_CANDIDATE_REFS - 1}",
                generated_from_draft_version=1,
                request_id="req-final",
                created_at="2026-01-01T00:00:00Z",
            )
        )
        updated = draft_obj.model_copy(
            update={"candidate_refs": refs, "updated_at": "2026-01-01T00:00:01Z"}
        )
        store_mod._save_draft_unlocked(root, updated, as_draft_id=draft_obj.draft_id)
        injected["done"] = True
        return original_load(root, draft_id)

    monkeypatch.setattr(store_mod, "_load_draft_unlocked", load_and_inject)
    monkeypatch.setattr(revise_mod, "_load_draft_unlocked", load_and_inject)

    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    outcome, op = claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    assert outcome == "revise_history_full"
    assert op is None
    assert injected["done"] is True


def test_actor_included_in_revise_request_digest() -> None:
    draft_req = _revise_request()
    assert draft_req.source_definition is not None
    base = ReviseCandidateFromEditedDefinitionRequestV1(
        request_id="actor-digest-1",
        expected_draft_version=1,
        editor_state_revision="editor-rev-1",
        source_definition=draft_req.source_definition,
        revision_instructions=list(draft_req.revision_instructions),
        preserve_element_keys=draft_req.preserve_element_keys,
        ruleset=draft_req.ruleset,
        actor="alice",
    )
    body_a = map_edited_definition_to_revise_server_body(base)
    body_b = dict(body_a)
    body_b["actor"] = "bob"
    assert revise_request_digest_for_server_body(body_a) != revise_request_digest_for_server_body(
        body_b
    )


def test_existing_authority_replay_skips_client_and_missing_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing draft on reconciled replay is unavailable, not integrity conflict."""
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"

    def boom_client() -> None:
        raise AssertionError("client must not be constructed for reconciled replay")

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_revision.build_statblock_v1_client",
        boom_client,
    )
    # Delete the draft file after claim so draft re-proof cannot succeed.
    draft_path = (
        tmp_path / "out" / "threat_drafts" / f"{draft.draft_id}.json"
    )
    if draft_path.is_file():
        draft_path.unlink()
    else:
        candidates = list((tmp_path / "out").rglob(f"*{draft.draft_id}*.json"))
        for path in candidates:
            if "threat_draft" in str(path) or "draft" in path.name:
                path.unlink(missing_ok=True)

    replay = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=None,
    )
    assert replay.result == "revise_draft_unavailable"


def test_changed_body_conflict_without_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_candidate_revision.build_statblock_v1_client",
        lambda: (_ for _ in ()).throw(AssertionError("no client")),
    )
    mutated = req.model_copy(update={"revision_instructions": ["Changed instruction."]})
    result = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=mutated,
        client=None,
    )
    assert result.result == "revise_input_conflict"


def test_cache_stored_ref_pending_repairs_missing_cache_via_get(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.models.statblock_candidate_revision import (
        ReviseMaterializationV1,
    )
    from apps.live_control_server.services.statblock_candidate_cache import (
        candidate_cache_root,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        _write_operation_unlocked,
    )

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture

    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"

    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    pending = stored.model_copy(
        update={
            "status": "cache_stored_ref_pending",
            "materialization": ReviseMaterializationV1(
                cache="stored",
                draft_ref="missing",
                source_status="none",
            ),
        }
    )
    _write_operation_unlocked(tmp_path, pending)

    cache_path = (
        candidate_cache_root(tmp_path) / f"{response_fixture.candidate_id}.json"
    )
    assert cache_path.is_file()
    cache_path.unlink()
    client.revise_candidate.reset_mock()
    client.get_candidate.reset_mock()

    repaired = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert repaired.result == "reconciled"
    client.revise_candidate.assert_not_called()
    client.get_candidate.assert_called_once_with(response_fixture.candidate_id)
    assert cache_path.is_file()
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "reconciled"
    assert stored.materialization.cache == "stored"


def test_cache_stored_ref_pending_demotes_when_get_repair_fails(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.models.statblock_candidate_revision import (
        ReviseMaterializationV1,
    )
    from apps.live_control_server.services.statblock_candidate_cache import (
        candidate_cache_root,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        _write_operation_unlocked,
    )

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture

    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    _write_operation_unlocked(
        tmp_path,
        stored.model_copy(
            update={
                "status": "cache_stored_ref_pending",
                "materialization": ReviseMaterializationV1(
                    cache="stored",
                    draft_ref="missing",
                    source_status="none",
                ),
            }
        ),
    )
    cache_path = (
        candidate_cache_root(tmp_path) / f"{response_fixture.candidate_id}.json"
    )
    cache_path.unlink()
    client.get_candidate.side_effect = StatblockIntegrationError(
        category="downstream_not_found",
        message="candidate gone",
        status_code=404,
        retryable=False,
    )

    demoted = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert demoted.result == "candidate_received"
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "candidate_received"
    assert stored.materialization.cache == "failed"
    assert stored.candidate_id == response_fixture.candidate_id
    client.revise_candidate.assert_called_once()


def test_unbound_get_candidate_does_not_reach_cache_stored(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    write_ahead_dispatched_unknown(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=digest,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        record_candidate_received,
    )

    record_candidate_received(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=digest,
        candidate_id=response_fixture.candidate_id,
    )

    unbound = response_fixture.model_copy(
        deep=True,
        update={
            "generation_receipt": response_fixture.generation_receipt.model_copy(
                update={"request_id": "other-request-id"}
            )
        },
    )
    client = MagicMock()
    client.get_candidate.return_value = unbound

    result = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert result.result == "candidate_received"
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "candidate_received"
    assert stored.materialization.cache == "failed"
    client.revise_candidate.assert_not_called()


def test_unbound_post_candidate_rejects_before_journal_candidate(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    unbound = response_fixture.model_copy(
        deep=True,
        update={
            "generation_receipt": response_fixture.generation_receipt.model_copy(
                update={
                    "source_definition_digest": (
                        "sha256:0000000000000000000000000000000000000000000000000000000000000000"
                    )
                }
            )
        },
    )
    client = MagicMock()
    client.revise_candidate.return_value = unbound

    with pytest.raises(ReviseCandidateRevisionError, match="source_definition_digest"):
        revise_candidate_from_edited_definition(
            tmp_path,
            draft_id=draft.draft_id,
            request=req,
            client=client,
        )
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "dispatched_unknown"
    assert stored.candidate_id is None


def test_demote_preserves_draft_ref_failed_and_reloads(
    tmp_path: Path,
) -> None:
    """SBW06b CAS-fail → cache loss → GET fail must stay model-valid on reload."""
    from apps.live_control_server.models.statblock_candidate_revision import (
        ReviseMaterializationV1,
        ReviseOperationV1,
    )
    from apps.live_control_server.services.statblock_candidate_cache import (
        candidate_cache_root,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        _write_operation_unlocked,
        mark_cache_failed,
    )

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture

    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"

    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    # Simulate SBW06b ThreatDraft CAS failure leaving draft_ref=failed.
    pending_with_failed_ref = stored.model_copy(
        update={
            "status": "cache_stored_ref_pending",
            "materialization": ReviseMaterializationV1(
                cache="stored",
                draft_ref="failed",
                source_status="none",
            ),
        }
    )
    _write_operation_unlocked(tmp_path, pending_with_failed_ref)

    cache_path = (
        candidate_cache_root(tmp_path) / f"{response_fixture.candidate_id}.json"
    )
    assert cache_path.is_file()
    cache_path.unlink()
    client.get_candidate.side_effect = StatblockIntegrationError(
        category="downstream_not_found",
        message="candidate gone",
        status_code=404,
        retryable=False,
    )

    demoted = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert demoted.result == "candidate_received"

    after = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert after is not None
    assert after.status == "candidate_received"
    assert after.materialization.cache == "failed"
    assert after.materialization.draft_ref == "failed"
    # Reload validation must accept the successor (not classify as corrupt).
    reloaded = ReviseOperationV1.model_validate(
        after.model_dump(mode="json", by_alias=True)
    )
    assert reloaded.materialization.draft_ref == "failed"
    # Direct demotion helper preserves the same successor.
    again = mark_cache_failed(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=after.request_digest,
        candidate_id=response_fixture.candidate_id,
    )
    assert again.status == "candidate_received"
    assert again.materialization == after.materialization


def test_exact_body_idempotency_conflict_is_durable_integrity_classification(
    tmp_path: Path,
) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    client = MagicMock()
    client.revise_candidate.side_effect = StatblockIntegrationError(
        category="downstream_conflict",
        message="idempotency key conflict",
        status_code=409,
        retryable=False,
        error_code="idempotency_conflict",
    )

    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "revise_integrity_conflict"
    assert first.operation_status == "dispatched_unknown"
    assert first.candidate_id is None
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "dispatched_unknown"
    assert stored.recovery_classification == "idempotency_authority_conflict"
    assert stored.candidate_id is None

    client.revise_candidate.reset_mock()
    second = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert second.result == "revise_integrity_conflict"
    client.revise_candidate.assert_not_called()
    # Changed body still cannot replace authority.
    mutated = req.model_copy(update={"revision_instructions": ["Different instruction."]})
    conflict = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=mutated,
        client=client,
    )
    assert conflict.result == "revise_input_conflict"


def test_mark_revise_reconciled_rejects_applied_source_status(tmp_path: Path) -> None:
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        ReviseReconciliationError,
        mark_revise_reconciled,
    )

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture
    result = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert result.result == "reconciled"
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None

    with pytest.raises(ReviseReconciliationError) as exc_info:
        mark_revise_reconciled(
            tmp_path,
            draft_id=draft.draft_id,
            request_id=req.request_id,
            request_digest=stored.request_digest,
            candidate_id=response_fixture.candidate_id,
            source_status="applied",
        )
    assert exc_info.value.status_code == 422


def test_persisted_reconciled_applied_fails_closed_on_reload_and_replay(
    tmp_path: Path,
) -> None:
    """Poisoned reconciled/applied must not replay as ordinary success."""
    from apps.live_control_server.models.statblock_candidate_revision import (
        ReviseOperationV1,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        ReviseReconciliationError,
        _record_path,
    )
    from src.live_play.live_store import write_json

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture
    revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "reconciled"

    poisoned = stored.model_dump(mode="json", by_alias=True)
    poisoned["materialization"]["source_status"] = "applied"
    path = _record_path(tmp_path, draft_id=draft.draft_id, request_id=req.request_id)
    write_json(path, poisoned)

    with pytest.raises(ValidationError):
        ReviseOperationV1.model_validate(poisoned)

    with pytest.raises(ReviseReconciliationError) as exc_info:
        get_revise_operation(
            tmp_path, draft_id=draft.draft_id, request_id=req.request_id
        )
    assert exc_info.value.status_code == 409
    assert "applied" in str(exc_info.value)

    replay = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert replay.result == "revise_integrity_conflict"


def test_reconciled_materialization_is_immutable_none_only(tmp_path: Path) -> None:
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        mark_revise_reconciled,
    )

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture
    revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "reconciled"
    assert stored.materialization.source_status == "none"

    again = mark_revise_reconciled(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=stored.request_digest,
        candidate_id=response_fixture.candidate_id,
        source_status="none",
    )
    assert again.status == "reconciled"
    assert again.materialization.source_status == "none"


def test_prove_revise_ref_attached_ignores_journal_source_status(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.models.threat_draft import CandidateLineageV1
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        prove_revise_ref_attached,
    )

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture
    revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    after = get_threat_draft(tmp_path, draft.draft_id)
    lineage = CandidateLineageV1.model_validate(
        after.candidate_refs[0].lineage.model_dump(mode="json", by_alias=True)
    )
    assert prove_revise_ref_attached(
        after,
        stored,
        expected_lineage=lineage,
    )


def test_replay_fails_when_generated_from_diverges_from_journal(
    tmp_path: Path,
) -> None:
    """Readable draft with mismatched generated_from is integrity, not success."""
    from src.live_play.live_store import write_json

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    client.get_candidate.return_value = response_fixture
    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"
    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.source_draft_version == 1

    after = get_threat_draft(tmp_path, draft.draft_id)
    poisoned = after.model_dump(mode="json", by_alias=True)
    poisoned["candidate_refs"][0]["generated_from_draft_version"] = 99
    draft_path = tmp_path / "out" / "threat_drafts" / f"{draft.draft_id}.json"
    write_json(draft_path, poisoned)

    replay = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert replay.result == "revise_integrity_conflict"


def test_pending_applied_source_status_rejected_by_model_and_load(
    tmp_path: Path,
) -> None:
    """cache_stored_ref_pending/applied must not load or normalize to reconciled."""
    from apps.live_control_server.models.statblock_candidate_revision import (
        ReviseOperationV1,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        _record_path,
        mark_cache_stored_ref_pending,
        record_candidate_received,
    )
    from src.live_play.live_store import write_json

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    body, digest, src_digest, instr_digest = _body_and_digests(req)
    claim_revise_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        request_id=req.request_id,
        request_digest=digest,
        request_body=body,
        editor_state_revision=req.editor_state_revision,
        source_definition_digest=src_digest,
        instruction_options_digest=instr_digest,
    )
    write_ahead_dispatched_unknown(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=digest,
    )

    response_fixture = _revise_response()
    record_candidate_received(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=digest,
        candidate_id=response_fixture.candidate_id,
    )
    pending = mark_cache_stored_ref_pending(
        tmp_path,
        draft_id=draft.draft_id,
        request_id=req.request_id,
        request_digest=digest,
        candidate_id=response_fixture.candidate_id,
    )
    assert pending.status == "cache_stored_ref_pending"
    assert pending.materialization.source_status == "none"

    poisoned = pending.model_dump(mode="json", by_alias=True)
    poisoned["materialization"]["source_status"] = "applied"
    path = _record_path(tmp_path, draft_id=draft.draft_id, request_id=req.request_id)
    write_json(path, poisoned)

    with pytest.raises(ValidationError):
        ReviseOperationV1.model_validate(poisoned)

    with pytest.raises(ReviseReconciliationError) as exc_info:
        get_revise_operation(
            tmp_path, draft_id=draft.draft_id, request_id=req.request_id
        )
    assert exc_info.value.status_code == 409
    assert "applied" in str(exc_info.value)

    replay = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=MagicMock(),
    )
    assert replay.result == "revise_integrity_conflict"
    # Journal must not have been silently healed to reconciled/none.
    with pytest.raises(ReviseReconciliationError):
        get_revise_operation(
            tmp_path, draft_id=draft.draft_id, request_id=req.request_id
        )


def test_corrupt_draft_on_reconciled_replay_is_unavailable(tmp_path: Path) -> None:
    from src.live_play.live_store import write_json

    draft = _create_draft(tmp_path)
    req = _service_request(draft)
    response_fixture = _revise_response()
    client = MagicMock()
    client.revise_candidate.return_value = response_fixture
    first = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert first.result == "reconciled"

    draft_path = tmp_path / "out" / "threat_drafts" / f"{draft.draft_id}.json"
    write_json(draft_path, {"not": "a threat draft"})

    replay = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert replay.result == "revise_draft_unavailable"

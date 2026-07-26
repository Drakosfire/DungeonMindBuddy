"""SBW06a revise journal, adapter, and no-mutation proofs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

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
        ref_candidate_ids=set(),
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
        ref_candidate_ids=set(),
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
        ref_candidate_ids=set(),
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
        ref_candidate_ids=set(),
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
        ref_candidate_ids=set(),
    )
    assert outcome == "revise_busy"


def test_happy_path_ends_cache_stored_ref_pending_without_draft_mutation(
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
    assert result.result == "cache_stored_ref_pending"
    assert result.operation_status == "cache_stored_ref_pending"
    assert result.candidate_id == response_fixture.candidate_id

    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.version == before.version
    assert after.candidate_refs == before.candidate_refs

    stored = get_revise_operation(
        tmp_path, draft_id=draft.draft_id, request_id=req.request_id
    )
    assert stored is not None
    assert stored.status == "cache_stored_ref_pending"
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
    assert first.result == "cache_stored_ref_pending"
    client.revise_candidate.reset_mock()

    second = revise_candidate_from_edited_definition(
        tmp_path,
        draft_id=draft.draft_id,
        request=req,
        client=client,
    )
    assert second.result == "cache_stored_ref_pending"
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
        ref_candidate_ids=set(),
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
    assert second.result == "cache_stored_ref_pending"
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
    after = get_threat_draft(tmp_path, draft.draft_id)
    assert after.candidate_refs == before.candidate_refs


def test_history_full_when_generation_reservations_saturate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = _create_draft(tmp_path)
    req = _service_request(draft)

    monkeypatch.setattr(
        "apps.live_control_server.services.statblock_revise_reconciliation.count_generation_capacity_usage",
        lambda *_args, **_kwargs: 64,
    )
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

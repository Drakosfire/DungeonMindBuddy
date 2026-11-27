from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.build_proposal.service import BuildProposalService
from application_state.errors import ApplicationStateNotFoundError
from evals.buddy_benchmark.browser_capture import build_proposal_readback


@pytest.fixture
def staged_review(monkeypatch):
    action, conversation, document = uuid4(), uuid4(), uuid4()
    basis = dict(world_id="world", document_id=str(document),
                 registry_revision=7, content_sha256="a" * 64)
    capability = dict(idempotency_key=str(action), conversation_id=str(conversation),
                      expected_pointer_revision=1, basis=basis)
    turn = dict(turn_id=str(uuid4()), lifecycle_status="completed")
    proposal = {"target": {"kind": "replace_selection"}, "replacement_markdown": "| New |"}
    record = SimpleNamespace(
        action_id=action, revision=3, state="proposed", inserted_in_draft=False,
        reservation=SimpleNamespace(conversation_id=conversation, expected_pointer_revision=1,
                                    basis=SimpleNamespace(**basis)),
        proposal=SimpleNamespace(model_dump=lambda *, mode: proposal),
    )
    calls = []

    def get(self, world, action_id):
        calls.append((world, action_id))
        return record

    monkeypatch.setattr(BuildProposalService, "get", get)
    return {"build_write_capability": capability}, turn, record, proposal, calls


def test_retains_exact_staged_markdown_and_target(staged_review):
    request, turn, record, proposal, calls = staged_review
    assert build_proposal_readback(request, "world", turn) == {
        "action_id": str(record.action_id), "durable_turn_id": turn["turn_id"],
        "status": "observed", "state": "proposed", "revision": 3,
        "inserted_in_draft": False, "proposal": proposal,
    }
    assert calls == [("world", record.action_id)]


def test_does_not_copy_a_proposal_for_a_different_basis(staged_review):
    request, turn, record, _, _ = staged_review
    record.reservation.basis.registry_revision += 1
    result = build_proposal_readback(request, "world", turn)
    assert result["status"] == "mismatched"
    assert "proposal" not in result


def test_absent_proposal_is_an_observation(staged_review, monkeypatch):
    request, turn, _, _, _ = staged_review

    def missing(*args):
        raise ApplicationStateNotFoundError("missing")

    monkeypatch.setattr(BuildProposalService, "get", missing)
    assert build_proposal_readback(request, "world", turn)["status"] == "absent"


def test_only_reads_for_terminal_build_turn_with_a_capability(staged_review):
    request, turn, _, _, calls = staged_review
    assert build_proposal_readback({}, "world", turn) is None
    assert build_proposal_readback(request, "world", dict(turn, lifecycle_status="running")) is None
    assert calls == []

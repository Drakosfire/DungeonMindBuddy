from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.services import (
    selected_subject_initial_sources as hydration,
)
from apps.live_control_server.services import agent_context_assembler as assembler
from graph_memory.interaction.claims import GraphClaim, ClaimSupport
from graph_memory.interaction.session import (
    GraphRetrievalSession,
    SessionSnapshot,
    SourceAnchorState,
)
from graph_memory.interaction.session_store import (
    clear_sessions,
    replace_session,
    get_session,
)
from graph_memory.interaction.session_hydrate import hydrate_session_from_packet
from graph_memory.interaction import expansion_executor
from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult


@pytest.fixture(autouse=True)
def sessions():
    clear_sessions()
    yield
    clear_sessions()


def fixture(monkeypatch, count=9, length=30, outcome="enough"):
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test",
            campaign_id="",
            revision_id="rev:test",
            scope_mode="world",
            focus={"kind": "none"},
        )
    )
    for i in range(count):
        anchor = f"anchor:{i:02}"
        session.source_anchors.append(
            SourceAnchorState(anchor_id=anchor, readable=True)
        )
        session.claims.append(
            GraphClaim(
                claim_id=f"claim:{i}",
                claim_kind="relationship",
                subject_node_id="selected" if i % 2 else "other",
                object_node_id="other" if i % 2 else "selected",
                revision_id="rev:test",
                authority_class="accepted_relationship",
                evidence_ref_ids=[f"ref:{anchor}"],
                support=ClaimSupport(
                    state="source_anchor_available", source_anchor_ids=[anchor]
                ),
            )
        )
    replace_session(session)
    calls = []

    def native_read(request, *, repo_root):
        calls.append(request)
        body = ("source " + request.anchor_id + " ") * length
        body = body[: request.max_chars]
        result = WorldGraphSourceAnchorReadResult.model_validate(
            {
                "outcome": outcome,
                "anchorId": request.anchor_id,
                "evidenceRefId": f"ref:{request.anchor_id}",
                "sourceArtifactId": "artifact:test",
                "sourceDomain": "session_recap",
                "sourceSpanRefId": request.anchor_id,
                "locatorKind": "source_span",
                "content": body
                if outcome in {"enough", "partial", "truncated"}
                else None,
                "contentSha256": "a" * 64,
                "truncated": outcome == "truncated",
                "snapshot": {
                    "worldId": "world:test",
                    "campaignId": "",
                    "revisionId": "rev:test",
                    "headRevisionId": "rev:test",
                    "isHead": True,
                    "focus": {"kind": "none"},
                    "admissibility": "gm",
                    "scopeMode": "world",
                },
            }
        )
        return SimpleNamespace(
            result=result,
            graph_revision="rev:test",
            evidence_ref_id=result.evidence_ref_id,
            source_artifact_id="artifact:test",
            source_span_ref_id=request.anchor_id,
            locator_kind="source_span",
            locator_identity=request.anchor_id,
            source_revision_id="source:rev",
            source_revision_sha256="a" * 64,
        )

    monkeypatch.setattr(
        expansion_executor.retrieval_service,
        "read_source_anchor_internal_v2",
        native_read,
    )
    envelope = dict(
        world_id="world:test",
        campaign_id="",
        revision_id="rev:test",
        scope_mode="world",
        admissibility="gm",
        focus={"kind": "none"},
        completeness="complete",
        excerpt_policy="provenance_context_not_citation",
        matched_node_ids=["selected"],
    )
    return session, envelope, calls


def read(session, envelope):
    return hydration.hydrate_selected_subject_sources(
        session, envelope, root=Path("/tmp/source-test")
    )


def test_actual_initial_invocation_delivers_later_batch_and_receipts(monkeypatch):
    session, envelope, calls = fixture(monkeypatch)
    original_claims = [c.model_dump() for c in session.claims]
    monkeypatch.setattr(
        assembler, "create_session_from_preflight", lambda *a, **k: session
    )
    assembly = assembler.assemble_agent_graph_context(
        question="Compare the subject", graph_envelope=envelope
    )
    packet = assembly.invocation.context_packet.retrieval_session.packet
    assert len(calls) == 9
    assert packet["initial_source_read_coverage"]["state"] == "complete"
    assert (
        packet["initial_opened_source_reads"][-1]["result"]["anchorId"] == "anchor:08"
    )
    assert [c.model_dump() for c in session.claims] == original_claims
    restored = hydrate_session_from_packet(packet)
    assert len(restored.source_reads) == 9 and all(
        r.receipt_v2 for r in restored.source_reads
    )
    assert all(o.requested_by == "server_initial" for o in restored.operations)


def test_permutation_dedup_and_whole_set_budget(monkeypatch):
    session, envelope, calls = fixture(monkeypatch, count=16, length=300)
    session.claims.reverse()
    session.claims.append(session.claims[0].model_copy(deep=True))
    result = read(session, envelope)
    assert [r.anchor_id for r in calls] == [f"anchor:{i:02}" for i in range(16)]
    assert all(r.max_chars == 1500 for r in calls)
    assert result["initial_source_read_coverage"]["returnedCharacters"] == 24000
    assert len(session.source_reads) == 16


@pytest.mark.parametrize(
    "failure", ["wrong_revision", "missing_result", "after_mutation"]
)
def test_atomic_second_batch_failure_preserves_only_first_batch(monkeypatch, failure):
    session, envelope, calls = fixture(monkeypatch, count=10)
    real = hydration.execute_read_graph_source
    n = 0

    def execute(*a, **kw):
        nonlocal n
        n += 1
        result = real(*a, **kw)
        if n == 2:
            if failure == "after_mutation":
                raise RuntimeError("failed after native mutations")
            if failure == "missing_result":
                result["reads"].pop()
            else:
                result["reads"][0]["receipt"]["graph_revision"] = "foreign"
        return result

    monkeypatch.setattr(hydration, "execute_read_graph_source", execute)
    result = read(session, envelope)
    assert len(session.source_reads) == len(get_session(session.id).source_reads) == 8
    assert not any(a.opened for a in session.source_anchors[8:])
    assert len(result["initial_opened_source_reads"]) == 8
    assert result["initial_source_read_coverage"]["unread"] == 2
    assert result["initial_source_read_coverage"]["state"] == "partial"


def test_missing_unreadable_and_capped_support_stays_in_denominator(monkeypatch):
    session, envelope, calls = fixture(monkeypatch, count=20)
    session.source_anchors.pop()
    session.source_anchors[-1].readable = False
    result = read(session, envelope)["initial_source_read_coverage"]
    assert result["declared"] == 20 and result["eligible"] == 18
    assert result["selected"] == result["opened"] == 16 and result["unread"] == 4
    assert result["state"] == "partial"


def test_authentic_truncated_content_delivered_but_not_complete(monkeypatch):
    session, envelope, calls = fixture(monkeypatch, outcome="truncated")
    result = read(session, envelope)
    assert len(result["initial_opened_source_reads"]) == 9
    assert result["initial_source_read_coverage"]["truncated"] == 9
    assert result["initial_source_read_coverage"]["state"] == "partial"


@pytest.mark.parametrize(
    "change", ["player", "unselected", "foreign_world", "partial_object"]
)
def test_ineligible_context_never_reads(monkeypatch, change):
    session, envelope, calls = fixture(monkeypatch)
    if change == "player":
        session.snapshot.admissibility = envelope["admissibility"] = "player"
    elif change == "unselected":
        envelope.pop("excerpt_policy")
    elif change == "foreign_world":
        envelope["world_id"] = "world:foreign"
    else:
        envelope["completeness"] = "partial"
    assert read(session, envelope) is None and calls == []


def test_both_harness_inputs_contain_exact_opened_source_data(monkeypatch):
    from apps.live_control_server.services.hermes_graph_agent import _scope_block
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.pydantic_ai_agent_runtime import (
        _scope_capability_packet,
    )

    session, envelope, calls = fixture(monkeypatch)
    monkeypatch.setattr(
        assembler, "create_session_from_preflight", lambda *a, **k: session
    )
    invocation = assembler.assemble_agent_graph_context(
        question="Compare", graph_envelope=envelope
    ).invocation
    request = map_invocation_to_hermes_request(invocation)
    hermes = _scope_block(
        request.capability_policy,
        retrieval_session_id=session.id,
        retrieval_session=invocation.context_packet.retrieval_session.packet,
    )
    alternate = _scope_capability_packet(invocation)
    for text in (hermes, alternate):
        assert "openedSourceReads" in text and "sourceReadCoverage" in text
        assert "source anchor:08 " in text and "source:rev" in text


def test_supplied_session_is_not_automatically_read(monkeypatch):
    session, envelope, calls = fixture(monkeypatch)
    assembly = assembler.assemble_agent_graph_context(
        question="Compare", graph_envelope=envelope, retrieval_session=session
    )
    assert calls == []
    assert (
        "initial_opened_source_reads"
        not in assembly.invocation.context_packet.retrieval_session.packet
    )


@pytest.mark.parametrize("outcome", ["denied", "unavailable", "empty"])
def test_genuine_non_content_reads_remain_honest_failures(monkeypatch, outcome):
    session, envelope, calls = fixture(monkeypatch, count=2, outcome=outcome)
    result = read(session, envelope)
    assert result["initial_opened_source_reads"] == []
    assert result["initial_source_read_coverage"]["opened"] == 0
    assert (
        "selected_support_read_unavailable"
        in result["initial_source_read_coverage"]["gapCodes"]
    )
    assert len(session.source_reads) == 2
    assert all(
        r.receipt_v2 is None and r.outcome == outcome for r in session.source_reads
    )
    assert not any(a.opened for a in session.source_anchors)


@pytest.mark.parametrize("outcome", ["denied", "unavailable", "empty"])
def test_forged_non_content_reply_rolls_back_successful_mutations(monkeypatch, outcome):
    session, envelope, calls = fixture(monkeypatch, count=9)
    real = hydration.execute_read_graph_source
    count = 0

    def execute(*args, **kwargs):
        nonlocal count
        count += 1
        packet = real(*args, **kwargs)
        if count == 2:
            packet["reads"][0]["result"].update(outcome=outcome, content=None)
        return packet

    monkeypatch.setattr(hydration, "execute_read_graph_source", execute)
    result = read(session, envelope)
    assert len(session.source_reads) == len(get_session(session.id).source_reads) == 8
    assert len(session.operations) == 8
    assert not session.source_anchors[-1].opened
    assert len(result["initial_opened_source_reads"]) == 8
    restored = hydrate_session_from_packet(session.project_for_hermes())
    assert len(restored.source_reads) == 8
    assert not restored.source_anchors[-1].opened
    assert (
        "selected_support_batch_invalid"
        in result["initial_source_read_coverage"]["gapCodes"]
    )

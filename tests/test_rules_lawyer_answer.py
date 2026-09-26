"""Bounded answer support and citation-fidelity fixture set."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from apps.live_control_server.models.rules_query import (
    RulesEvidenceItem, RulesQueryPacket, RulesQueryTrace,
)
from apps.live_control_server.services.rules_lawyer_answer import synthesize_rules_answer


class FakeGenerator:
    def __init__(self, parsed: dict | None = None, *, fail: bool = False) -> None:
        self.parsed = parsed
        self.fail = fail
        self.requests = []

    async def generate_structured(self, request):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("provider unavailable")
        return SimpleNamespace(parsed=self.parsed)


def packet(status: str = "success") -> RulesQueryPacket:
    return RulesQueryPacket(
        query_id="query:1", ruleset_id="dnd5e-2024-srd-occupancy-v1",
        rules_space_id="space:1", rules_revision_id="rev:1", status=status,
        evidence=[RulesEvidenceItem(
            rank=1, entity_id="entity:1", assertion_id="assertion:1",
            evidence_ref_id="evidence:exact", evidence_unit_id="unit:exact",
            source_artifact_id="artifact:exact", excerpt="You can't willingly end a move in its space.",
        )] if status in {"success", "insufficient_evidence"} else [],
        trace=RulesQueryTrace(searched_revision_id="rev:1", completeness="complete"),
    )


def run(source, generator):
    return asyncio.run(synthesize_rules_answer(
        question="Can I end movement in an occupied space?", packet=source, generator=generator,
    ))


def test_supported_answer_cites_exact_admitted_evidence_only():
    generator = FakeGenerator({
        "answer": "No, you cannot willingly end movement there.",
        "citation_evidence_ref_ids": ["evidence:exact"],
        "support_quotes": [{"evidence_ref_id": "evidence:exact", "quote": "You can't willingly end a move"}],
        "support_status": "supported", "needs_more_evidence": False, "reason": "",
    })
    result = run(packet(), generator)
    assert result.answer.status == "supported"
    assert result.answer.citation_evidence_ref_ids == ["evidence:exact"]
    assert result.answer.generation_trace_id.startswith("rules-answer:")
    request = generator.requests[0]
    assert "You can't willingly end" in request.user_prompt
    assert "evidence:exact" in request.user_prompt
    assert "artifact:exact" not in request.user_prompt


def test_unknown_citation_and_uncited_answer_fail_closed():
    for citations, reason in ((["evidence:forged"], "unknown_citation"), ([], "answer_lacks_support")):
        result = run(packet(), FakeGenerator({
            "answer": "No.", "citation_evidence_ref_ids": citations,
            "support_quotes": [],
            "support_status": "supported", "needs_more_evidence": False, "reason": "",
        }))
        assert result.answer.status == "insufficient_evidence"
        assert result.answer.answer is None
        assert result.answer.reason == reason


def test_partial_and_failed_retrieval_never_call_provider():
    for status in ("insufficient_evidence", "no_evidence", "rules_space_unavailable", "downstream_failure"):
        generator = FakeGenerator()
        result = run(packet(status), generator)
        assert result.answer.status != "supported"
        assert generator.requests == []


def test_provider_failure_and_unparsed_output_fail_closed():
    for generator in (FakeGenerator(fail=True), FakeGenerator(None)):
        result = run(packet(), generator)
        assert result.answer.status == "insufficient_evidence"
        assert result.answer.answer is None


def test_fabricated_quote_cannot_launder_an_exact_citation():
    result = run(packet(), FakeGenerator({
        "answer": "You may end movement there.",
        "citation_evidence_ref_ids": ["evidence:exact"],
        "support_quotes": [{"evidence_ref_id": "evidence:exact", "quote": "You may end movement there."}],
        "support_status": "supported", "needs_more_evidence": False, "reason": "",
    }))
    assert result.answer.status == "insufficient_evidence"
    assert result.answer.reason == "unverified_support_quote"
    assert result.answer.answer is None

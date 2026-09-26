"""RLH-06 server contract over a configured exact rules authority."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.models.rules_query import RulesEvidenceItem
from apps.live_control_server.routes.rules_query import configured_binding, rules_source
from apps.live_control_server.services.rules_query import (
    RulesSearchOutcome, RulesSpaceUnavailable, load_binding,
)


BINDING = load_binding(
    Path(__file__).resolve().parents[1]
    / "apps/live_control_server/integrations/dungeonmind/rules_occupancy_srd_v1.json"
)
QUESTION = "What text prohibits ending movement in another creature's space?"


class FakeRulesSource:
    def __init__(self, mode: str = "success") -> None:
        self.mode = mode
        self.calls: list[tuple[str, str, str, int]] = []

    def search(self, binding, question: str, *, max_hits: int) -> RulesSearchOutcome:
        self.calls.append((binding.space_id, binding.revision_id, question, max_hits))
        if self.mode == "unavailable":
            raise RulesSpaceUnavailable("no exact revision")
        if self.mode == "failure":
            raise RuntimeError("database failed")
        items = () if self.mode == "empty" else (
            RulesEvidenceItem(
                rank=1,
                entity_id="ent:rule",
                assertion_id="asrt:rule",
                evidence_ref_id="ev:rulesingestion:04786f12722f6b15ccb70b18995b060e473ac07115b43dfdba3ca59ae685061d",
                evidence_unit_id="04786f12722f6b15ccb70b18995b060e473ac07115b43dfdba3ca59ae685061d",
                source_artifact_id=BINDING.source_artifacts[0]["source_artifact_id"],
                source_revision_id=BINDING.source_revisions[0]["source_revision_id"],
                source_uri=BINDING.source_artifacts[0]["uri"],
                source_locator="rulesingestion:evidence-unit:04786f12722f6b15ccb70b18995b060e473ac07115b43dfdba3ca59ae685061d",
                locator="printed-page:14;section:Moving around Other Creatures",
                source_anchor_id="dm-source-anchor-v1.test",
                excerpt=next(iter(BINDING.evidence_units.values()))["text"],
            ),
        )
        return RulesSearchOutcome(
            evidence=items,
            search_result_digest="search:exact",
            searched_entities=1 if items else 0,
            admitted_assertions=1 if items else 0,
            completeness="partial" if self.mode == "partial" else "complete",
            reason="source_incomplete" if self.mode == "partial" else None,
        )


def _client(source: FakeRulesSource) -> TestClient:
    app = create_app()
    app.dependency_overrides[configured_binding] = lambda: BINDING
    app.dependency_overrides[rules_source] = lambda: source
    return TestClient(app)


def _request(**overrides) -> dict:
    return {"question": QUESTION, "ruleset_id": BINDING.ruleset_id, **overrides}


def test_query_packet_preserves_exact_configured_revision_and_source_refs() -> None:
    source = FakeRulesSource()
    response = _client(source).post("/api/live/rules/query", json=_request())
    assert response.status_code == 200
    packet = response.json()
    assert packet["status"] == "success"
    assert packet["rules_space_id"] == BINDING.space_id
    assert packet["rules_revision_id"] == BINDING.revision_id
    assert packet["trace"]["search_result_digest"] == "search:exact"
    assert packet["evidence"][0]["source_anchor_id"] == "dm-source-anchor-v1.test"
    assert packet["evidence"][0]["source_uri"].startswith("https://")
    assert source.calls == [(BINDING.space_id, BINDING.revision_id, QUESTION, 5)]
    assert "answer" not in packet


def test_no_result_partial_and_unavailable_are_distinct() -> None:
    for mode, status in (
        ("empty", "no_evidence"),
        ("partial", "insufficient_evidence"),
        ("unavailable", "rules_space_unavailable"),
        ("failure", "downstream_failure"),
    ):
        packet = _client(FakeRulesSource(mode)).post(
            "/api/live/rules/query", json=_request()
        ).json()
        assert packet["status"] == status


def test_browser_cannot_choose_authoritative_space_or_revision() -> None:
    source = FakeRulesSource()
    client = _client(source)
    for untrusted in ({"space_id": "space:other"}, {"revision_id": "rev:other"}):
        response = client.post("/api/live/rules/query", json=_request(**untrusted))
        assert response.status_code == 422
    unknown = client.post("/api/live/rules/query", json=_request(ruleset_id="other"))
    assert unknown.json()["status"] == "rules_space_unavailable"
    assert source.calls == []

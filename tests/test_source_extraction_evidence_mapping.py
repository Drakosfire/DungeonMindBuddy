from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    WorldGraphWriteError,
    _source_extraction_evidence_view,
)

ARTIFACT = "artifact:recap:longmont-c1:session-1:digest"
TOKEN = "sha256:" + ("ab" * 32)
DM_REVISION = "source-revision:session-1"
EVIDENCE = f"evidence:{ARTIFACT}:span:1-1"


class _Sources:
    def get_revision(self, revision_id: str):
        assert revision_id == DM_REVISION
        return SimpleNamespace(locator="file:///corpus/session-1.md")


def _contribution(*, evidence=None):
    assertion = SimpleNamespace(
        assertion_id="assertion:karsemine",
        source_artifact_id=ARTIFACT,
        source_revision_id=TOKEN,
        evidence_ref_ids=[EVIDENCE],
        value={
            "evidence": evidence
            if evidence is not None
            else [
                {
                    "evidence_ref_id": EVIDENCE,
                    "source_artifact_id": ARTIFACT,
                    "source_domain": "recap",
                    "source_span_ref_id": "span:1-1",
                }
            ]
        },
    )
    return SimpleNamespace(
        accepted_assertions=[assertion],
        candidate_assertions=[],
        rejected_assertions=[],
    )


def test_source_extraction_uses_admitted_recap_evidence() -> None:
    view = _source_extraction_evidence_view(
        _contribution(),
        pair_to_dm={(ARTIFACT, TOKEN): DM_REVISION},
        sources=_Sources(),
    )
    record = view.evidence[EVIDENCE]
    assert record.source_domain == "recap"
    assert record.locator == "file:///corpus/session-1.md"
    assert record.can_open_source is True
    assert record.can_highlight_span is False


def test_source_extraction_missing_embedded_evidence_fails_closed() -> None:
    with pytest.raises(WorldGraphWriteError, match="sealed embedded record"):
        _source_extraction_evidence_view(
            _contribution(evidence=[]),
            pair_to_dm={(ARTIFACT, TOKEN): DM_REVISION},
            sources=_Sources(),
        )


def test_source_extraction_unadmitted_pair_fails_closed() -> None:
    with pytest.raises(WorldGraphWriteError, match="was not admitted"):
        _source_extraction_evidence_view(
            _contribution(), pair_to_dm={}, sources=_Sources()
        )

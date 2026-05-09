"""Lexicon build must work when session memory comes from ``--records-jsonl`` (no ``rec_objs``)."""

from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.token_resolver_shadow import (
    build_campaign_lexicon,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_JSONL = (
    _REPO_ROOT
    / "evals"
    / "sentence_routing_retrieval_falsification"
    / "artifacts"
    / "last_session1_c1_breadcrumb_records.jsonl"
)


def test_build_campaign_lexicon_from_jsonl_records_derives_campaign_stopwords() -> None:
    """Mirrors ``--records-jsonl`` ingest: dict rows only, no breadcrumb frontmatter."""
    assert _FIXTURE_JSONL.is_file(), f"missing fixture: {_FIXTURE_JSONL}"
    lines = _FIXTURE_JSONL.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    assert len(records) >= 4, "fixture should contain several session-memory rows"

    lex = build_campaign_lexicon(
        breadcrumb_artifact_text="",
        records=records,
        campaign_id="longmont-c1",
    )
    assert "longmont" in lex.derived_route_stopwords, (
        "route-frequency derivation should mark recurring setting token longmont; "
        "empty lexicon (records not passed) would miss this"
    )


def test_build_campaign_lexicon_from_jsonl_records_includes_cohort_equivalence_seeds() -> None:
    """Cohort benchmark seeds are merged into the lexicon layer (no frontmatter aliases)."""
    lines = _FIXTURE_JSONL.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    lex = build_campaign_lexicon(
        breadcrumb_artifact_text="",
        records=records,
        campaign_id="longmont-c1",
    )
    assert "captain" in lex.equivalences

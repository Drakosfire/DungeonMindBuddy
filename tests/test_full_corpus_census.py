"""Census tests for the full-corpus World Graph ingestion slice."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "census_full_corpus.py"
spec = importlib.util.spec_from_file_location("census_full_corpus", TOOL)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_admitted_campaign_recaps_are_contiguous_and_unique() -> None:
    records = mod.census_records()
    summary = mod.summarize(records)
    c1 = summary["chronology"]["campaign_1_sessions"]
    c2 = summary["chronology"]["campaign_2_sessions"]
    assert c1 == list(range(1, 18)), c1
    assert c2 == list(range(1, 26)), c2
    assert summary["counts"]["campaign_recap_files_admitted"] == 17 + 25
    assert summary["counts"]["files_ambiguous"] == 2
    assert summary["worldbuilding_decision"] == "DEFER"


def test_session_prep_and_derivatives_are_excluded() -> None:
    records = mod.census_records()
    prep = [r for r in records if r["bucket"] == "campaign_2_session_prep"]
    assert prep
    assert all(not r["eligible_for_ingest"] for r in prep)
    deriv = [r for r in records if r["bucket"] == "derivative_or_staging"]
    assert deriv
    assert all(not r["eligible_for_ingest"] for r in deriv)


def test_duplicate_session_files_are_recorded_as_ambiguous() -> None:
    records = {r["path"]: r for r in mod.census_records()}
    c1_dup = records[
        "Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Stonebridge and Glowkindle Rats.md"
    ]
    c1_keep = records[
        "Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md"
    ]
    c2_dup = records[
        "Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md"
    ]
    c2_keep = records[
        "Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate Battle.md"
    ]
    assert c1_keep["eligible_for_ingest"] is True
    assert c1_dup["eligible_for_ingest"] is False
    assert c1_dup["ambiguous"] is True
    assert c2_keep["eligible_for_ingest"] is True
    assert c2_dup["eligible_for_ingest"] is False
    assert c2_dup["ambiguous"] is True

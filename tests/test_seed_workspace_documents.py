"""Tests for workspace document registry seed script."""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.services.workspace_document_registry import (
    list_workspace_documents,
)
from scripts.seed_workspace_documents import seed


def _layout(root: Path) -> None:
    prep = root / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep"
    prep.mkdir(parents=True)
    (prep / "Session 23 Prep.md").write_text("# C2 Session 23 Prep\n", encoding="utf-8")
    (prep / "Session 21 - brainstorming dump.md").write_text("# dump\n", encoding="utf-8")
    spike = root / "evals/c2_live_prep/mireward-prep/content/tiptap"
    spike.mkdir(parents=True)
    (spike / "north-gate-session-runbook.md").write_text("# runbook\n", encoding="utf-8")
    (spike / "north-gate-callout-spike.md").write_text("# spike\n", encoding="utf-8")


def test_seed_creates_allowlisted_plan_and_spike_docs(tmp_path: Path, capsys) -> None:
    _layout(tmp_path)
    assert seed(root=tmp_path, dry_run=False) == 0
    records = list_workspace_documents(tmp_path, status=None)
    paths = {r.target_relpath for r in records}
    assert (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md"
        in paths
    )
    assert (
        "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md"
        in paths
    )
    assert (
        "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md"
        in paths
    )
    assert all(r.document_id.count("-") == 4 for r in records)
    out = capsys.readouterr().out
    assert "Ambiguous Session Prep files" in out
    assert "Session 21 - brainstorming dump.md" in out


def test_seed_is_idempotent(tmp_path: Path) -> None:
    _layout(tmp_path)
    assert seed(root=tmp_path, dry_run=False) == 0
    first = list_workspace_documents(tmp_path, status=None)
    assert seed(root=tmp_path, dry_run=False) == 0
    second = list_workspace_documents(tmp_path, status=None)
    assert len(first) == len(second)
    assert {r.document_id for r in first} == {r.document_id for r in second}

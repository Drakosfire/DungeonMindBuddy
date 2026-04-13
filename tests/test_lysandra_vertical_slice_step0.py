"""Step 0 gates for Lysandra vertical slice benchmark."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import (
    load_step0_gold,
    resolve_corpus_dir,
    run_step0_gates,
    statblock_service_gate_passes,
    step0_gold_path,
)


def test_step0_gold_files_exist() -> None:
    assert step0_gold_path().is_file()
    policy = Path(__file__).resolve().parents[1] / "evals" / "lysandra_vertical_slice" / "gold" / "corpus_policy.json"
    assert policy.is_file()


def test_corpus_policy_json_valid() -> None:
    policy_path = (
        Path(__file__).resolve().parents[1] / "evals" / "lysandra_vertical_slice" / "gold" / "corpus_policy.json"
    )
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    assert data.get("entity_canonical_name")
    assert data.get("statblock_status")


def test_run_step0_gates_passes_with_skip_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE", "1")
    ok, viol = run_step0_gates()
    assert ok, viol


def test_statblock_gate_fails_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUNGEONMIND_STATBLOCK_URL", raising=False)
    monkeypatch.delenv("LYSANDRA_SLICE_MOCK_STATBLOCK", raising=False)
    monkeypatch.delenv("LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE", raising=False)
    gold = load_step0_gold()
    assert statblock_service_gate_passes(gold) is False


def test_resolve_corpus_dir_points_at_eldyrwild_markdown() -> None:
    p = resolve_corpus_dir()
    assert p.name == "eldyrwild-markdown"
    assert (p / "Longmont Campaign").is_dir()

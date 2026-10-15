from __future__ import annotations

import json
import shutil
from pathlib import Path

from evals.graph_memory_layer.validate_mirathorn_worldbuilding_query_gold_v1 import (
    GOLD_PATH,
    REPO_ROOT,
    validate_gold,
)


def _copy_fixture_repo(tmp_path: Path) -> tuple[Path, Path]:
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    root = tmp_path
    for relative_path in (
        gold["corpus"]["source_path"],
        gold["profile_snapshot"]["source_path"],
    ):
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative_path, destination)
    gold_path = root / "gold.json"
    gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
    return root, gold_path


def test_mirathorn_query_gold_is_source_locked_and_complete(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)

    assert validate_gold(gold_path, root) == []


def test_gold_rejects_source_revision_drift(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)
    source = root / json.loads(gold_path.read_text())["corpus"]["source_path"]
    source.write_text(source.read_text(encoding="utf-8") + "\nChanged.\n", encoding="utf-8")

    assert any("source SHA-256" in error for error in validate_gold(gold_path, root))


def test_gold_rejects_quote_or_line_range_that_does_not_open(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["facts"][0]["evidence"][0]["quote"] = "not present in this source"
    gold["facts"][1]["evidence"][0]["start_line"] = 0
    gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")

    errors = validate_gold(gold_path, root)
    assert any("quote is absent" in error for error in errors)
    assert any("invalid source bounds" in error for error in errors)


def test_gold_rejects_dangling_question_fact_ids(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["questions"][0]["fact_ids"].append("fact-that-does-not-exist")
    gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")

    assert any("references an unknown fact id" in error for error in validate_gold(gold_path, root))


def test_gold_requires_all_five_goal_expectations_to_be_questioned(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["questions"][0]["covers_expectations"] = []
    gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")

    assert any("required expectations are not covered" in error for error in validate_gold(gold_path, root))


def test_gold_requires_the_expected_fact_set_for_each_goal_expectation(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["questions"][1]["fact_ids"].remove("torrin_guild_concern")
    gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")

    assert any(
        "expectation council_and_representative_interests is missing required gold facts"
        in error
        for error in validate_gold(gold_path, root)
    )


def test_gold_rejects_profile_drift_without_refreshing_snapshot(tmp_path):
    root, gold_path = _copy_fixture_repo(tmp_path)
    profile = root / json.loads(gold_path.read_text())["profile_snapshot"]["source_path"]
    profile.write_text(profile.read_text(encoding="utf-8") + "\n# Changed profile.\n", encoding="utf-8")

    assert any("profile source SHA-256" in error for error in validate_gold(gold_path, root))

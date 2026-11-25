"""Guard the workflow selection inventory and the ordinary Build partition."""

import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from scripts import ownership_ci_partition as partition
from scripts.ci_contract import contracts

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_retains_every_original_selector_once_except_partitioned_module():
    workflow = (ROOT / ".github/workflows/world-ownership-core.yml").read_text()
    commands = [contracts()[suite]["argv"] for suite in partition.SUITES]
    actual = Counter(arg for command in commands for arg in command if arg.startswith("tests/"))
    expected = Counter(json.loads((ROOT / "tests/fixtures/ownership_ci_selectors.json").read_text()))
    expected[partition.MODULE] = 3
    expected["tests/test_ownership_ci_partition.py"] = 1
    expected.update([
        "tests/test_aw_action_assessment.py",
        "tests/test_build_prose_catalog.py",
        "tests/integration/test_recap_evidence_append.py",
        "tests/test_category_candidate_graph_extractor.py",
        "tests/test_recap_object_dispositions.py",
        "tests/test_recap_quote_integrity.py",
        "tests/test_recap_semantic_candidate_correction.py",
        "tests/application_state/test_plan_author_location.py",
        "tests/application_state/test_plan_contextual_targets.py",
        "tests/test_plan_jev_authoring.py::test_author_scope_input_admission_joins_exact_native_turn_without_granting_work",
        "tests/test_plan_jev_authoring.py::test_source_blind_sdk_records_only_its_actual_native_scope_observation",
    ])
    assert actual == expected
    assert len(commands) == 4
    assert all("scripts.ownership_ci_partition" in c for c in commands)
    aggregate = "world-and-content ingestion-and-review query-and-answer saved-page-readers"
    assert set(aggregate.split()) == set(partition.SUITES)
    assert f"run: uv run --locked python scripts/ci_contract.py run {aggregate}" in workflow
    assert "matrix:" not in workflow
    for suite in partition.SUITES:
        assert f"--ownership-suite={suite}" in contracts()[suite]["argv"]
    for suite in set(partition.BUCKET_OWNERS):
        assert partition.MODULE in contracts()[suite]["argv"]


def test_partition_is_complete_disjoint_and_keeps_other_modules():
    ids = [f"{partition.MODULE}::test_example[param-{i}]" for i in range(1000)]
    selected = []
    for suite in partition.SUITES:
        deselected = []
        config = SimpleNamespace(
            getoption=lambda _, suite=suite: suite,
            hook=SimpleNamespace(pytest_deselected=lambda items: deselected.extend(items)),
        )
        items = [SimpleNamespace(nodeid=id_) for id_ in [*ids, "tests/test_other.py::test_kept"]]
        partition.pytest_collection_modifyitems(config, items)
        assert items[-1].nodeid == "tests/test_other.py::test_kept"
        kept = [item.nodeid for item in items[:-1]]
        selected.extend(kept)
        assert Counter([*kept, *(item.nodeid for item in deselected)]) == Counter(ids)
    assert Counter(selected) == Counter(ids)


def test_local_world_directory_is_in_hosted_frontend_gate():
    commands = contracts()["hosted-frontend"]["steps"]
    assert any(step["argv"][:4] == ["npm", "test", "--", "src/localWorld"] for step in commands)

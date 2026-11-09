"""Guard the workflow selection inventory and the ordinary Build partition."""

import json
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from scripts import ownership_ci_partition as partition

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_retains_every_original_selector_once_except_partitioned_module():
    workflow = (ROOT / ".github/workflows/world-ownership-core.yml").read_text()
    # Only pytest selections: ruff's inventory is deliberately excluded.
    commands = re.findall(r"run: >-\n(.*?)(?=\n\n|\Z)", workflow, re.S)
    commands = [command for command in commands if "pytest " in command]
    actual = Counter(re.findall(r"^          (tests/\S+)\s*$", "\n".join(commands), re.M))
    expected = Counter(json.loads((ROOT / "tests/fixtures/ownership_ci_selectors.json").read_text()))
    expected[partition.MODULE] = 3
    expected["tests/test_ownership_ci_partition.py"] = 1
    assert actual == expected
    assert len(commands) == 4
    assert all("-p scripts.ownership_ci_partition --ownership-suite=${{ matrix.suite }}" in c for c in commands)
    for suite in set(partition.BUCKET_OWNERS):
        step = workflow.split(f"if: matrix.suite == '{suite}'")[-1].split("\n\n", 1)[0]
        assert partition.MODULE in step


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
    workflow = (ROOT / ".github/workflows/hosted-validation.yml").read_text()
    assert "npm test -- src/localWorld " in workflow

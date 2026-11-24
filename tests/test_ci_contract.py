"""Owning-boundary guards for live CI commands and complete file classification."""

import copy
import json
import os
import shutil
import subprocess

import pytest

from scripts import ci_contract as ci


def test_workflows_consume_the_live_named_contracts():
    world = (ci.ROOT / ".github/workflows/world-ownership-core.yml").read_text()
    hosted = (ci.ROOT / ".github/workflows/hosted-validation.yml").read_text()
    suites = "world-and-content ingestion-and-review query-and-answer saved-page-readers"
    assert f"run: uv run --locked python scripts/ci_contract.py run {suites}" in world
    assert "matrix:" not in world
    for workflow, contract in (("rules-only-runtime", "rules-only-runtime"), ("agent-legacy-import", "agent-legacy-import")):
        text = (ci.ROOT / f".github/workflows/{workflow}.yml").read_text()
        assert f"scripts/ci_contract.py run {contract}" in text
    assert "run: uv run --locked python scripts/ci_contract.py run auth-app" in hosted
    assert "node /workspace/scripts/ci_frontend_contract.mjs" in hosted
    assert '--env GITHUB_SHA="${GITHUB_SHA}"' in hosted


def test_guest_release_contract_covers_release_tests_and_hosted_entry():
    catalog = ci.contracts(ci.ROOT)
    backend = set(catalog["guest-release"]["argv"])
    expected_backend = {str(path.relative_to(ci.ROOT)) for path in (ci.ROOT / "tests").glob("test_guest_release_*.py")}
    assert expected_backend and expected_backend <= backend
    hosted = catalog["hosted-frontend"]["steps"]
    selectors = {argument for step in hosted for argument in step["argv"]}
    assert {"src/App.guestHome.test.tsx", "src/App.guestRelease.test.tsx", "src/guestRelease"} <= selectors


def assert_live_contracts(catalog, root):
    python_suites = {"world-and-content", "ingestion-and-review", "query-and-answer", "saved-page-readers", "auth-app"}
    assert python_suites | {"hosted-frontend"} <= catalog.keys()
    for name, contract in catalog.items():
        steps = contract.get("steps", [contract])
        assert isinstance(steps, list) and steps
        for step in steps:
            workdir = (root / step["cwd"]).resolve()
            assert workdir.is_relative_to(root.resolve()) and workdir.is_dir()
            argv = step["argv"]
            assert isinstance(argv, list) and argv and all(isinstance(arg, str) and arg for arg in argv)
            paths = [arg.split("::", 1)[0] for arg in argv if arg == "tests" or arg.startswith(("tests/", "src/"))]
            for path in paths:
                selected = (workdir / path).resolve()
                assert selected.is_relative_to(workdir) and selected.exists(), (name, path)
            if name in python_suites:
                assert argv[:3] == ["{python}", "-m", "pytest"] and paths
        if name == "hosted-frontend":
            assert steps[0]["argv"] == ["npm", "ci"]
            assert steps[-1]["argv"] == ["npm", "run", "build"]
            assert len(steps) > 2
            for step in steps[1:-1]:
                assert step["argv"][:3] == ["npm", "test", "--"]
                assert any(arg.startswith("src/") for arg in step["argv"])


def test_live_contracts_select_existing_sources_and_real_test_commands():
    # The historical extraction snapshot is evidence, not a second live selector authority.
    # Current selection changes require review of ci/contracts.json and full discovery.
    assert_live_contracts(ci.contracts(), ci.ROOT)


@pytest.mark.parametrize("invalid", ["empty-command", "stale-selector", "escaping-workdir", "empty-frontend"])
def test_live_contract_guards_reject_invalid_commands(invalid):
    catalog = copy.deepcopy(ci.contracts())
    if invalid == "empty-command":
        catalog["auth-app"]["argv"] = []
    elif invalid == "stale-selector":
        catalog["auth-app"]["argv"].append("tests/no-such-selected-test.py::test_missing")
    elif invalid == "escaping-workdir":
        catalog["auth-app"]["cwd"] = ".."
    else:
        catalog["hosted-frontend"]["steps"] = []
    with pytest.raises(AssertionError):
        assert_live_contracts(catalog, ci.ROOT)


def test_all_discovered_files_are_classified_once():
    result = ci.validate_inventory()
    assert sum(result["lane_file_counts"].values()) == result["discovered_test_files"]


def test_discovery_includes_untracked_files_and_both_python_patterns(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    names = {"tests/test_new.py", "tests/new_test.py", "apps/live-control-ui/src/new.spec.tsx", "apps/live-control-ui/tests/new.pw.ts"}
    for name in names | {"tests/helper.py", "apps/live-control-ui/src/new.tsx"}:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    assert ci.discover(tmp_path) == names
    (tmp_path / "tests/test_new.py").unlink()
    assert ci.discover(tmp_path) == names - {"tests/test_new.py"}


@pytest.mark.parametrize("lanes,found,key", [
    ({"fast": [], "domain-integration": [], "qualification": []}, {"tests/test_new.py"}, "unclassified"),
    ({"fast": ["tests/test_gone.py"], "domain-integration": [], "qualification": []}, set(), "stale"),
    ({"fast": ["tests/test_dup.py"], "domain-integration": [], "qualification": ["tests/test_dup.py"]}, {"tests/test_dup.py"}, "duplicate"),
])
def test_inventory_fails_closed_for_missing_stale_and_duplicate_assignments(tmp_path, monkeypatch, lanes, found, key):
    (tmp_path / "ci").mkdir()
    (tmp_path / "ci/test-classification.json").write_text(json.dumps({"version": 1, "lanes": lanes}))
    monkeypatch.setattr(ci, "discover", lambda root: found)
    with pytest.raises(ValueError, match=key):
        ci.validate_inventory(tmp_path)


def test_python_runner_propagates_failure_and_stops_following_steps(tmp_path, monkeypatch, capsys):
    contract = {"probe": {"steps": [
        {"cwd": ".", "argv": ["{python}", "-c", "raise SystemExit(7)"]},
        {"cwd": ".", "argv": ["{python}", "-c", "open('must-not-run','w').close()"]},
    ]}}
    monkeypatch.setattr(ci, "contracts", lambda root: contract)
    monkeypatch.setattr(ci, "sha", lambda root: "reviewed-sha")
    assert ci.execute("probe", tmp_path) == 7
    assert not (tmp_path / "must-not-run").exists()
    report = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report["sha"] == "reviewed-sha" and report["exit_code"] == 7
    assert report["elapsed_seconds"] >= 0


def test_node_runner_propagates_failure_without_git_or_later_steps(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "ci").mkdir()
    shutil.copyfile(ci.ROOT / "scripts/ci_frontend_contract.mjs", tmp_path / "scripts/ci_frontend_contract.mjs")
    steps = [{"cwd": ".", "argv": ["node", "-e", "process.exit(9)"]},
             {"cwd": ".", "argv": ["node", "-e", "require('fs').writeFileSync('must-not-run','')"]}]
    (tmp_path / "ci/contracts.json").write_text(json.dumps({"version": 1, "contracts": {"hosted-frontend": {"steps": steps}}}))
    result = subprocess.run(["node", "scripts/ci_frontend_contract.mjs"], cwd=tmp_path,
                            env={**os.environ, "GITHUB_SHA": "reviewed-sha"}, capture_output=True, text=True)
    assert result.returncode == 9
    assert not (tmp_path / "must-not-run").exists()
    assert json.loads(result.stdout.splitlines()[-1])["sha"] == "reviewed-sha"


@pytest.mark.parametrize(
    ("argv", "field", "detail"),
    [
        (["./missing-ci-command"], "spawn_error", "ENOENT"),
        (["node", "-e", "process.kill(process.pid, 'SIGTERM')"], "signal", "SIGTERM"),
    ],
)
def test_node_runner_reports_abnormal_exit(tmp_path, argv, field, detail):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "ci").mkdir()
    runner = "scripts/ci_frontend_contract.mjs"
    shutil.copyfile(ci.ROOT / runner, tmp_path / runner)
    steps = [{"cwd": ".", "argv": argv}]
    catalog = {"version": 1, "contracts": {"hosted-frontend": {"steps": steps}}}
    (tmp_path / "ci/contracts.json").write_text(json.dumps(catalog))

    result = subprocess.run(
        ["node", runner],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_SHA": "reviewed-sha"},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = json.loads(result.stdout.splitlines()[-1])
    assert report["exit_code"] == 1
    assert detail in report[field]


def test_ci_and_production_pin_the_same_uv_version():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    setup = (root / ".github/actions/setup-python-toolchain/action.yml").read_text()
    dockerfile = (root / "Dockerfile.production").read_text()
    ci_pin = re.findall(r"""^\s+version:\s*['"](\d+\.\d+\.\d+)['"]\s*$""", setup, re.M)
    image_pin = re.findall(r"^FROM ghcr\.io/astral-sh/uv:(\d+\.\d+\.\d+)@sha256:[a-f0-9]{64} AS uv-tool$", dockerfile, re.M)
    assert len(ci_pin) == len(image_pin) == 1
    assert ci_pin == image_pin, f"CI uv pin {ci_pin} differs from production {image_pin}"


@pytest.mark.parametrize("codes,expected", [([0, 0], 0), ([7, 9], 7)])
def test_serial_contracts_share_one_owner_and_run_remaining_suites(tmp_path, monkeypatch, codes, expected):
    from contextlib import contextmanager
    from scripts import ci_app_database as database
    events = []
    assignment = object()

    @contextmanager
    def owner():
        events.append("owner-enter")
        try:
            yield assignment
        except BaseException:
            events.append("abandon")
            raise
        else:
            events.append("accept")
        finally:
            events.append("owner-exit")

    @contextmanager
    def environment(actual):
        assert actual is assignment
        events.append("environment-enter")
        yield
        events.append("environment-exit")

    catalog = {name: {"argv": ["{python}", "-m", "pytest"]} for name in ("one", "two")}
    monkeypatch.setattr(ci, "contracts", lambda root: catalog)
    monkeypatch.setattr(database, "app_workstream", owner)
    monkeypatch.setattr(database, "assignment_environment", environment)
    def execute(name, root, *, catalog):
        events.append(name)
        return codes[["one", "two"].index(name)]
    monkeypatch.setattr(ci, "execute", execute)
    assert ci.run_contracts(["one", "two"], tmp_path) == expected
    assert events[:4] == ["owner-enter", "environment-enter", "one", "two"]
    assert events[-2:] == (["abandon", "owner-exit"] if expected else ["accept", "owner-exit"])
    assert events.count("owner-enter") == 1


def test_worker_waits_for_descendants_before_owner_can_exit(tmp_path):
    import sys
    marker = tmp_path / "worker-closed"
    child = "import time,pathlib; time.sleep(0.2); pathlib.Path('worker-closed').write_text('closed')"
    parent = f"import subprocess,sys; subprocess.Popen([sys.executable, '-c', {child!r}])"
    assert ci._run_worker([sys.executable, "-c", parent], tmp_path) == 0
    assert marker.read_text() == "closed"


def test_repeated_interrupts_do_not_escape_before_worker_closure(tmp_path, monkeypatch):
    events = []
    class Child:
        pid = 76543
        attempts = 0
        def wait(self):
            self.attempts += 1
            events.append("wait")
            if self.attempts <= 2:
                raise KeyboardInterrupt
            return 0
    child = Child()
    monkeypatch.setattr(ci.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(ci, "_group_live", lambda group: child.attempts <= 2)
    monkeypatch.setattr(ci.os, "killpg", lambda group, sig: events.append((group, sig)))
    with pytest.raises(KeyboardInterrupt):
        ci._run_worker(["probe"], tmp_path)
    assert child.attempts == 3
    assert len([event for event in events if isinstance(event, tuple)]) == 2


def test_direct_script_entry_reaches_owner_guard_without_pythonpath():
    import sys
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTHONPATH", "DMB_CI_APP_OWNER_FILE", "DMB_CI_APP_DATABASE_URL"}}
    env["GITHUB_ACTIONS"] = "false"
    result = subprocess.run([sys.executable, "scripts/ci_contract.py", "run", "auth-app"],
                            cwd=ci.ROOT, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Assign a retained CI App owner" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr

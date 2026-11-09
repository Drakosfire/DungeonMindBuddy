"""Local-verifier boundaries, with real temporary Git worktrees and no npm load."""

import json
import os
import signal
import sys
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import pytest
import yaml

from scripts import ci_local_frontend as local


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    ui = repo / "apps/live-control-ui"
    ui.mkdir(parents=True)
    (ui / "package-lock.json").write_text('{"lockfileVersion":3}')
    (repo / ".gitignore").write_text("node_modules/\n")
    (repo / "ci").mkdir()
    catalog = {
        "version": 1,
        "contracts": {
            "hosted-frontend": {
                "steps": [
                    {"cwd": "apps/live-control-ui", "argv": argv}
                    for argv in [
                        ["npm", "ci"],
                        ["npm", "test", "--", "src/owner.test.ts"],
                        ["npm", "run", "build"],
                    ]
                ]
            }
        },
    }
    (repo / "ci/contracts.json").write_text(json.dumps(catalog))
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    sha = local.git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(local, "ROOT", repo)
    lock = local.resource_lock
    monkeypatch.setattr(local, "resource_lock", lambda: lock(tmp_path / "global.lock"))
    monkeypatch.setattr(local, "resources", lambda workers: {"workers": workers})
    original = subprocess.check_output
    monkeypatch.setattr(
        local.subprocess,
        "check_output",
        lambda argv, **kwargs: (
            local.NODE + "\n"
            if argv == ["node", "--version"]
            else local.NPM + "\n"
            if argv == ["npm", "--version"]
            else original(argv, **kwargs)
        ),
    )
    calls = []

    def fake(argv, cwd, log, env):
        calls.append(argv)
        Path(log).write_text("retained command output")
        if argv[:2] == ["npm", "ci"]:
            package = cwd / "node_modules/vitest/package.json"
            package.parent.mkdir(parents=True)
            package.write_text('{"version":"3.2.4"}')
        if "list" in argv:
            dest = next(x.split("=", 1)[1] for x in argv if x.startswith("--json="))
            Path(dest).write_text(
                json.dumps(
                    [
                        {
                            "file": str(cwd / "src/owner.test.ts"),
                            "name": "owner > refuses stale write",
                        }
                    ]
                )
            )
        if "--reporter=json" in argv:
            dest = next(
                x.split("=", 1)[1] for x in argv if x.startswith("--outputFile=")
            )
            Path(dest).write_text(
                json.dumps(
                    {
                        "testResults": [
                            {
                                "name": str(cwd / "src/owner.test.ts"),
                                "assertionResults": [
                                    {
                                        "ancestorTitles": ["owner"],
                                        "title": "refuses stale write",
                                        "fullName": "owner refuses stale write",
                                        "status": "passed",
                                    }
                                ],
                            }
                        ]
                    }
                )
            )
        return {
            "argv": argv,
            "exit_code": 0,
            "elapsed_seconds": 0.01,
            "log": Path(log).name,
        }

    monkeypatch.setattr(local, "command", fake)
    args = SimpleNamespace(
        repo=str(repo),
        sha=sha,
        output=str(tmp_path / "evidence"),
        suite="discovered",
        workers=8,
    )
    return args, calls, fake


def test_real_worktree_cleanup_and_source_bound_inventory(sandbox):
    args, calls, _ = sandbox
    assert local.verify(args) == 0
    report = local.validate(Path(args.output) / "evidence.json", args.sha, "discovered")
    assert (
        report["cleanup_complete"]
        and not report["source_dirty_before"]
        and not report["source_dirty_after"]
    )
    assert not Path(report["source_frontend_path"]).exists()
    assert report["tests"][0]["discovered_cases"] == 1
    assert any("--maxWorkers=8" in call and "--minWorkers=8" in call for call in calls)
    assert any(arg.startswith("--userconfig=") for arg in calls[0])
    assert any(arg.startswith("--globalconfig=") for arg in calls[0])
    configs = [
        arg.split("=", 1)[1]
        for arg in calls[0]
        if arg.startswith(("--userconfig=", "--globalconfig="))
    ]
    assert len(set(configs)) == 2
    assert all(Path(path).read_text() == "" for path in configs)
    assert (
        len(local.git(args.repo, "worktree", "list", "--porcelain").split("worktree "))
        == 2
    )


@pytest.mark.parametrize("failed", ["tests", "build", "missing-results", "discovery"])
def test_failures_preserve_build_evidence_and_cleanup(sandbox, monkeypatch, failed):
    args, calls, fake = sandbox

    def fault(argv, cwd, log, env):
        result = fake(argv, cwd, log, env)
        if failed == "tests" and "--reporter=json" in argv:
            result["exit_code"] = 7
        if failed == "build" and argv == ["npm", "run", "build"]:
            result["exit_code"] = 8
        if failed == "missing-results" and "--reporter=json" in argv:
            Path(
                next(x.split("=", 1)[1] for x in argv if x.startswith("--outputFile="))
            ).unlink()
        if failed == "discovery" and "list" in argv:
            result["exit_code"] = 9
        return result

    monkeypatch.setattr(local, "command", fault)
    assert local.verify(args) == 1
    report = json.loads((Path(args.output) / "evidence.json").read_text())
    assert report["build"] is not None and report["cleanup_complete"]
    assert ["npm", "run", "build"] in calls
    with pytest.raises(ValueError):
        local.validate(Path(args.output) / "evidence.json", args.sha, "discovered")


@pytest.mark.parametrize(
    "change", ["sha", "suite", "age", "dirty", "artifact", "parity"]
)
def test_stale_mismatched_or_modified_evidence_refused(sandbox, change):
    args, _, _ = sandbox
    assert local.verify(args) == 0
    path = Path(args.output) / "evidence.json"
    report = json.loads(path.read_text())
    if change == "sha":
        report["verified_sha"] = "0" * 40
    if change == "suite":
        report["suite"] = "hosted"
    if change == "age":
        report["finished_unix"] = time.time() - 90000
    if change == "dirty":
        report["source_dirty_after"] = True
    if change == "artifact":
        (path.parent / "results-0.json").write_text("{}")
    if change == "parity":
        report["tests"][0]["discovered_cases"] = 2
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        local.validate(path, args.sha, "discovered")


def test_dirty_runner_is_labelled_diagnostic(sandbox):
    args, _, _ = sandbox
    (Path(args.repo) / "uncommitted.txt").write_text("diagnostic only")
    assert local.verify(args) == 1
    report = json.loads((Path(args.output) / "evidence.json").read_text())
    assert report["mode"] == "working-tree-diagnostic" and report["runner_dirty"]
    with pytest.raises(ValueError):
        local.validate(Path(args.output) / "evidence.json", args.sha, "discovered")


def test_lock_exclusion_and_release_without_inode_replacement(tmp_path):
    path = tmp_path / "guard"
    with local.resource_lock(path):
        inode = path.stat().st_ino
        with pytest.raises(ValueError, match="another local"):
            with local.resource_lock(path):
                pytest.fail("concurrent run")
    with local.resource_lock(path):
        assert path.stat().st_ino == inode


def test_symlink_lock_refused(tmp_path):
    path = tmp_path / "guard"
    path.symlink_to(tmp_path / "other")
    with pytest.raises(OSError):
        with local.resource_lock(path):
            pytest.fail("symlink lock")


def test_resource_memory_cpu_and_competing_process_refusal(tmp_path):
    (tmp_path / "123").mkdir()
    (tmp_path / "123/cmdline").write_bytes(
        b"node\0/work/node_modules/vitest/vitest.mjs\0run\0"
    )
    with pytest.raises(ValueError, match="visible logical"):
        local.resources(8, 100 * 1024**3, cpu=2, proc=tmp_path)
    with pytest.raises(ValueError, match="memory"):
        local.resources(8, 1024**3, cpu=32, proc=tmp_path)
    with pytest.raises(ValueError, match="competing"):
        local.resources(8, 100 * 1024**3, cpu=32, proc=tmp_path)


def test_contract_drift_fails_closed_and_hosted_filters_preserved(sandbox):
    args, _, _ = sandbox
    catalog = json.loads((Path(args.repo) / "ci/contracts.json").read_text())
    assert local.frontend_plan(catalog, "hosted")[1] == [
        ["npm", "test", "--", "src/owner.test.ts"]
    ]
    assert local.frontend_plan(catalog, "discovered")[1] == [["npm", "test", "--"]]
    catalog["contracts"]["hosted-frontend"]["steps"].append(
        {"cwd": "apps/live-control-ui", "argv": ["npm", "run", "unknown"]}
    )
    with pytest.raises(ValueError, match="unclassified"):
        local.frontend_plan(catalog, "discovered")


def test_interrupted_command_kills_child_and_removes_worktree(sandbox, monkeypatch):
    args, _, _ = sandbox

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(local, "command", interrupt)
    assert local.verify(args) == 1
    report = json.loads((Path(args.output) / "evidence.json").read_text())
    assert report["cleanup_complete"] and report["error"] == "KeyboardInterrupt"


def test_long_workflows_manual_and_short_security_regressions_preserved():
    for name in ["hosted-validation.yml", "world-ownership-core.yml"]:
        workflow = yaml.load(
            (local.ROOT / ".github/workflows" / name).read_text(),
            Loader=yaml.BaseLoader,
        )
        assert set(workflow["on"]) == {"workflow_dispatch"}
    for name in ["agent-legacy-import.yml", "rules-only-runtime.yml"]:
        workflow = yaml.load(
            (local.ROOT / ".github/workflows" / name).read_text(),
            Loader=yaml.BaseLoader,
        )
        assert "pull_request" in workflow["on"]
    short = yaml.load(
        (local.ROOT / ".github/workflows/local-verifier.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    assert "pull_request" in short["on"]
    assert "test_ci_local_frontend.py" in str(short)


def test_command_interrupt_terminates_owned_process_group(tmp_path, monkeypatch):
    signals = []

    class Child:
        pid = 1234
        count = 0

        def wait(self, timeout=None):
            self.count += 1
            if self.count == 1:
                raise KeyboardInterrupt()
            return -15

    child = Child()
    monkeypatch.setattr(local.subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(local.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    alive = iter([True, False, False])
    monkeypatch.setattr(local, "group_alive", lambda _: next(alive))
    with pytest.raises(KeyboardInterrupt):
        local.command(["unused"], tmp_path, tmp_path / "child.log", {})
    assert signals == [(1234, local.signal.SIGTERM)]


def test_locked_run_retains_failure_without_worktree_allocation(
    sandbox, monkeypatch, tmp_path
):
    args, _, _ = sandbox
    from contextlib import contextmanager

    @contextmanager
    def refused():
        raise ValueError("another local frontend verification owns the resource lock")
        yield

    monkeypatch.setattr(local, "resource_lock", refused)
    assert local.verify(args) == 1
    report = json.loads((Path(args.output) / "evidence.json").read_text())
    assert "resource lock" in report["error"] and not report["tests"]
    assert (
        len(local.git(args.repo, "worktree", "list", "--porcelain").split("worktree "))
        == 2
    )


@pytest.mark.parametrize("filtered", [True, False])
def test_only_declared_hosted_name_filters_allow_unselected_skips(tmp_path, filtered):
    frontend = tmp_path
    expected = local.inventory_keys(
        [{"file": str(frontend / "test.ts"), "name": "selected"}], frontend
    )
    result = {
        "testResults": [
            {
                "name": str(frontend / "test.ts"),
                "assertionResults": [
                    {"ancestorTitles": [], "title": "selected", "status": "passed"},
                    {"ancestorTitles": [], "title": "unselected", "status": "skipped"},
                ],
            }
        ]
    }
    argv = (
        ["npm", "test", "--", "-t", "selected"] if filtered else ["npm", "test", "--"]
    )
    report = local.case_parity(expected, result, frontend, argv)
    assert report["collection_parity"] == filtered
    assert report["reported_unselected_skips"] == int(filtered)
    result["testResults"][0]["assertionResults"][1]["status"] = "passed"
    assert not local.case_parity(expected, result, frontend, argv)["collection_parity"]


def test_header_cannot_relabel_hosted_as_discovered(sandbox):
    args, _, _ = sandbox
    args.suite = "hosted"
    assert local.verify(args) == 0
    path = Path(args.output) / "evidence.json"
    report = json.loads(path.read_text())
    report["suite"] = "discovered"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="provenance"):
        local.validate(path, args.sha, "discovered")


def test_header_cannot_claim_a_new_existing_untested_commit(sandbox):
    args, _, _ = sandbox
    assert local.verify(args) == 0
    subprocess.run(
        [
            "git",
            "-C",
            args.repo,
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.test",
            "commit",
            "--allow-empty",
            "-qm",
            "new untested SHA",
        ],
        check=True,
    )
    new = local.git(args.repo, "rev-parse", "HEAD")
    path = Path(args.output) / "evidence.json"
    report = json.loads(path.read_text())
    report["verified_sha"] = new
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="provenance"):
        local.validate(path, new, "discovered")


def test_real_interrupt_stops_grandchild_even_after_parent_exits(tmp_path):
    grand_marker = tmp_path / "grand.pid"
    parent_marker = tmp_path / "parent.pid"
    grand_code = (
        "import signal,time,os;from pathlib import Path;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        f"Path({str(grand_marker)!r}).write_text(str(os.getpid()));time.sleep(60)"
    )
    parent_code = (
        "import subprocess,sys,time,os;from pathlib import Path;"
        f"subprocess.Popen([sys.executable,'-c',{grand_code!r}]);"
        f"marker=Path({str(grand_marker)!r})\n"
        "while not marker.exists():time.sleep(0.02)\n"
        f"Path({str(parent_marker)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(60)"
    )
    wrapper_code = (
        "import sys,os;from pathlib import Path;"
        f"sys.path.insert(0,{str(local.ROOT / 'scripts')!r});import ci_local_frontend as tool\n"
        "try:\n"
        f" tool.command([sys.executable,'-c',{parent_code!r}],Path({str(tmp_path)!r}),Path({str(tmp_path / 'tree.log')!r}),dict(os.environ))\n"
        "except KeyboardInterrupt:pass\n"
    )
    wrapper = subprocess.Popen([sys.executable, "-c", wrapper_code])
    pgid = None
    try:
        deadline = time.monotonic() + 5
        while not parent_marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert parent_marker.exists()
        pgid = int(parent_marker.read_text())
        os.kill(wrapper.pid, signal.SIGINT)
        assert wrapper.wait(timeout=15) == 0
        assert not local.group_alive(pgid)
    finally:
        if wrapper.poll() is None:
            wrapper.kill()
            wrapper.wait()
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_documented_trigger_rollback_preserves_manual_jobs():
    block = "  pull_request:\n    branches: [main]\n    types: [opened, synchronize, reopened]\n"
    for name in ["hosted-validation.yml", "world-ownership-core.yml"]:
        text = (local.ROOT / ".github/workflows" / name).read_text()
        paused = yaml.load(text, Loader=yaml.BaseLoader)
        restored = yaml.load(
            text.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n" + block, 1),
            Loader=yaml.BaseLoader,
        )
        assert set(restored["on"]) == {"workflow_dispatch", "pull_request"}
        assert restored["on"]["pull_request"] == {
            "branches": ["main"],
            "types": ["opened", "synchronize", "reopened"],
        }
        assert restored["jobs"] == paused["jobs"]
        assert restored["permissions"] == paused["permissions"]


def test_existing_output_is_never_overwritten(sandbox):
    args, _, _ = sandbox
    assert local.verify(args) == 0
    evidence = Path(args.output) / "evidence.json"
    before = evidence.read_bytes()
    with pytest.raises(FileExistsError):
        local.verify(args)
    assert evidence.read_bytes() == before

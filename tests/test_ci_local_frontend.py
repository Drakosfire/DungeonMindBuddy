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

REAL_COMMAND = local.command


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    allocations = tmp_path / "allocations"
    allocations.mkdir()
    monkeypatch.setattr(local, "DEFAULT_WORKSPACE_ROOT", allocations)
    monkeypatch.setattr(local, "filesystem_uuid", lambda path: local.PROJECTS_UUID)
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


def test_filtered_result_cannot_hide_duplicate_selected_case_as_unselected(tmp_path):
    expected = local.inventory_keys(
        [{"file": str(tmp_path / "test.ts"), "name": "selected"}], tmp_path
    )
    result = {
        "testResults": [
            {
                "name": str(tmp_path / "test.ts"),
                "assertionResults": [
                    {"ancestorTitles": [], "title": "selected", "status": "passed"},
                    {"ancestorTitles": [], "title": "selected", "status": "skipped"},
                ],
            }
        ]
    }
    assert not local.case_parity(
        expected, result, tmp_path, ["npm", "test", "--", "-t", "selected"]
    )["collection_parity"]


def test_clean_committed_source_drift_during_install_is_refused(sandbox, monkeypatch):
    args, _, fake = sandbox

    def move_head(argv, cwd, log, env):
        result = fake(argv, cwd, log, env)
        if argv[:2] == ["npm", "ci"]:
            source = cwd.parents[1]
            (source / "changed.txt").write_text("new committed source")
            subprocess.run(["git", "-C", str(source), "add", "changed.txt"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(source),
                    "-c",
                    "user.name=Verifier",
                    "-c",
                    "user.email=verifier@example.test",
                    "commit",
                    "-qm",
                    "source drift",
                ],
                check=True,
            )
            assert not local.git(source, "status", "--porcelain")
        return result

    monkeypatch.setattr(local, "command", move_head)
    assert local.verify(args) == 1
    report = json.loads((Path(args.output) / "evidence.json").read_text())
    assert "exact source changed during install" in report["error"]
    assert report["source_sha_after"] != args.sha and not report["source_dirty_after"]
    assert report["cleanup_complete"]
    with pytest.raises(ValueError):
        local.validate(Path(args.output) / "evidence.json", args.sha, "discovered")


@pytest.mark.parametrize("ambient", [None, "/tmp", "/var/tmp"])
def test_default_allocation_ignores_ambient_temp_and_routes_child_storage(
    sandbox, monkeypatch, ambient
):
    args, _, fake = sandbox
    if ambient is None:
        monkeypatch.delenv("TMPDIR", raising=False)
    else:
        monkeypatch.setenv("TMPDIR", ambient)
    monkeypatch.setenv("npm_config_cache", "/tmp/inherited-npm-cache")
    monkeypatch.setenv("NPM_CONFIG_CACHE", "/tmp/inherited-uppercase-npm-cache")
    monkeypatch.setenv("npm_CONFIG_Cache", "/tmp/inherited-mixed-case-npm-cache")
    monkeypatch.setenv("NODE_COMPILE_CACHE", "/tmp/inherited-node-cache")
    monkeypatch.setattr(local.tempfile, "tempdir", "/tmp")
    before = dict(os.environ)
    observed = []

    def command(argv, cwd, log, env):
        source = Path(cwd).parents[1]
        run = source.parent.parent
        assert run.parent == local.DEFAULT_WORKSPACE_ROOT
        assert source == run / "verification/source"
        for key in ("TMPDIR", "TMP", "TEMP", "npm_config_cache", "NPM_CONFIG_CACHE",
                    "UV_CACHE_DIR", "XDG_CACHE_HOME", "NODE_COMPILE_CACHE"):
            path = Path(env[key])
            assert path.is_dir() and path.is_relative_to(run)
        assert {
            value for key, value in env.items() if key.lower() == "npm_config_cache"
        } == {str(run / "cache/npm")}
        # Exercise an actual subprocess's temporary-file choice, not only a dict.
        actual = subprocess.check_output(
            [sys.executable, "-c", "import tempfile; print(tempfile.gettempdir())"],
            env=env, text=True,
        ).strip()
        assert actual == env["TMPDIR"]
        observed.append(run)
        return fake(argv, cwd, log, env)

    monkeypatch.setattr(local, "command", command)
    assert local.verify(args) == 0
    report = local.validate(Path(args.output) / "evidence.json", args.sha, args.suite)
    assert observed and report["workspace_uuid"] == local.PROJECTS_UUID
    assert report["workspace_root"] == str(local.DEFAULT_WORKSPACE_ROOT)
    assert report["temporary_root"] == str(observed[0])
    assert not observed[0].exists()
    assert dict(os.environ) == before


@pytest.mark.parametrize("failure", ["missing", "file", "unwritable", "wrong-uuid", "empty-uuid"])
def test_storage_preflight_refuses_before_output_or_worktree_allocation(
    sandbox, monkeypatch, failure
):
    args, calls, _ = sandbox
    root = local.DEFAULT_WORKSPACE_ROOT
    if failure == "missing":
        args.workspace_root = str(root / "absent")
    elif failure == "file":
        target = root / "not-a-directory"
        target.write_text("retained")
        args.workspace_root = str(target)
    elif failure == "unwritable":
        monkeypatch.setattr(local.os, "access", lambda *_: False)
    else:
        args.workspace_uuid = "other-device" if failure == "wrong-uuid" else ""
    monkeypatch.setattr(
        local.tempfile, "TemporaryDirectory",
        lambda **_: pytest.fail("allocated before storage validation"),
    )
    with pytest.raises((ValueError, OSError)):
        local.verify(args)
    assert not Path(args.output).exists()
    assert not calls
    assert len(local.git(args.repo, "worktree", "list", "--porcelain").split("worktree ")) == 2


def test_explicit_workspace_and_uuid_support_an_authorized_other_executor(sandbox, monkeypatch):
    args, _, _ = sandbox
    root = Path(args.repo).parent / "explicit-workspace"
    root.mkdir()
    args.workspace_root = str(root)
    args.workspace_uuid = "authorized-device"
    monkeypatch.setattr(local, "filesystem_uuid", lambda _: "authorized-device")
    assert local.verify(args) == 0
    report = local.validate(Path(args.output) / "evidence.json", args.sha, args.suite)
    assert Path(report["temporary_root"]).parent == root
    assert report["workspace_uuid"] == "authorized-device"
    assert not list(root.iterdir())


def test_symlink_escape_is_checked_on_actual_backing_filesystem(sandbox, monkeypatch):
    args, _, _ = sandbox
    root = local.DEFAULT_WORKSPACE_ROOT
    outside = root.parent / "other-filesystem"
    outside.mkdir()
    alias = root / "escape"
    alias.symlink_to(outside, target_is_directory=True)
    args.workspace_root = str(alias)
    monkeypatch.setattr(local, "filesystem_uuid", lambda path: "wrong" if path == outside else local.PROJECTS_UUID)
    with pytest.raises(ValueError, match="filesystem"):
        local.verify(args)
    assert not Path(args.output).exists()
    assert not list(outside.iterdir())


def test_evidence_on_another_filesystem_is_refused_before_mkdir(sandbox, monkeypatch):
    args, _, _ = sandbox
    root = local.DEFAULT_WORKSPACE_ROOT
    monkeypatch.setattr(local, "filesystem_uuid", lambda path: local.PROJECTS_UUID if path == root else "wrong")
    with pytest.raises(ValueError, match="filesystem"):
        local.verify(args)
    assert not Path(args.output).exists()


@pytest.mark.parametrize("field", ["output", "workspace_root"])
def test_repository_local_allocations_are_refused(sandbox, field):
    args, _, _ = sandbox
    setattr(args, field, str(Path(args.repo) / "ci"))
    with pytest.raises(ValueError, match="outside the source repository"):
        local.verify(args)


def test_filesystem_uuid_uses_backing_mount_not_empty_automount_row(monkeypatch):
    observed = []

    def probe(argv, **kwargs):
        observed.append(argv)
        return "\n48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8\n"

    monkeypatch.setattr(local.subprocess, "check_output", probe)
    assert local.filesystem_uuid(Path("/example")) == local.PROJECTS_UUID
    assert observed == [["findmnt", "--target", "/example", "--noheadings", "--output", "UUID"]]


def test_filesystem_probe_error_fails_closed_without_allocation(sandbox, monkeypatch):
    args, calls, _ = sandbox

    def unavailable(_):
        raise FileNotFoundError("findmnt unavailable")

    monkeypatch.setattr(local, "filesystem_uuid", unavailable)
    with pytest.raises(FileNotFoundError, match="findmnt unavailable"):
        local.verify(args)
    assert not Path(args.output).exists()
    assert not calls


@pytest.mark.parametrize("field", ["output", "workspace_root"])
def test_repo_subdirectory_cannot_hide_repository_local_allocation(sandbox, field):
    args, _, _ = sandbox
    repository = Path(args.repo)
    args.repo = str(repository / "apps")
    setattr(args, field, str(repository / "ci"))
    with pytest.raises(ValueError, match="outside the source repository"):
        local.verify(args)


@pytest.mark.parametrize("replace_fails", [False, True])
def test_publish_evidence_keeps_old_report_until_replace(tmp_path, monkeypatch, replace_fails):
    destination = tmp_path / "evidence.json"
    destination.write_text('{"state": "old"}')
    replace = Path.replace
    new_report = {"state": "complete"}

    def observe_replace(source, target):
        assert source.parent == target.parent
        assert json.loads(target.read_text()) == {"state": "old"}
        assert json.loads(source.read_text()) == new_report
        if replace_fails:
            raise OSError("publication interrupted")
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", observe_replace)
    if replace_fails:
        with pytest.raises(OSError, match="publication interrupted"):
            local.publish_evidence(destination, new_report)
        assert json.loads(destination.read_text()) == {"state": "old"}
    else:
        local.publish_evidence(destination, new_report)
        assert json.loads(destination.read_text()) == new_report
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize(
    ("payload", "reason"),
    [(None, "missing"), ("{", "invalid JSON"), ("{}", "unexpected report structure"),
     ('{"testResults": null}', "unexpected report structure")],
)
def test_invalid_vitest_report_records_reason(sandbox, monkeypatch, payload, reason):
    args, _, fake = sandbox

    def command(argv, cwd, log, env):
        result = fake(argv, cwd, log, env)
        if "--reporter=json" in argv:
            path = Path(next(arg.split("=", 1)[1] for arg in argv if arg.startswith("--outputFile=")))
            if payload is None:
                path.unlink()
            else:
                path.write_text(payload)
        return result

    monkeypatch.setattr(local, "command", command)
    assert local.verify(args) == 1
    evidence = Path(args.output) / "evidence.json"
    step = json.loads(evidence.read_text())["tests"][0]
    assert step["results_file"].endswith(".json")
    assert step["results_error"] == reason
    assert step["collection_parity"] is False
    with pytest.raises(ValueError):
        local.validate(evidence, args.sha, args.suite)


@pytest.mark.parametrize("removal_fails", [False, True])
def test_final_inspection_failure_still_attempts_removal(sandbox, monkeypatch, removal_fails):
    args, _, fake = sandbox
    original_git = local.git
    build_ran = False

    def command(argv, cwd, log, env):
        nonlocal build_ran
        result = fake(argv, cwd, log, env)
        if Path(log).name == "build.log":
            build_ran = True
        return result

    def git(path, *argv, **kwargs):
        if build_ran and Path(path) != Path(args.repo) and argv == ("rev-parse", "HEAD"):
            raise ValueError("final source inspection failed")
        return original_git(path, *argv, **kwargs)

    original_run = local.subprocess.run

    def run(argv, *args, **kwargs):
        if removal_fails and argv[3:5] == ["worktree", "remove"]:
            raise ValueError("worktree removal failed")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(local.subprocess, "run", run)
    monkeypatch.setattr(local, "command", command)
    monkeypatch.setattr(local, "git", git)
    assert local.verify(args) == 1
    report = json.loads((Path(args.output) / "evidence.json").read_text())
    assert report["source_inspection_error"] == "final source inspection failed"
    assert report["error"] == (
        "worktree removal failed" if removal_fails else "final source inspection failed"
    )
    assert report["cleanup_complete"] is not removal_fails
    registrations = original_git(Path(args.repo), "worktree", "list", "--porcelain")
    assert registrations.count("worktree ") == (2 if removal_fails else 1)


def test_timeout_retains_step_receipt_and_cleans_worktree(sandbox, monkeypatch):
    args, _, _ = sandbox
    argv = [sys.executable, "-u", "-c", "import time; print('started'); time.sleep(60)"]
    monkeypatch.setattr(local, "COMMAND_TIMEOUT_SECONDS", 0.25)
    monkeypatch.setattr(
        local, "command",
        lambda _argv, cwd, log, env: REAL_COMMAND(argv, cwd, log, env),
    )

    assert local.verify(args) == 1
    out = Path(args.output)
    receipt = json.loads((out / "run-receipt.json").read_text())
    assert receipt["cleanup_complete"]
    assert receipt["timed_out_step"]["argv"] == argv
    assert receipt["timed_out_step"]["timeout_seconds"] == 0.25
    assert receipt["timed_out_step"]["elapsed_seconds"] >= 0.25
    assert receipt["timed_out_step"]["exit_code"] == 1
    assert receipt["timed_out_step"]["log"] == "install.log"
    assert (out / "install.log").read_text() == "started\n"
    assert "timed out" in receipt["error"]

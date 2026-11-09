"""Fail-closed qualification orchestration contracts; real image evidence is separate."""
import ast
import json
import sys
from types import SimpleNamespace

import pytest
import yaml

from scripts.qualification import image_probe as probe


def test_qualification_workflow_pins_source_and_preserves_premerge_checks():
    workflow = yaml.load((probe.ROOT / ".github/workflows/qualification.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch", "schedule", "push", "pull_request"}
    assert workflow["on"]["push"]["tags"] == ["rc/**"]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
    assert workflow["on"]["pull_request"]["branches"] == ["main"]
    assert "scripts/qualification/**" in workflow["on"]["pull_request"]["paths"]
    for job in ("full-regression", "image-and-browser"):
        assert workflow["jobs"][job]["needs"] == "source"
        checkout = workflow["jobs"][job]["steps"][0]
        assert checkout["with"]["ref"] == "${{ needs.source.outputs.sha }}"
    commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["image-and-browser"]["steps"])
    assert "python -m scripts.qualification.image_probe --output" in commands
    assert "--image-only" not in commands
    aggregate = workflow["jobs"]["qualification-result"]
    assert set(aggregate["needs"]) == {"source", "full-regression", "image-and-browser"}
    assert aggregate["if"] == "always()"
    assert 'test "$SOURCE" = success && test "$FULL" = success && test "$IMAGE" = success' in aggregate["steps"][0]["run"]


def test_packaging_exception_is_source_only_and_old_pr_gates_remain_unfiltered():
    rules = (probe.ROOT / ".dockerignore").read_text().splitlines()
    source_rules = [line for line in rules if line.startswith("!src/corpus/")]
    assert source_rules == ["!src/corpus/", "!src/corpus/__init__.py", "!src/corpus/session_recap_paths.py"]
    assert "src/corpus/**" in rules and "**/corpus/" in rules
    for filename in ("hosted-validation.yml", "world-ownership-core.yml"):
        workflow = yaml.load((probe.ROOT / ".github/workflows" / filename).read_text(), Loader=yaml.BaseLoader)
        assert set(workflow["on"]["pull_request"]) == {"branches", "types"}


def test_startup_exit_is_reported_by_the_same_live_health_observer():
    instance = object.__new__(probe.Probe)
    instance.state = lambda name: {"Running": False, "ExitCode": 23}
    with pytest.raises(probe.QualificationFailure, match="startup_exit:23"):
        instance.wait_live("owned-probe", "http://127.0.0.1:1")


def test_clean_source_required_before_full_qualification():
    instance = object.__new__(probe.Probe)
    instance.dirty = True
    with pytest.raises(probe.QualificationFailure, match="clean committed source"):
        instance.boot(image_only=False)


def test_insufficient_docker_storage_stops_before_build_or_resource_allocation(monkeypatch):
    instance = object.__new__(probe.Probe)
    instance.dirty = False
    instance.report = {}
    calls = []
    instance.docker = lambda *args: (calls.append(args) or SimpleNamespace(stdout="/docker-root\n"))
    monkeypatch.setattr(probe.shutil, "disk_usage", lambda path: SimpleNamespace(free=1))
    with pytest.raises(probe.QualificationFailure, match="less than 8 GiB"):
        instance.boot(image_only=True)
    assert calls == [("info", "--format", "{{.DockerRootDir}}")]


@pytest.mark.parametrize("failed_cleanup", [False, True])
def test_process_failure_or_cleanup_failure_cannot_publish_qualified(tmp_path, monkeypatch, failed_cleanup):
    class FakeProbe:
        def __init__(self, output):
            self.output = output
            self.output.mkdir()
            self.report = {"qualified": False, "cleanup": {}}

        def boot(self, *, image_only):
            if failed_cleanup:
                self.report["qualified"] = True
            else:
                raise probe.QualificationFailure("real startup boundary failed")

        def cleanup(self):
            self.report["cleanup"]["owned-resource"] = not failed_cleanup

    monkeypatch.setattr(probe, "Probe", FakeProbe)
    monkeypatch.setattr(sys, "argv", ["image_probe", "--output", str(tmp_path / "evidence")])
    assert probe.main() == 1
    report = json.loads((tmp_path / "evidence/result.json").read_text())
    assert report["qualified"] is False
    assert "cleanup_error" in report if failed_cleanup else "failure" in report


def test_cleanup_uses_only_explicit_owned_names_and_retains_logs(tmp_path):
    instance = object.__new__(probe.Probe)
    instance.output = tmp_path
    instance.prefix = "dmb-qualification-test-owned"
    instance.containers = [instance.prefix + "-api", instance.prefix + "-db"]
    instance.network, instance.volume = instance.prefix + "-network", instance.prefix + "-state"
    instance.postgres_volume = instance.prefix + "-postgres-data"
    instance.postgres_volume_created = True
    instance.network_created = instance.volume_created = True
    instance.report = {"cleanup": {}}
    calls = []

    def docker(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="owned log", stderr="")

    instance.docker = docker
    instance.cleanup()
    assert all(any(name.startswith(instance.prefix) for name in args) for args in calls)
    assert not any("prune" in args for args in calls)
    assert len(list(tmp_path.glob("*.log"))) == 2
    assert all(instance.report["cleanup"].values())
    assert ("volume", "rm", instance.postgres_volume) in calls
    assert all(("rm", "--force", "--volumes", name) in calls for name in instance.containers)


def test_canonical_core_migrations_are_selected_by_installed_pin(monkeypatch, tmp_path):
    from scripts.qualification import bootstrap_core

    direct = {"url": "https://github.com/Drakosfire/DungeonMind.git", "vcs_info": {"commit_id": "a" * 40}}
    monkeypatch.setattr(bootstrap_core.importlib.metadata, "distribution", lambda name: SimpleNamespace(read_text=lambda path: json.dumps(direct)))
    assert bootstrap_core.installed_core_pin() == "a" * 40
    direct["url"] = "https://wrong-owner.test/repo.git"
    with pytest.raises(ValueError, match="source owner"):
        bootstrap_core.installed_core_pin()


def test_repaired_modules_retain_all_original_test_definitions():
    manifest = json.loads((probe.ROOT / "ci/collection-repairs.json").read_text())
    for path, expected in manifest["original_test_definitions"].items():
        tree = ast.parse((probe.ROOT / path).read_text())
        actual = sorted(node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"))
        assert actual == expected
        actual_params = sorted(ast.dump(node, show_empty=True) for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "parametrize")
        assert actual_params == manifest["original_parametrization"][path]


def test_postgres_readiness_rejects_socket_only_initialization_server(monkeypatch):
    instance = object.__new__(probe.Probe)
    calls = []
    sleeps = []

    def docker(*args, **kwargs):
        calls.append(args)
        # A socket probe would incorrectly accept the temporary server at once.
        is_tcp = "-h" in args and args[args.index("-h") + 1] == "127.0.0.1"
        return SimpleNamespace(returncode=0 if not is_tcp or len(calls) == 3 else 1)

    instance.docker = docker
    monkeypatch.setattr(probe.time, "sleep", sleeps.append)
    instance.wait_postgres("owned-postgres")
    assert len(calls) == 3
    assert sleeps == [1, 1]
    assert all(args[-2:] == ("-d", "postgres") for args in calls)


def test_postgres_readiness_is_bounded_and_fails_closed(monkeypatch):
    instance = object.__new__(probe.Probe)
    calls = []
    instance.docker = lambda *args, **kwargs: (calls.append(args) or SimpleNamespace(returncode=1))
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    with pytest.raises(probe.QualificationFailure, match="disposable_postgres_unavailable"):
        instance.wait_postgres("owned-postgres")
    assert len(calls) == 60


def test_native_database_command_propagates_failure_and_scopes_dsn(tmp_path, monkeypatch):
    from scripts.qualification import native_database as native

    closed = []
    calls = []
    class OwnedDatabase:
        def __init__(self, output):
            assert output == tmp_path / "owned"
        def __enter__(self):
            return "postgresql://owned@127.0.0.1:1234/qualification_native_test"
        def __exit__(self, *args):
            closed.append(True)
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=17)
    monkeypatch.setattr(native, "NativeTestDatabase", OwnedDatabase)
    monkeypatch.setattr(native.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["native_database", "--output", str(tmp_path / "owned")])
    assert native.main() == 17
    assert closed == [True]
    assert calls[0][0][-2:] == ["run", "full-regression"]
    assert calls[0][1]["env"]["DMB_CUTOVER_TEST_DATABASE_URL"].endswith("/qualification_native_test")


def test_native_database_cleanup_failure_is_fatal_and_named(tmp_path, monkeypatch):
    from scripts.qualification import native_database as native

    instance = native.NativeTestDatabase(tmp_path / "owned")
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=1, stdout="", stderr="cleanup refused")
    monkeypatch.setattr(native.subprocess, "run", run)
    with pytest.raises(probe.QualificationFailure, match="cleanup failed"):
        instance.__exit__(None, None, None)
    assert calls == [["docker", "logs", instance.name], ["docker", "rm", "--force", "--volumes", instance.name]]
    assert json.loads((instance.output / "result.json").read_text())["cleaned"] is False

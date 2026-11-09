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
    assert set(workflow["on"]) == {"workflow_dispatch", "schedule", "push"}
    assert workflow["on"]["push"]["tags"] == ["rc/**"]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
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

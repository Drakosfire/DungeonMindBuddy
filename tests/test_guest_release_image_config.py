"""Release helper must bind guest build settings to the image it returns."""
import hashlib
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_buddy_release_image.sh"
SHA = "a" * 40
IMAGE = "sha256:" + "b" * 64


@pytest.fixture
def fake_tools(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "git").write_text(f'''#!/bin/sh
case "$1" in
  rev-parse) echo {SHA} ;;
  status) : ;;
esac
''')
    (bindir / "docker").write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["DOCKER_CALLS"], "a") as f:
    f.write(json.dumps(args) + "\\n")
if args[:2] == ["image", "ls"]:
    print(os.environ.get("FAKE_EXISTING", ""))
elif args[:2] == ["image", "inspect"]:
    fmt = args[3]
    if fmt == "{{.Id}}": print(os.environ["FAKE_IMAGE"])
    elif "revision" in fmt: print(os.environ["FAKE_REVISION"])
    else: print(os.environ.get("FAKE_CONFIG", "<no value>"))
''')
    for path in bindir.iterdir():
        path.chmod(0o755)
    return bindir, tmp_path / "calls"


def run_helper(fake_tools, **values):
    bindir, calls = fake_tools
    env = os.environ.copy()
    for key in ("VITE_HOSTED_GUEST_BUILD", "VITE_HOSTED_GUEST_GRAPH", "VITE_GUEST_RELEASE_REVIEW", "VITE_GUEST_RELEASE_PAGE", "VITE_GUEST_HOME_PUBLIC_ID"):
        env.pop(key, None)
    env.update(PATH=f"{bindir}:{env['PATH']}", DOCKER_CALLS=str(calls),
               FAKE_IMAGE=IMAGE, FAKE_REVISION=SHA, **values)
    result = subprocess.run(["bash", str(SCRIPT), SHA], env=env, text=True, capture_output=True)
    import json
    return result, [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []


def test_default_build_preserves_legacy_tag(fake_tools):
    result, calls = run_helper(fake_tools, FAKE_CONFIG="review=0;page=0;home=")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == IMAGE
    build = next(c for c in calls if c[0] == "build")
    assert "dungeonmindbuddy:" + SHA in build
    assert "VITE_GUEST_RELEASE_REVIEW=0" in build
    assert "VITE_GUEST_RELEASE_PAGE=0" in build


def test_configured_build_is_separately_identified(fake_tools):
    config = "review=1;page=0;home="
    result, calls = run_helper(fake_tools, VITE_GUEST_RELEASE_REVIEW="1", FAKE_CONFIG=config)
    assert result.returncode == 0, result.stderr
    build = next(c for c in calls if c[0] == "build")
    assert "dungeonmindbuddy:" + SHA + "-guest-" + hashlib.sha256(config.encode()).hexdigest()[:16] in build
    assert "VITE_GUEST_RELEASE_REVIEW=1" in build
    assert "org.dungeonmindbuddy.guest-build=" + config in build


def test_mismatched_config_is_rejected_even_with_matching_source(fake_tools):
    result, _ = run_helper(fake_tools, VITE_GUEST_RELEASE_REVIEW="1", FAKE_CONFIG="review=0;page=0;home=")
    assert result.returncode == 1
    assert "configuration does not match" in result.stderr


def test_matching_existing_configured_image_is_reused(fake_tools):
    config = "review=1;page=1;home=12345678-1234-1234-1234-123456789abc"
    tag = "dungeonmindbuddy:" + SHA + "-guest-" + hashlib.sha256(config.encode()).hexdigest()[:16]
    result, calls = run_helper(
        fake_tools, VITE_GUEST_RELEASE_REVIEW="1", VITE_GUEST_RELEASE_PAGE="1",
        VITE_GUEST_HOME_PUBLIC_ID="12345678-1234-1234-1234-123456789abc",
        FAKE_CONFIG=config, FAKE_EXISTING=tag,
    )
    assert result.returncode == 0, result.stderr
    assert not any(c[0] == "build" for c in calls)


def test_default_tag_rejects_a_labeled_configured_image(fake_tools):
    result, _ = run_helper(fake_tools, FAKE_CONFIG="review=1;page=0;home=")
    assert result.returncode == 1
    assert "configuration does not match" in result.stderr


def test_unlabelled_image_is_not_accepted(fake_tools):
    result, _ = run_helper(fake_tools)
    assert result.returncode == 1
    assert "configuration does not match" in result.stderr


@pytest.mark.parametrize("values", [
    {"VITE_GUEST_RELEASE_REVIEW": "true"},
    {"VITE_GUEST_RELEASE_PAGE": "1", "VITE_GUEST_HOME_PUBLIC_ID": "NOT-A-UUID"},
    {"VITE_GUEST_HOME_PUBLIC_ID": "12345678-1234-1234-1234-123456789abc"},
])
def test_invalid_configuration_does_not_invoke_docker(fake_tools, values):
    result, calls = run_helper(fake_tools, **values)
    assert result.returncode == 2
    assert calls == []


def test_guest_graph_build_has_distinct_configuration_and_tag(fake_tools):
    config = "review=0;page=0;home=;graph=1"
    result, calls = run_helper(fake_tools, VITE_HOSTED_GUEST_GRAPH="1", FAKE_CONFIG=config)
    assert result.returncode == 0, result.stderr
    build = next(c for c in calls if c[0] == "build")
    assert "VITE_HOSTED_GUEST_GRAPH=1" in build
    assert "dungeonmindbuddy:" + SHA + "-guest-" + hashlib.sha256(config.encode()).hexdigest()[:16] in build
    assert "org.dungeonmindbuddy.guest-build=" + config in build


def test_invalid_guest_graph_flag_does_not_invoke_docker(fake_tools):
    result, calls = run_helper(fake_tools, VITE_HOSTED_GUEST_GRAPH="true")
    assert result.returncode == 2
    assert calls == []


def test_publisher_keeps_graph_builds_distinct_and_default_off():
    workflow = (SCRIPT.parents[1] / ".github/workflows/publish-buddy-image.yml").read_text()
    dockerfile = (SCRIPT.parents[1] / "Dockerfile.production").read_text()
    assert "ARG VITE_HOSTED_GUEST_GRAPH=0" in dockerfile
    assert "hosted_guest_graph:" in workflow
    assert "default: false" in workflow
    assert "VITE_HOSTED_GUEST_GRAPH=\"$GUEST_GRAPH\"" in workflow
    assert 'tag="$REVISION-guest-graph"' in workflow
    assert 'docker image push "$repository:$tag"' in workflow


def test_guest_graph_release_rejects_older_source_and_accepts_complete_contract(tmp_path):
    script = SCRIPT.parent / "verify_guest_graph_release.sh"
    assert subprocess.run(["bash", str(script), str(tmp_path)], capture_output=True).returncode != 0
    files = {
        "Dockerfile.production": "ARG VITE_HOSTED_GUEST_GRAPH=0\n",
        "apps/live-control-ui/src/App.tsx": "VITE_HOSTED_GUEST_GRAPH\n",
        "src/application_state/index_graph/sessions.py": "DMB_HOSTED_GUEST_GRAPH_ENABLED\n",
        "apps/live_control_server/services/hosted_auth.py": "DMB_HOSTED_GUEST_GRAPH_ENABLED\n",
    }
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    assert subprocess.run(["bash", str(script), str(tmp_path)], capture_output=True).returncode == 0
    (tmp_path / "apps/live_control_server/services/hosted_auth.py").write_text("")
    assert subprocess.run(["bash", str(script), str(tmp_path)], capture_output=True).returncode != 0


def test_serving_source_requires_exact_merged_pr_tip_and_parent(monkeypatch):
    import importlib.util
    import json
    script = SCRIPT.parent / "verify_buddy_serving_release.py"
    spec = importlib.util.spec_from_file_location("verify_buddy_serving_release", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    revision, parent, branch = "a" * 40, "b" * 40, "codex/serving-release"
    metadata = {"merged": True, "merge_commit_sha": revision, "base": {"ref": branch}}
    calls = []
    monkeypatch.setenv("GH_TOKEN", "not-a-real-token")
    def output(command, **kwargs):
        calls.append(command)
        if command[0] == "gh":
            return json.dumps(metadata)
        if command[-1].endswith("^1"):
            return parent + "\n"
        if command[-1].endswith("^{tree}"):
            return ("e" if command[-1].startswith(parent) else "f") * 40 + "\n"
        return revision + "\n"
    monkeypatch.setattr(module.subprocess, "check_output", output)
    monkeypatch.setattr(module.subprocess, "run", lambda command, **kwargs: calls.append(command))
    module.verify(revision=revision, parent=parent, pr="4607", branch=branch, repository="Drakosfire/DungeonMindBuddy")
    assert any(command[:2] == ["git", "fetch"] for command in calls)
    for bad in ({**metadata, "merged": False}, {**metadata, "merge_commit_sha": "c" * 40}, {**metadata, "base": {"ref": "codex/other"}}):
        with pytest.raises(ValueError):
            module.validate_pr(bad, revision=revision, branch=branch)
    with pytest.raises(ValueError):
        module.verify(revision=revision, parent=parent, pr="4607", branch="main", repository="Drakosfire/DungeonMindBuddy")
    with pytest.raises(ValueError):
        module.verify(revision=revision, parent=parent, pr="4607", branch=branch, repository="Other/Repo")
    metadata["merged"] = True
    with pytest.raises(ValueError):
        module.verify(revision=revision, parent="c" * 40, pr="4607", branch=branch, repository="Drakosfire/DungeonMindBuddy")
    def old_tip(command, **kwargs):
        if command[0] == "gh":
            return json.dumps(metadata)
        if command[-1].endswith("^1"):
            return parent + "\n"
        return "d" * 40 + "\n"
    monkeypatch.setattr(module.subprocess, "check_output", old_tip)
    with pytest.raises(ValueError):
        module.verify(revision=revision, parent=parent, pr="4607", branch=branch, repository="Drakosfire/DungeonMindBuddy")


def test_serving_parent_requires_ancestor_with_identical_tree(tmp_path):
    import importlib.util

    script = SCRIPT.parent / "verify_buddy_serving_release.py"
    spec = importlib.util.spec_from_file_location("verify_buddy_serving_release_git", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
            cwd=tmp_path, text=True, stderr=subprocess.PIPE,
        ).strip()

    git("init", "-q")
    tracked = tmp_path / "source.txt"
    tracked.write_text("deployed\n")
    git("add", "source.txt")
    git("commit", "-q", "-m", "deployed")
    deployed = git("rev-parse", "HEAD")
    tracked.write_text("intermediate\n")
    git("commit", "-qam", "intermediate")
    different_ancestor = git("rev-parse", "HEAD")
    tracked.write_text("deployed\n")
    git("commit", "-qam", "identical serving tree")
    base = git("rev-parse", "HEAD")
    tracked.write_text("candidate\n")
    git("commit", "-qam", "candidate")
    candidate = git("rev-parse", "HEAD")
    unrelated = git("commit-tree", git("rev-parse", f"{deployed}^{{tree}}"), "-m", "unrelated")
    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        module.validate_serving_parent(revision=candidate, parent=base)
        module.validate_serving_parent(revision=candidate, parent=deployed)
        with pytest.raises(ValueError, match="differs"):
            module.validate_serving_parent(revision=candidate, parent=different_ancestor)
        with pytest.raises(ValueError, match="not an ancestor"):
            module.validate_serving_parent(revision=candidate, parent=unrelated)
    finally:
        os.chdir(original)


def test_guest_build_flag_is_bound_to_image_config(fake_tools):
    config = "review=0;page=0;home=;graph=1;build=1"
    result, calls = run_helper(fake_tools, VITE_HOSTED_GUEST_GRAPH="1", VITE_HOSTED_GUEST_BUILD="1", FAKE_CONFIG=config)
    assert result.returncode == 0, result.stderr
    build = next(c for c in calls if c[0] == "build")
    assert "VITE_HOSTED_GUEST_BUILD=1" in build
    assert "org.dungeonmindbuddy.guest-build=" + config in build


def test_guest_build_requires_guest_graph(fake_tools):
    result, _ = run_helper(fake_tools, VITE_HOSTED_GUEST_BUILD="1")
    assert result.returncode == 2

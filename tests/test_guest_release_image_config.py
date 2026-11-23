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
    for key in ("VITE_GUEST_RELEASE_REVIEW", "VITE_GUEST_RELEASE_PAGE", "VITE_GUEST_HOME_PUBLIC_ID"):
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

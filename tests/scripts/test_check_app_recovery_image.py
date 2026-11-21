"""Safety checks for building from the reviewed runtime image."""
import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from scripts import check_app_recovery_image as builder

SHA = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64


def invoke(label, tags=""):
    def fake_run(*args):
        if args[1] == "context":
            return json.dumps("unix:///var/run/docker.sock")
        if args[0] == "git":
            return SHA + "\n"
        assert args[:3] == ("docker", "--host", "unix:///var/run/docker.sock")
        if "inspect" in args:
            return json.dumps([{"Id": IMAGE_ID, "Config": {"Labels": {"org.opencontainers.image.revision": label}}}])
        return tags
    with patch.object(sys, "argv", ["builder", SHA, SHA, "runtime"]), patch.object(builder, "run", fake_run), patch.object(subprocess, "run") as execution:
        with pytest.raises(SystemExit):
            builder.main()
        assert not execution.called


def test_rejects_runtime_with_wrong_revision_before_build():
    invoke("c" * 40)


def test_rejects_existing_output_tag_before_build():
    invoke(SHA, f"buddy-app-recovery:{SHA}-{SHA}\n")


def test_builds_with_distinct_tool_and_runtime_revisions():
    tool_sha, runtime_sha = "a" * 40, "c" * 40
    calls = []

    def fake_run(*args):
        if args[1] == "context":
            return json.dumps("unix:///var/run/docker.sock")
        if args[0] == "git":
            return args[3].removesuffix("^{commit}") + "\n"
        assert args[:3] == ("docker", "--host", "unix:///var/run/docker.sock")
        if "inspect" in args:
            return json.dumps([{"Id": IMAGE_ID, "Config": {"Labels": {"org.opencontainers.image.revision": runtime_sha}}}])
        return ""

    def fake_subprocess(args, **kwargs):
        calls.append(args)
        if args[0] == "git":
            return subprocess.CompletedProcess(args, 0, stdout=b"fixture")
        return subprocess.CompletedProcess(args, 0)

    with patch.object(sys, "argv", ["builder", tool_sha, runtime_sha, "runtime"]), patch.object(builder, "run", fake_run), patch.object(subprocess, "run", fake_subprocess):
        builder.main()
    assert calls[0] == ["git", "show", f"{tool_sha}:Dockerfile.app-recovery"]
    assert calls[1] == ["git", "show", f"{runtime_sha}:scripts/application_state_authority.py"]
    build = calls[2]
    assert build[:3] == ["docker", "--host", "unix:///var/run/docker.sock"]
    assert f"BUDDY_RUNTIME_IMAGE={IMAGE_ID}" in build
    assert f"org.opencontainers.image.revision={tool_sha}" in build
    assert f"org.dungeonmind.runtime.revision={runtime_sha}" in build
    assert f"buddy-app-recovery:{tool_sha}-{runtime_sha}" in build
    assert build[build.index("--file") + 1].endswith("/Dockerfile.app-recovery")


def test_rejects_remote_docker_endpoint_before_image_inspection():
    def fake_run(*args):
        if args[0] == "git":
            return SHA + "\n"
        assert args[1] == "context"
        return json.dumps("ssh://remote-host")
    with patch.object(sys, "argv", ["builder", SHA, SHA, "runtime"]), patch.object(builder, "run", fake_run), patch.object(subprocess, "run") as execution:
        with pytest.raises(SystemExit):
            builder.main()
        assert not execution.called


def test_rejects_docker_host_override_before_inspection():
    with patch.object(sys, "argv", ["builder", SHA, SHA, "runtime"]), patch.dict(builder.os.environ, {"DOCKER_HOST": "ssh://remote-host"}), patch.object(builder, "run", return_value=SHA + "\n") as call, patch.object(subprocess, "run") as execution:
        with pytest.raises(SystemExit):
            builder.main()
        assert call.call_count == 2
        assert not execution.called

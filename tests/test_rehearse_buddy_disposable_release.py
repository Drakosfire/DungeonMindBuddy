"""Exercise the real Bash entry point's builder fence without a Docker daemon."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rehearse_buddy_disposable_release.sh"
DOCKER = """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with open(os.environ["DOCKER_CALLS"], "a") as stream:
    stream.write(json.dumps(args) + "\\n")
assert args[:2] == ["--context", "default"]
assert not any(key in os.environ for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "BUILDX_BUILDER", "BUILDKIT_HOST"))
if args[2:4] == ["context", "inspect"]:
    print("unix:///var/run/docker.sock")
elif args[2:4] == ["buildx", "ls"]:
    state = Path(os.environ["BUILDX_CONFIG"])
    assert state.parent.parent == Path(os.environ["BUDDY_REHEARSAL_ROOT"])
    assert state.name == "buildx" and not list(state.iterdir())
    print(os.environ["BUILDER_RECORD"])
elif args[2:4] == ["buildx", "build"]:
    assert args[4:6] == ["--builder", "default"]
    assert Path(args[-1], "Dockerfile.production").is_file()
    sys.exit(73)
else:
    sys.exit(1)
"""


class BuilderFenceTest(unittest.TestCase):
    def run_with_builder(self, *, driver, endpoint):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            (repo / "Dockerfile.production").touch()

            def git(*args):
                return subprocess.check_output(
                    ["git", "-c", "user.name=Rehearsal", "-c", "user.email=rehearsal@example.invalid", *args],
                    cwd=repo, text=True, stderr=subprocess.PIPE,
                ).strip()

            git("init", "-q")
            git("add", "Dockerfile.production")
            git("commit", "-qm", "prior")
            prior = git("rev-parse", "HEAD")
            git("commit", "--allow-empty", "-qm", "candidate")
            candidate = git("rev-parse", "HEAD")
            git("update-ref", "refs/remotes/origin/main", candidate)

            shim = root / "docker"
            shim.write_text(DOCKER)
            shim.chmod(0o700)
            recorded = root / "docker-calls"
            cwd = root / "rehearsal"
            cwd.mkdir()
            env = {
                "PATH": f"{root}:{os.environ['PATH']}",
                "HOME": str(root),
                "BUILDX_BUILDER": "off-host",
                "BUILDKIT_HOST": "tcp://off-host.invalid:1234",
                "BUILDX_CONFIG": str(root / "untrusted-buildx"),
                "DOCKER_HOST": "tcp://off-host.invalid:2375",
                "DOCKER_CONTEXT": "off-host",
                "BUDDY_REHEARSAL_ROOT": str(cwd),
                "BUILDER_RECORD": json.dumps(
                    {"Name": "default", "Driver": driver, "Nodes": [{"Endpoint": endpoint}]}
                ),
                "DOCKER_CALLS": str(recorded),
            }
            run = subprocess.run(
                ["bash", str(SCRIPT), candidate, prior], cwd=repo, env=env,
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(list(cwd.iterdir()), [], "task scratch leaked")
            return run, [json.loads(line) for line in recorded.read_text().splitlines()]

    def test_ignores_ambient_override_and_pins_build(self):
        run, calls = self.run_with_builder(driver="docker", endpoint="default")
        self.assertEqual(run.returncode, 73, run.stderr)
        self.assertEqual([c[2:6] for c in calls if c[2:4] == ["buildx", "build"]],
                         [["buildx", "build", "--builder", "default"]])

    def test_refuses_remote_driver_or_endpoint_before_any_build(self):
        for driver, endpoint in (("remote", "default"), ("docker", "tcp://off-host.invalid:1234")):
            with self.subTest(driver=driver, endpoint=endpoint):
                run, calls = self.run_with_builder(driver=driver, endpoint=endpoint)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertIn("Refusing to build", run.stderr)
                self.assertFalse(any(c[2:4] == ["buildx", "build"] for c in calls))

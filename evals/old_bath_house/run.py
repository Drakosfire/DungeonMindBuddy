"""Launch a pinned Buddy release and measure Old Bath House on isolated state."""

import argparse
import json
import os
import secrets
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from .isolation import APP_DSN, CORE_DSN, read_fixture, verify_target

STATBLOCK_URL = "DUNGEONMIND_STATBLOCKS_BASE_URL"
STATBLOCK_KEY = "DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY"


def inspect_image(image):
    data = subprocess.check_output(["docker", "image", "inspect", image], text=True)
    return json.loads(data)[0]


def wait_ready(origin, container):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if subprocess.check_output(
            ["docker", "inspect", "--format", "{{.State.Running}}", container], text=True,
        ).strip() != "true":
            raise RuntimeError("Isolated Buddy exited before readiness")
        try:
            with urlopen(origin + "/health/ready", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.25)
    raise TimeoutError("Isolated Buddy did not reach readiness")


def run(fixture_path, fixture_digest, output):
    fixture = read_fixture(fixture_path, fixture_digest)
    verify_target(fixture, os.environ)
    external = urlsplit(os.environ[STATBLOCK_URL])
    if external.scheme != "http" or external.hostname != "127.0.0.1" or not external.port:
        raise ValueError("Pinned assets require a disposable loopback statblock service")
    runtime = fixture["runtime"]
    image = runtime["image"]
    info = inspect_image(image)
    if info["Id"] != image or info["Config"]["Labels"]["org.opencontainers.image.revision"] != runtime["source"]:
        raise ValueError("Local Buddy image differs from the fixture release")
    if info["Config"]["Labels"].get("org.dungeonmindbuddy.guest-build") != runtime["guest_build"]:
        raise ValueError("Local Buddy image guest build differs from the fixture release")

    origin = fixture["origin"]
    port = str(urlsplit(origin).port)
    root = Path(fixture["runtime_state"]).resolve(strict=True)
    if root == Path("/") or not all((root / item).is_dir() for item in ("managed", "artifacts", "sessions")):
        raise ValueError("Expected staged disposable Buddy state directories")
    env = {key: os.environ[key] for key in (APP_DSN, CORE_DSN, STATBLOCK_URL, STATBLOCK_KEY)}
    token = secrets.token_urlsafe(32)
    env.update({
        "DMB_DEPLOYMENT_ENVIRONMENT": "local",
        "DMB_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": token,
        "DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN": origin,
        "DMB_AGENT_GRAPH_LOCAL_API_HOST": f"127.0.0.1:{port}",
        "DUNGEONMIND_STATBLOCKS_ENABLED": "true",
        "DMB_MANAGED_WORLD_DATA_ROOT": "/benchmark/managed",
        "DMB_ARTIFACT_DATA_ROOT": "/benchmark/artifacts",
        "DUNGEONMIND_LIVE_SESSION_DIR": "/benchmark/sessions",
        "DMB_AGENT_GRAPH_SESSION_STORE": "/tmp/old-bath-house-auth/local-session.json",
    })
    output.mkdir(mode=0o700)
    container_args = [
        "docker", "run", "--network", "host",
        "--mount", f"type=bind,source={root},target=/benchmark",
        "--mount", f"type=bind,source={Path(__file__).with_name('local_ui.py').resolve()},target=/app/benchmark_local_ui.py,readonly",
    ]
    for key in env:
        container_args.extend(["-e", key])
    launch_env = dict(os.environ, **env)
    schema = subprocess.check_output(
        [*container_args, "--rm", "--entrypoint", "python", image, "-c",
         "from application_state.cli import _current_and_head; "
         "from application_state.config import load_runtime_dsn; "
         "print(*_current_and_head(load_runtime_dsn()))"],
        env=launch_env, text=True,
    ).strip()
    if schema.split() != [runtime["app_schema"]] * 2:
        raise ValueError("Buddy installed and database schema must match the fixture release")

    # Reserve the port in the launcher preflight so a leftover local service cannot
    # satisfy readiness before this process has had a chance to bind.
    import socket
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", int(port)))
    name = "buddy-old-bath-house-" + secrets.token_hex(6)
    subprocess.run(
        [*container_args, "--detach", "--name", name, image,
         "uvicorn", "benchmark_local_ui:app",
         "--host", "127.0.0.1", "--port", port],
        env=launch_env, stdout=subprocess.DEVNULL, check=True,
    )
    try:
        wait_ready(origin, name)
        browser = Path(__file__).with_name("browser.cjs")
        return subprocess.run(
            [os.environ["DMB_BENCHMARK_NODE"], str(browser), str(fixture_path),
             fixture_digest, str(output / "run.json")],
            env=dict(os.environ, DMB_BENCHMARK_BROWSER_TOKEN=token),
            check=False,
        ).returncode
    finally:
        with (output / "buddy.log").open("xb") as logs:
            subprocess.run(["docker", "logs", name], stdout=logs, stderr=logs, check=False)
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.fixture, args.fixture_sha256, args.output))


if __name__ == "__main__":
    main()

"""Launch a pinned Buddy release and measure Old Bath House on isolated state."""

import argparse
from hashlib import sha256
import json
import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from .isolation import APP_DSN, CORE_DSN, read_fixture, verify_target
from .provider_evidence import extract, verify_live_turn_traces

STATBLOCK_URL = "DUNGEONMIND_STATBLOCKS_BASE_URL"
STATBLOCK_KEY = "DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY"
TOKENIZER_ENV = "DUNGEONBUDDY_JEV_TOKENIZER_FILE"
TOKENIZER_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
STATE_DIRECTORIES = ("managed", "artifacts", "sessions")


def copy_runtime_state(source, destination):
    """Give Buddy a private writable copy, without following fixture links."""
    if source.is_symlink():
        raise ValueError("Benchmark fixture root must not be a symlink")
    source = source.resolve(strict=True)
    if source == Path("/") or destination.resolve().is_relative_to(source):
        raise ValueError("Choose a benchmark output outside the fixture source")
    for name in STATE_DIRECTORIES:
        directory = source / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"Expected a plain fixture directory: {name}")
        for path in directory.rglob("*"):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError("Benchmark fixture contains a symlink or special file")
    destination.mkdir(mode=0o700)
    for name in STATE_DIRECTORIES:
        shutil.copytree(source / name, destination / name)


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
    if fixture.get("live"):
        from .live_sources import live_manifest, verify_core_snapshot

        core_head = fixture["live"]["coreHead"]
        if fixture["live"] != live_manifest(core_head):
            raise ValueError("Live fixture differs from the pinned source and prompts")
        verify_core_snapshot(os.environ[CORE_DSN], core_head)
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
    root = output.resolve() / "runtime-state"
    env = {key: os.environ[key] for key in (APP_DSN, CORE_DSN, STATBLOCK_URL, STATBLOCK_KEY)}
    tokenizer = None
    if fixture.get("live"):
        required = ("OPENAI_API_KEY", "TYPESAFE_JEV_API_KEY", TOKENIZER_ENV)
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            raise ValueError("Missing live-provider configuration: " + ", ".join(missing))
        with Path(os.environ[TOKENIZER_ENV]).open("rb") as stream:
            tokenizer = stream.read(8 * 1024 * 1024 + 1)
        if sha256(tokenizer).hexdigest() != TOKENIZER_SHA256:
            raise ValueError("Live benchmark tokenizer checksum differs from Buddy's runtime pin")
        for key in ("OPENAI_API_KEY", "TYPESAFE_JEV_API_KEY", "DUNGEONBUDDY_FAL_KEY", "FAL_KEY"):
            if os.environ.get(key):
                env[key] = os.environ[key]
        # New public benchmark images require an explicitly configured
        # disposable CDN account. Never inherit the campaign's media account.
        for target, source in (
            ("CLOUDFLARE_ACCOUNT_ID", "DMB_BENCHMARK_CDN_ACCOUNT_ID"),
            ("CLOUDFLARE_IMAGES_API_TOKEN", "DMB_BENCHMARK_CDN_IMAGES_TOKEN"),
        ):
            if os.environ.get(source):
                env[target] = os.environ[source]
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
    copy_runtime_state(Path(fixture["runtime_state"]), root)
    uid = info["Config"]["User"].split(":", 1)[0]
    if not uid.isdecimal() or uid == "0":
        raise ValueError("Benchmark image must declare a numeric unprivileged runtime user")
    subprocess.run(["setfacl", "-R", "-m", f"u:{uid}:rwX", str(root)], check=True)
    container_args = [
        "docker", "run", "--network", "host",
        "--mount", f"type=bind,source={root},target=/benchmark",
        "--mount", f"type=bind,source={Path(__file__).with_name('local_ui.py').resolve()},target=/app/benchmark_local_ui.py,readonly",
    ]
    if tokenizer is not None:
        local_tokenizer = output.resolve() / "o200k_base.tiktoken"
        local_tokenizer.write_bytes(tokenizer)
        local_tokenizer.chmod(0o444)
        mounted_tokenizer = "/app/benchmark-tokenizer.tiktoken"
        container_args.extend(["--mount", f"type=bind,source={local_tokenizer},target={mounted_tokenizer},readonly"])
        env[TOKENIZER_ENV] = mounted_tokenizer
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
        log_path = output / "buddy.log"
        with log_path.open("xb") as logs:
            subprocess.run(["docker", "logs", name], stdout=logs, stderr=logs, check=False)
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, check=True)
        if fixture.get("live"):
            with log_path.open() as logs, (output / "provider-timings.json").open("x") as report:
                traces = extract(logs)
                json.dump(traces, report, indent=2, allow_nan=False)
            browser_result = output / "run.json"
            if browser_result.is_file():
                result = json.loads(browser_result.read_text())
                result["checks"]["live_turn_provider_trace"] = verify_live_turn_traces(result, traces)
                pending = output / "run.with-provider-proof.json"
                with pending.open("x") as report:
                    json.dump(result, report, indent=2, allow_nan=False)
                pending.replace(browser_result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.fixture, args.fixture_sha256, args.output))


if __name__ == "__main__":
    main()

"""Qualification against one clean production image and disposable owned services.

No operator DSN, browser profile, deployment command or shared resource is accepted.
The default includes the browser witness; --image-only is diagnostic, never qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
# Canonical DungeonMind compose pin, not a hand-written database substitute.
POSTGRES_IMAGE = "pgvector/pgvector:0.8.6-pg16@sha256:a36250871de0833b8757561c72f2477ef1ddd1101afa4e617fb552e0de514c6b"


class QualificationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QualificationFailure(message)


def request(url: str, *, cookie: bool = False, accept: str = "application/json") -> tuple[int, bytes, str]:
    headers = {"Accept": accept}
    if cookie:
        headers["Cookie"] = "dungeonmind_session=qualification-session"
    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.read(), response.headers.get("Content-Type", "")


class Probe:
    def __init__(self, output: Path):
        self.output = output.resolve()
        require(not self.output.exists(), "use a fresh task-owned evidence directory")
        self.output.mkdir(parents=True)
        self.sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        self.dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        self.prefix = f"dmb-qualification-{self.sha[:10]}-{secrets.token_hex(4)}"
        self.network = self.prefix + "-network"
        self.volume = self.prefix + "-state"
        self.postgres_volume = self.prefix + "-postgres-data"
        self.containers: list[str] = []
        self.network_created = self.volume_created = False
        self.postgres_volume_created = False
        self.report = {"owner": "Drakosfire (Buddy CI coordinator)", "source_sha": self.sha, "dirty_worktree": self.dirty, "qualified": False,
                       "resource_prefix": self.prefix, "checks": {}, "cleanup": {}}
        self.sequence = 0

    def run(self, args: list[str], *, stdin: str | None = None, check: bool = True, timeout: int = 1800) -> subprocess.CompletedProcess:
        self.sequence += 1
        try:
            result = subprocess.run(args, cwd=ROOT, input=stdin, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            (self.output / f"command-{self.sequence:03}.log").write_bytes((error.stdout or b"") + (error.stderr or b""))
            raise
        (self.output / f"command-{self.sequence:03}.log").write_text(result.stdout + result.stderr)
        if check and result.returncode:
            raise QualificationFailure(f"command {self.sequence} failed ({args[0]} {args[1]}), exit {result.returncode}; retained log")
        return result

    def docker(self, *args: str, **kwargs) -> subprocess.CompletedProcess:
        return self.run(["docker", *args], **kwargs)

    def start(self, suffix: str, *args: str) -> str:
        name = self.prefix + "-" + suffix
        self.containers.append(name)
        self.docker("run", "--detach", "--name", name, *args)
        return name

    def one_off(self, suffix: str, *args: str) -> None:
        # Named even with --rm: a killed Docker client must not orphan an
        # unidentifiable migration container. Cleanup owns this exact name.
        name = self.prefix + "-" + suffix
        self.containers.append(name)
        self.docker("run", "--rm", "--name", name, *args)

    def state(self, name: str) -> dict:
        return json.loads(self.docker("inspect", name).stdout)[0]["State"]

    def wait_live(self, name: str, base: str, timeout: float = 120) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.state(name)
            if not state["Running"]:
                raise QualificationFailure(f"startup_exit:{state['ExitCode']}")
            try:
                status, body, _ = request(base + "/health/live")
                if status == 200 and json.loads(body) == {"status": "live"}:
                    return
            except (OSError, ValueError):
                pass
            time.sleep(1)
        raise QualificationFailure("startup_health_timeout")

    def boot(self, *, image_only: bool) -> None:
        from scripts.qualification.bootstrap_core import prepare_checkout

        require(image_only or not self.dirty, "full qualification requires a clean committed source")
        docker_root = self.docker("info", "--format", "{{.DockerRootDir}}").stdout.strip()
        free = shutil.disk_usage(docker_root).free
        self.report["docker_storage"] = {"root": docker_root, "free_bytes_before": free}
        require(free >= 8 * 1024**3, "Docker storage has less than 8 GiB free; no build/resources allocated")

        self.docker("buildx", "build", "--no-cache", "--file", "Dockerfile.production", "--label",
                    f"org.opencontainers.image.revision={self.sha}", "--tag", self.prefix, "--load", "--progress", "plain", ".")
        image = json.loads(self.docker("image", "inspect", self.prefix).stdout)[0]
        self.image = image["Id"]
        require(image["Config"]["Labels"]["org.opencontainers.image.revision"] == self.sha, "image/source binding mismatch")
        self.report["image_id"] = self.image
        self.docker("network", "create", self.network)
        self.network_created = True
        self.docker("volume", "create", self.volume)
        self.volume_created = True
        self.docker("volume", "create", self.postgres_volume)
        self.postgres_volume_created = True
        self.report["postgres_data_volume"] = self.postgres_volume
        password = secrets.token_hex(20)
        database = self.start("postgres", "--network", self.network, "--network-alias", "qualification-db",
                              "--volume", f"{self.postgres_volume}:/var/lib/postgresql/data",
                              "--env", "POSTGRES_USER=qualification_admin", "--env", f"POSTGRES_PASSWORD={password}", POSTGRES_IMAGE)
        mounts = json.loads(self.docker("container", "inspect", database).stdout)[0]["Mounts"]
        require(any(m.get("Name") == self.postgres_volume and m["Destination"] == "/var/lib/postgresql/data" for m in mounts),
                "PostgreSQL data must use the explicitly owned volume")
        for _ in range(60):
            ready = self.docker("exec", database, "pg_isready", "-U", "qualification_admin", check=False)
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise QualificationFailure("disposable_postgres_unavailable")
        self.docker("exec", "-i", database, "psql", "-U", "qualification_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1", stdin=(
            f"CREATE ROLE qualification_app LOGIN PASSWORD '{password}';\n"
            f"CREATE ROLE qualification_core LOGIN PASSWORD '{password}';\n"
            "CREATE DATABASE qualification_app OWNER qualification_app;\n"
            "CREATE DATABASE qualification_core OWNER qualification_core;\n"))
        self.docker("exec", database, "psql", "-U", "qualification_admin", "-d", "qualification_core", "-v", "ON_ERROR_STOP=1", "-c", "CREATE EXTENSION vector")
        app_dsn = f"postgresql://qualification_app:{password}@qualification-db:5432/qualification_app"
        core_dsn = f"postgresql://qualification_core:{password}@qualification-db:5432/qualification_core"
        core_checkout = self.output / "canonical-core"
        self.report["core_source_sha"] = prepare_checkout(core_checkout)
        self.one_off("migrate-core", "--network", self.network, "--env", f"DUNGEONMIND_DATABASE_URL={core_dsn}",
                    "--volume", f"{core_checkout}:/qualification-core:ro", "--workdir", "/qualification-core", self.image,
                    "python", "-m", "alembic", "-c", "/qualification-core/alembic.ini", "upgrade", "head")
        self.one_off("migrate-app", "--network", self.network, "--env", f"DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL={app_dsn}",
                    self.image, "python", "-c", "from application_state.cli import upgrade_to_head; upgrade_to_head()")
        self.one_off("prepare-state", "--user", "0", "--volume", f"{self.volume}:/qualification-state", self.image, "python", "-c",
                    "import os; [(os.makedirs('/qualification-state/'+p,exist_ok=True), os.chown('/qualification-state/'+p,10001,10001)) for p in ('worlds','artifacts','sessions','graph')]")
        cert, key = self.output / "dms-cert.pem", self.output / "dms-key.pem"
        self.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-keyout", str(key),
                  "-out", str(cert), "-subj", "/CN=qualification-dms", "-addext", "subjectAltName=DNS:qualification-dms"])
        self.start("dms", "--network", self.network, "--network-alias", "qualification-dms", "--user", "0",
                   "--volume", f"{self.output}:/qualification-fixture:ro", self.image, "python", "scripts/qualification/dms_stub.py",
                   "--cert", "/qualification-fixture/dms-cert.pem", "--key", "/qualification-fixture/dms-key.pem")
        environment = {
            "DMB_DEPLOYMENT_ENVIRONMENT": "production", "DMB_AUTH_MODE": "hosted_dms",
            "DUNGEONMIND_SERVER_API_ORIGIN": "https://qualification-dms",
            "AUTH_TRUSTED_FRONTEND_ORIGINS": "https://buddy.dungeonmind.net",
            "DMB_HOSTED_WORLD_ACCESS_JSON": '{"qualification-world":["qualification-user"]}',
            "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL": app_dsn,
            "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": core_dsn,
            "DMB_MANAGED_WORLD_DATA_ROOT": "/qualification-state/worlds",
            "DMB_ARTIFACT_DATA_ROOT": "/qualification-state/artifacts",
            "DUNGEONMIND_LIVE_SESSION_DIR": "/qualification-state/sessions",
            "DUNGEONMIND_WORLD_GRAPH_ROOT": "/qualification-state/graph",
            "SSL_CERT_FILE": "/qualification-ca.pem", "NO_PROXY": "qualification-dms,qualification-db,localhost,127.0.0.1",
        }
        common = ["--network", self.network, "--publish", "127.0.0.1::8000", "--volume", f"{self.volume}:/qualification-state",
                  "--volume", f"{cert}:/qualification-ca.pem:ro"]
        env_args = [part for pair in environment.items() for part in ("--env", "=".join(pair))]
        good = self.start("api", *common, *env_args, self.image)
        base = self.base_url(good)
        self.wait_live(good, base)
        status, body, _ = request(base + "/health/ready")
        require(status == 200 and json.loads(body) == {"status": "ready"}, "production_readiness_failed")
        require(request(base + "/api/auth/current-user")[0] == 401, "anonymous_api_not_denied")
        status, body, _ = request(base + "/api/auth/current-user", cookie=True)
        require(status == 200 and json.loads(body).get("sub") == "qualification-user", "authenticated_api_failed")
        status, html, content_type = request(base + "/", accept="text/html")
        require(status == 200 and "text/html" in content_type, "static_index_missing")
        assets = re.findall(rb'(?:src|href)="(/assets/[^"?]+\.(?:js|css))"', html)
        require(bool(assets), "static_index_has_no_assets")
        for raw in assets:
            asset = raw.decode()
            status, payload, kind = request(base + asset, accept="*/*")
            require(status == 200 and "text/html" not in kind, "asset_replaced_by_spa_fallback")
            expected = self.docker("exec", good, "python", "-c",
                                   "import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())",
                                   "/app/apps/live-control-ui/dist" + asset).stdout.strip()
            require(hashlib.sha256(payload).hexdigest() == expected, "static_asset_does_not_match_image")
        self.report["checks"].update({"production_startup": True, "readiness": True, "api_auth_and_denial": True, "static_asset_bytes": True})
        bad = self.start("bad-startup", *common, *env_args, "--env", "DMB_AUTH_MODE=deliberately-invalid", self.image)
        bad_base = self.base_url(bad)
        try:
            self.wait_live(bad, bad_base, timeout=45)
        except QualificationFailure as failure:
            require(str(failure).startswith("startup_exit:"), "startup fault was not detected at process boundary")
            logs = self.docker("logs", bad)
            require("hosted_auth_configuration_invalid" in logs.stdout + logs.stderr, "startup fault failed for an unrelated reason")
        else:
            raise QualificationFailure("deliberate_startup_fault_escaped")
        self.report["checks"]["startup_fault_detected"] = True
        self.report["base_url"] = base
        # Image-only diagnostics cannot produce a qualified result.
        if not image_only:
            env = {**os.environ, "QUALIFICATION_BASE_URL": base, "QUALIFICATION_OUTPUT": str(self.output / "browser")}
            browser = subprocess.run(["npx", "--no-install", "playwright", "test", "--config", "tests/qualification/playwright.config.ts"],
                                     cwd=ROOT / "apps/live-control-ui", env=env, capture_output=True, text=True, timeout=300)
            (self.output / "browser.log").write_text(browser.stdout + browser.stderr)
            require(browser.returncode == 0, "browser_graph_or_persistence_qualification_failed; see browser.log and #2276 dependency")
            self.report["checks"]["browser_graph_and_persistence_fault"] = True
            self.report["qualified"] = True
        else:
            self.report["qualification_dependency"] = "browser graph/persistence witness not run; image-only is diagnostic"

    def base_url(self, container: str) -> str:
        port = self.docker("port", container, "8000/tcp").stdout.strip()
        require(bool(re.fullmatch(r"127\.0\.0\.1:\d+", port)), "container must bind only a random loopback port")
        return "http://" + port

    def cleanup(self) -> None:
        for name in reversed(self.containers):
            exists = self.docker("container", "inspect", name, check=False)
            if exists.returncode and any(message in exists.stderr.lower() for message in ("no such container", "no such object")):
                self.report["cleanup"][name] = True
                continue
            logs = self.docker("logs", name, check=False)
            (self.output / (name + ".log")).write_text(logs.stdout + logs.stderr)
            removed = self.docker("rm", "--force", "--volumes", name, check=False)
            self.report["cleanup"][name] = removed.returncode == 0
        for kind, name, created in (("volume", self.postgres_volume, self.postgres_volume_created),
                                    ("volume", self.volume, self.volume_created),
                                    ("network", self.network, self.network_created)):
            if not created:
                continue
            result = self.docker(kind, "rm", name, check=False)
            self.report["cleanup"][name] = result.returncode == 0
        if hasattr(self, "image"):
            result = self.docker("image", "rm", self.prefix, check=False)
            self.report["cleanup"][self.prefix] = result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image-only", action="store_true")
    args = parser.parse_args()
    probe = Probe(args.output)
    started = time.monotonic()
    status = 1
    try:
        probe.boot(image_only=args.image_only)
        status = 0
    except Exception as error:
        probe.report["failure"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            probe.cleanup()
        except (subprocess.SubprocessError, OSError) as error:
            probe.report["cleanup_error"] = str(error)
            status = 1
        if any(value is False for value in probe.report["cleanup"].values()):
            probe.report["cleanup_error"] = "owned resource teardown failed; coordinator must inspect retained identities"
            status = 1
        if status:
            probe.report["qualified"] = False
        probe.report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (probe.output / "result.json").write_text(json.dumps(probe.report, indent=2) + "\n")
        print(json.dumps(probe.report), flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())

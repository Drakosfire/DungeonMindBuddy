"""Fail closed before starting an Old Bath House benchmark runtime."""

from pathlib import Path
from urllib.parse import urlsplit

APP_DSN = "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
CORE_DSN = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"
BASELINE_RELEASE = {
    "source": "2d4361fb05e0b6bbb4e652535b77acd7b30ad1fb",
    "image": "sha256:a469deffc039f40de0459cd57f35c2412a50d2e3e6ba57bdb7de15202b57f418",
    "app_schema": "20261123_0204",
}


def _database_identity(dsn, expected, *, writable):
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    params = conninfo_to_dict(dsn)
    host, port, name = params.get("host"), params.get("port"), params.get("dbname")
    if host != "127.0.0.1" or not port or params.get("hostaddr") or params.get("service"):
        raise ValueError("Benchmark requires an explicit loopback PostgreSQL endpoint")
    if (host, int(port), name) != (expected["host"], expected["port"], expected["database"]):
        raise ValueError("Benchmark database endpoint differs from the fixture")
    if writable and not name.startswith("dungeonbuddy_app_state_test_"):
        raise ValueError("Benchmark writes require a disposable Buddy application database")
    with psycopg.connect(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        actual = conn.execute("""
            SELECT current_database(),
                   (SELECT oid::text FROM pg_database WHERE datname = current_database()),
                   system_identifier::text
            FROM pg_control_system()
        """).fetchone()
        if actual != (name, expected["oid"], expected["system_identifier"]):
            raise ValueError("Benchmark database identity differs from the fixture")
    return actual


def verify_target(manifest, environment):
    """Validate the pins used by the process that will launch Buddy."""
    from evals.buddy_benchmark.cohort_capture import require_read_only_core

    origin = urlsplit(manifest["origin"])
    if (
        origin.scheme != "http" or origin.hostname != "127.0.0.1" or not origin.port
        or origin.username or origin.password or origin.path or origin.query or origin.fragment
    ):
        raise ValueError("Benchmark runtime must bind to an explicit loopback origin")
    isolation = manifest["isolation"]
    app = _database_identity(environment[APP_DSN], isolation["app"], writable=True)
    core = _database_identity(environment[CORE_DSN], isolation["core"], writable=False)
    if app == core:
        raise ValueError("Application writes and corpus reads require distinct authorities")
    require_read_only_core(environment[CORE_DSN])
    return {"app": app, "core": core}


def read_fixture(path, digest):
    """Verify exact fixture bytes before parsing configuration or launching tools."""
    from hashlib import sha256
    import json

    data = Path(path).read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Old Bath House fixture digest differs")
    manifest = json.loads(data)
    if manifest.get("schema") != "dmb_old_bath_house_benchmark_v1":
        raise ValueError("Unsupported Old Bath House benchmark fixture")
    return manifest


def source_fixture_digest(pins, exported_hashes):
    """Identify the content independently of the release and disposable runtime."""
    from hashlib import sha256
    import json

    source = {key: value for key, value in pins.items() if key != "runtime"}
    payload = {"source": source, "exports": exported_hashes, "protocol": "old_bath_house_v2"}
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

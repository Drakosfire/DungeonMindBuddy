"""Parallel ordinary retrieval with a single pinned, read-only Core snapshot."""

from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
import json
import multiprocessing
import os
from pathlib import Path
from urllib.parse import quote, urlparse

import psycopg
from psycopg.rows import dict_row

from .artifacts import immutable_save, row_inventory

APP_DSN = "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
CORE_DSN = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"


def require_read_only_core(dsn):
    """Require a read-only session and a login without durable write privileges."""
    with psycopg.connect(dsn) as conn:
        read_only, trusted_login = conn.execute("""
            SELECT current_setting('transaction_read_only') = 'on',
                   NOT (r.rolsuper OR r.rolcreaterole OR r.rolcreatedb
                       OR r.rolreplication OR r.rolbypassrls)
                   AND current_user = session_user
                   AND NOT EXISTS (
                       SELECT FROM pg_auth_members WHERE member = r.oid
                   )
                   AND NOT has_database_privilege(current_database(), 'CREATE')
                   AND NOT EXISTS (
                       SELECT FROM pg_database d WHERE d.datname = current_database() AND d.datdba = r.oid
                   )
                   AND NOT EXISTS (
                       SELECT FROM pg_namespace n
                       WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
                       AND (n.nspowner = r.oid OR has_schema_privilege(n.oid, 'CREATE'))
                   )
                   AND NOT EXISTS (
                       SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                       WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
                       AND (c.relowner = r.oid OR CASE
                           WHEN c.relkind = 'S' THEN has_sequence_privilege(c.oid, 'USAGE,UPDATE')
                           WHEN c.relkind IN ('r','p','v','m','f') THEN
                               has_table_privilege(c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')
                           ELSE false END)
                   )
                   AND NOT EXISTS (
                       SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                       WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
                       AND (p.proowner = r.oid OR (p.prosecdef AND has_function_privilege(p.oid, 'EXECUTE')))
                   )
            FROM pg_roles r WHERE r.rolname = current_user
        """).fetchone()
        if not (read_only and trusted_login):
            raise ValueError("Cohort Core requires a read-only session and a dedicated non-writing login")


@contextmanager
def readonly(dsn):
    with psycopg.connect(dsn, options="-c default_transaction_read_only=on", row_factory=dict_row) as conn:
        yield conn


def _endpoint(dsn, expected):
    url = urlparse(dsn)
    if (url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or (url.hostname, url.port, url.path[1:]) !=
            (expected["host"], expected["port"], expected["database"])):
        raise ValueError("Cohort database differs from the pinned isolated endpoint")
    with readonly(dsn) as conn:
        actual = conn.execute("""
            SELECT current_database() AS name, oid::text AS oid,
                   (SELECT system_identifier::text FROM pg_control_system()) AS system
            FROM pg_database WHERE datname = current_database()
        """).fetchone()
    if tuple(actual.values()) != (expected["database"], expected["oid"], expected["system_identifier"]):
        raise ValueError("Cohort database identity differs from its pin")


def _capture_member(manifest, output, app_dsn):
    from .workflow import capture

    scratch = output.parent / "scratch" / output.name
    scratch.mkdir(parents=True, exist_ok=False)
    for key in ("DMB_MANAGED_WORLD_DATA_ROOT", "DUNGEONMIND_LIVE_SESSION_DIR", "DUNGEONMIND_WORLD_GRAPH_ROOT"):
        directory = scratch / key
        directory.mkdir()
        os.environ[key] = str(directory)
    os.environ[APP_DSN] = app_dsn
    capture(manifest, output, context_only=True, cohort_member=True)


def capture_cohort(manifest_path, output, *, workers):
    """Capture independent member manifests, then prove Core parity once."""
    from .workflow import load_manifest, read_pin

    if not 1 <= workers <= 8:
        raise ValueError("Cohort workers must be between 1 and 8")
    path = Path(manifest_path).resolve()
    config = json.loads(path.read_text())
    if (config.get("schema") != "dmb_context_capture_cohort_v1"
            or not isinstance(config.get("members"), list) or not config["members"]):
        raise ValueError("Cohort requires pinned ordinary capture member manifests")
    core_dsn = os.environ[CORE_DSN]
    app_url = urlparse(os.environ[APP_DSN])
    native = None
    expected_inventory = None
    cases = set()
    app_identities = set()
    jobs = []
    output = Path(output).resolve()
    for entry in config["members"]:
        read_pin(entry, path.parent)
        member_path = (path.parent / entry["path"]).resolve()
        member, base = load_manifest(member_path)
        app = member["isolation"]["app"]
        current_native = member["isolation"]["native"]
        locator = {k: v for k, v in current_native.items() if k != "inventory"}
        inventory = read_pin(current_native["inventory"], base)
        if native is None:
            native, expected_inventory = locator, inventory
        elif (native, expected_inventory) != (locator, inventory):
            raise ValueError("Cohort members must share the exact pinned Core inventory")
        identity = (app["system_identifier"], app["oid"])
        if identity in app_identities or identity == (native["system_identifier"], native["oid"]):
            raise ValueError("Cohort requires separate App databases for each member")
        app_identities.add(identity)
        ids = {case["id"] for case in member["cases"]}
        if cases & ids:
            raise ValueError("Repeated case identity in cohort")
        cases |= ids
        app_dsn = app_url._replace(path="/" + quote(app["database"], safe="")).geturl()
        _endpoint(app_dsn, app)
        jobs.append((member_path, output / "members" / sorted(ids)[0], app_dsn))

    _endpoint(core_dsn, native)
    require_read_only_core(core_dsn)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    before = row_inventory(core_dsn, readonly=readonly)
    if before != json.loads(expected_inventory):
        raise ValueError("Native corpus differs from pinned inventory")
    immutable_save(output, "native-before", before)
    try:
        with ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=1,
                                 mp_context=multiprocessing.get_context("spawn")) as executor:
            futures = [(job[1].name, executor.submit(_capture_member, *job)) for job in jobs]
            outcomes = {}
            for member, future in futures:
                error = future.exception()
                outcomes[member] = {"status": "failed", "error_type": type(error).__name__} if error else {"status": "completed"}
            immutable_save(output, "members", outcomes)
    finally:
        _endpoint(core_dsn, native)
        require_read_only_core(core_dsn)
        after = row_inventory(core_dsn, readonly=readonly)
        immutable_save(output, "native-after", after)
        if before != after:
            raise ValueError("Native authority changed during cohort capture")
    if any(row["status"] != "completed" for row in outcomes.values()):
        raise RuntimeError("One or more cohort members failed; inspect retained outcomes")

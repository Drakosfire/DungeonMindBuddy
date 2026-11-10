"""Real loopback transport tests; fake service does not prove native semantics."""

from __future__ import annotations

from contextlib import closing
import http.client
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import signal
from unittest import mock
import threading
import unittest

from apps.live_control_server.native_graph_demo.server import (
    DemoHTTPServer,
    MAX_BODY_BYTES,
)


class FakeService:
    def __init__(self):
        self.calls = []

    def graph(self):
        self.calls.append("graph")
        return {"world_id": "isolated-native-world", "revision_id": "native-r1"}

    def prepare(self, payload):
        self.calls.append(("prepare", payload))
        return {"status": "prepared", "operation_id": payload.get("operation_id")}

    def confirm(self, operation_id):
        self.calls.append(("confirm", operation_id))
        return {"status": "committed", "graph": self.graph()}

    def operation(self, operation_id):
        return {"status": "unknown", "operation_id": operation_id}


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="native-demo-http-")
        self.assets = Path(self.directory.name)
        (self.assets / "native-demo.html").write_text(
            '<html><head><meta name="native-demo-capability" content=""></head><body>Native demo</body></html>'
        )
        (self.assets / "assets").mkdir()
        (self.assets / "assets" / "main.js").write_text("export const real=true;")
        self.service = FakeService()
        self.server = DemoHTTPServer(0, self.service, self.assets)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.directory.cleanup()

    def request(
        self,
        method,
        path,
        payload=None,
        *,
        capability=True,
        origin=True,
        headers=None,
        raw=None,
    ):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3
        )
        request_headers = {"Host": self.server.authority}
        if capability:
            request_headers["X-Demo-Capability"] = self.server.capability
        if origin:
            request_headers["Origin"] = self.server.origin
        if raw is None and payload is not None:
            raw = json.dumps(payload)
        if raw is not None:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        connection.request(method, path, body=raw, headers=request_headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_html_injects_one_launch_capability_and_security_headers(self):
        status, headers, body = self.request("GET", "/", capability=False, origin=False)
        self.assertEqual(status, 200)
        self.assertEqual(body.count(b'name="native-demo-capability"'), 1)
        self.assertIn(self.server.capability.encode(), body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.service.calls, [])

    def test_native_read_requires_capability(self):
        self.assertEqual(self.request("GET", "/api/graph", capability=False)[0], 403)
        self.assertEqual(self.service.calls, [])
        self.assertEqual(self.request("GET", "/api/graph")[0], 200)
        self.assertEqual(self.service.calls, ["graph"])

    def test_dns_rebinding_host_and_cross_site_are_rejected(self):
        for header in (
            {"Host": "evil.example"},
            {"Origin": "http://evil.example"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            self.assertEqual(self.request("GET", "/", headers=header)[0], 403)
            self.assertEqual(
                self.request(
                    "POST", "/api/confirm", {"operation_id": "x"}, headers=header
                )[0],
                403,
            )
        self.assertEqual(self.service.calls, [])

    def test_user_can_follow_a_top_level_link_but_cross_site_api_stays_denied(self):
        navigation = {
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }
        self.assertEqual(
            self.request(
                "GET", "/", origin=False, capability=False, headers=navigation
            )[0],
            200,
        )
        self.assertEqual(
            self.request("GET", "/api/graph", origin=False, headers=navigation)[0], 403
        )
        self.assertEqual(
            self.request(
                "GET",
                "/",
                origin=False,
                capability=False,
                headers={**navigation, "Sec-Fetch-Dest": "iframe"},
            )[0],
            403,
        )
        self.assertEqual(self.service.calls, [])

    def test_missing_origin_and_invalid_capability_cannot_mutate(self):
        self.assertEqual(
            self.request("POST", "/api/confirm", {"operation_id": "x"}, origin=False)[
                0
            ],
            403,
        )
        self.assertEqual(
            self.request(
                "POST", "/api/confirm", {"operation_id": "x"}, capability=False
            )[0],
            403,
        )
        self.assertEqual(
            self.request(
                "POST",
                "/api/confirm",
                {"operation_id": "x"},
                headers={"X-Demo-Capability": "invalid"},
            )[0],
            403,
        )
        self.assertEqual(self.service.calls, [])

    def test_valid_prepare_confirm_and_recovery_reach_fixed_service(self):
        payload = {"operation_id": "op", "kind": "create_object", "name": "Mara"}
        self.assertEqual(self.request("POST", "/api/prepare", payload)[0], 200)
        self.assertEqual(
            self.request("POST", "/api/confirm", {"operation_id": "op"})[0], 200
        )
        self.assertEqual(self.request("GET", "/api/operations/op")[0], 200)
        self.assertEqual(
            self.service.calls[:2], [("prepare", payload), ("confirm", "op")]
        )

    def test_confirm_rejects_world_or_other_injected_fields(self):
        self.assertEqual(
            self.request(
                "POST", "/api/confirm", {"operation_id": "op", "world_id": "production"}
            )[0],
            400,
        )
        self.assertEqual(self.service.calls, [])

    def test_bounded_unique_json_no_transfer_encoding_or_query(self):
        cases = [
            ("/api/confirm", '{"operation_id":"one","operation_id":"two"}', {}, 400),
            ("/api/confirm", "[]", {}, 400),
            ("/api/confirm", "x" * (MAX_BODY_BYTES + 1), {}, 413),
            ("/api/confirm", '{"operation_id":NaN}', {}, 400),
            ("/api/confirm", "{}", {"Transfer-Encoding": "chunked"}, 400),
            ("/api/confirm", "{}", {"Content-Type": "text/plain"}, 415),
            ("/api/confirm?world=production", "{}", {}, 404),
        ]
        for path, raw, headers, expected in cases:
            with self.subTest(raw=raw[:60]):
                self.assertEqual(
                    self.request("POST", path, raw=raw, headers=headers)[0], expected
                )
        self.assertEqual(self.service.calls, [])

    def test_assets_are_bounded_to_build_not_arbitrary_paths(self):
        self.assertEqual(self.request("GET", "/assets/main.js")[0], 200)
        for path in (
            "/assets/../../native-demo-owner.json",
            "/assets/%2e%2e/secret",
            "/api/graph?token=x",
            "/etc/passwd",
        ):
            self.assertNotEqual(self.request("GET", path)[0], 200)

    def test_restart_rotates_capability(self):
        second = DemoHTTPServer(0, self.service, self.assets)
        try:
            self.assertNotEqual(second.capability, self.server.capability)
        finally:
            second.server_close()


class NativeTransportTest(unittest.TestCase):
    """HTTP -> WorldKeeper -> actual native in-memory Core proof, not PG restart."""

    def test_real_http_create_confirm_and_native_readback(self):
        import uuid
        from dungeonmind.infrastructure.memory.vnext_sources import (
            InMemoryNativeSourceEvidenceRepository,
        )
        from apps.live_control_server.native_graph_demo.service import (
            NativeGraphDemoService,
        )

        with tempfile.TemporaryDirectory(prefix="native-http-core-") as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            (assets / "native-demo.html").write_text(
                "<html><head></head><body>Native fixture</body></html>"
            )
            repository = InMemoryNativeSourceEvidenceRepository()
            service = NativeGraphDemoService(
                repository, root / "commands", storage_label="memory-test-only"
            )
            with closing(service), DemoHTTPServer(0, service, assets) as server:
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()

                def request(method, path, payload=None):
                    connection = http.client.HTTPConnection(
                        "127.0.0.1", server.server_port, timeout=10
                    )
                    headers = {
                        "Host": server.authority,
                        "Origin": server.origin,
                        "X-Demo-Capability": server.capability,
                        "Content-Type": "application/json",
                    }
                    connection.request(
                        method,
                        path,
                        body=None if payload is None else json.dumps(payload),
                        headers=headers,
                    )
                    response = connection.getresponse()
                    status, result = response.status, json.loads(response.read())
                    connection.close()
                    self.assertEqual(status, 200, result)
                    return result

                try:
                    before = request("GET", "/api/graph")
                    self.assertEqual(before["storage"], "memory-test-only")
                    operation_id = str(uuid.uuid4())
                    prepared = request(
                        "POST",
                        "/api/prepare",
                        {
                            "operation_id": operation_id,
                            "expected_revision_id": before["revision_id"],
                            "kind": "create_object",
                            "name": "HTTP native witness",
                            "object_kind": "person",
                        },
                    )
                    self.assertEqual(prepared["status"], "prepared")
                    committed = request(
                        "POST", "/api/confirm", {"operation_id": operation_id}
                    )
                    self.assertEqual(committed["status"], "committed")
                    after = request("GET", "/api/graph")
                    self.assertEqual(after, committed["graph"])
                    self.assertEqual(len(after["nodes"]), len(before["nodes"]) + 1)
                    self.assertEqual(after["world_id"], before["world_id"])
                    head = repository.get_head(after["world_id"])
                    self.assertEqual(head.head_revision_id, after["revision_id"])
                    self.assertEqual(
                        repository.get_revision(
                            after["world_id"], after["revision_id"]
                        ).graph_payload_sha256,
                        after["graph_sha256"],
                    )
                    replay = request(
                        "POST", "/api/confirm", {"operation_id": operation_id}
                    )
                    self.assertEqual(replay["graph"], after)
                    self.assertEqual(
                        request("GET", f"/api/operations/{operation_id}")["status"],
                        "committed",
                    )
                finally:
                    server.shutdown()
                    worker.join(timeout=3)


class LauncherIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "scripts" / "native_graph_demo.py"
        spec = importlib.util.spec_from_file_location(
            "native_demo_launcher_tests", path
        )
        cls.launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.launcher)

    def test_ambient_libpq_settings_are_rejected_before_any_connection(self):
        for name in ("PGHOSTADDR", "PGSERVICE", "PGOPTIONS", "PGPASSFILE"):
            with (
                self.subTest(name=name),
                mock.patch.dict(os.environ, {name: "must-not-be-read"}, clear=True),
                mock.patch("psycopg.connect") as connect,
            ):
                with self.assertRaises(self.launcher.LaunchBlocked):
                    next(
                        self.launcher.isolated_database(
                            Path("/unused"), {}, Path("/unused")
                        )
                    )
                connect.assert_not_called()

    def test_missing_postgres_does_not_fallback_to_docker_or_environment(self):
        with tempfile.TemporaryDirectory(prefix="native-demo-tools-") as temporary:
            with self.assertRaises(self.launcher.LaunchBlocked):
                self.launcher.postgres_tools(Path(temporary))

    def test_ambient_production_and_provider_settings_are_not_inherited(self):
        environment = self.launcher.clean_env(Path("/owned/task"))
        self.assertEqual(
            set(environment),
            {"PATH", "HOME", "LANG", "TMPDIR", "PYTHONDONTWRITEBYTECODE"},
        )
        self.assertFalse(
            any(name.startswith("PG") or "DATABASE" in name for name in environment)
        )

    def test_only_empty_owned_directory_can_initialize(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            parent = Path(temporary)
            dirty = parent / "dirty"
            dirty.mkdir(mode=0o700)
            (dirty / "existing").write_text("user data")
            with self.assertRaises(self.launcher.LaunchBlocked):
                self.launcher.owned_state(dirty)
            safe = parent / "s"
            if len(os.fsencode(str(safe / "s" / ".s.PGSQL.5432"))) >= 104:
                # A long task-owned TMPDIR is itself a refusal, not a fallback.
                with self.assertRaises(self.launcher.LaunchBlocked):
                    self.launcher.owned_state(safe)
            else:
                self.assertEqual(self.launcher.owned_state(safe), safe.resolve())
                self.assertEqual(self.launcher.owned_state(safe), safe.resolve())

    def make_migration_fixture(self, root):
        root.mkdir()
        (root / "migrations" / "versions").mkdir(parents=True)
        (root / "alembic.ini").write_text("[alembic]\nscript_location = migrations\n")
        (root / "migrations" / "env.py").write_text("# pinned migration environment\n")
        (root / "migrations" / "versions" / "0001.py").write_text(
            "# pinned migration\n"
        )
        (root / ".gitignore").write_text("migrations/versions/ignored.py\n")
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(root),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        subprocess.run(["git", "init", "-q"], cwd=root, env=environment, check=True)
        subprocess.run(["git", "add", "."], cwd=root, env=environment, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Native demo test",
                "-c",
                "user.email=native-demo@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qm",
                "test fixture",
            ],
            cwd=root,
            env=environment,
            check=True,
        )
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, env=environment, text=True
        ).strip()

    def test_migration_pin_checks_ignored_and_modified_file_bytes(self):
        with tempfile.TemporaryDirectory(prefix="migration-pin-") as temporary:
            root = Path(temporary) / "source"
            pin = self.make_migration_fixture(root)
            with mock.patch.object(self.launcher, "CORE_PIN", pin):
                self.assertEqual(self.launcher.verified_source(root), root.resolve())
                ignored = root / "migrations" / "versions" / "ignored.py"
                ignored.write_text("# not in the pinned source\n")
                with self.assertRaises(self.launcher.LaunchBlocked):
                    self.launcher.verified_source(root)
                ignored.unlink()
                subprocess.run(
                    ["git", "update-index", "--assume-unchanged", "migrations/env.py"],
                    cwd=root,
                    check=True,
                )
                (root / "migrations" / "env.py").write_text(
                    "# altered despite index flag\n"
                )
                with self.assertRaises(self.launcher.LaunchBlocked):
                    self.launcher.verified_source(root)

    def test_migration_pin_does_not_inherit_git_repository_override(self):
        with tempfile.TemporaryDirectory(prefix="migration-env-") as temporary:
            root = Path(temporary) / "source"
            pin = self.make_migration_fixture(root)
            with (
                mock.patch.object(self.launcher, "CORE_PIN", pin),
                mock.patch.dict(
                    os.environ,
                    {
                        "GIT_DIR": "/nonexistent/untrusted",
                        "GIT_WORK_TREE": "/nonexistent/untrusted",
                    },
                ),
            ):
                self.assertEqual(self.launcher.verified_source(root), root.resolve())

    def test_interrupted_start_inspects_and_stops_only_owned_postmaster(self):
        with tempfile.TemporaryDirectory(prefix="pg-start-test-") as temporary:
            root = Path(temporary)
            (root / "pgdata").mkdir()
            results = [
                subprocess.CompletedProcess([], 3),
                KeyboardInterrupt(),
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0),
            ]
            with mock.patch.object(
                self.launcher.subprocess, "run", side_effect=results
            ) as run:
                generator = self.launcher.isolated_database(
                    root, {"initdb": "initdb", "pg_ctl": "pg_ctl"}, root
                )
                with self.assertRaises(KeyboardInterrupt):
                    next(generator)
                self.assertEqual(run.call_count, 4)
                self.assertEqual(run.call_args_list[-1].args[0][-1], "stop")
                self.assertIn(str(root / "pgdata"), run.call_args_list[-1].args[0])

    def test_existing_postmaster_is_never_adopted_or_stopped(self):
        with tempfile.TemporaryDirectory(prefix="pg-existing-test-") as temporary:
            root = Path(temporary)
            (root / "pgdata").mkdir()
            with mock.patch.object(
                self.launcher.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0),
            ) as run:
                generator = self.launcher.isolated_database(
                    root, {"initdb": "initdb", "pg_ctl": "pg_ctl"}, root
                )
                with self.assertRaises(self.launcher.LaunchBlocked):
                    next(generator)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0][-1], "status")

    def test_unverifiable_postmaster_state_refuses_start_without_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="pg-uncertain-test-") as temporary:
            root = Path(temporary)
            (root / "pgdata").mkdir()
            with mock.patch.object(
                self.launcher.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 4),
            ) as run:
                generator = self.launcher.isolated_database(
                    root, {"initdb": "initdb", "pg_ctl": "pg_ctl"}, root
                )
                with self.assertRaises(self.launcher.LaunchBlocked):
                    next(generator)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0][-1], "status")

    def test_sigterm_handler_precedes_database_setup_and_is_restored(self):
        with tempfile.TemporaryDirectory(prefix="signal-test-") as temporary:
            root = Path(temporary)
            (root / "native-demo.html").write_text("<head></head>")
            old = signal.getsignal(signal.SIGTERM)
            observed = []

            def interrupted_setup(*args):
                handler = signal.getsignal(signal.SIGTERM)
                observed.append(handler != old)
                handler(signal.SIGTERM, None)
                yield "unreachable"

            with (
                mock.patch.object(self.launcher, "postgres_tools", return_value={}),
                mock.patch.object(self.launcher, "verified_source", return_value=root),
                mock.patch.object(self.launcher, "verified_dependencies"),
                mock.patch.object(self.launcher, "owned_state", return_value=root),
                mock.patch.object(
                    self.launcher, "isolated_database", interrupted_setup
                ),
            ):
                result = self.launcher.main(
                    [
                        "--state-dir",
                        str(root),
                        "--dungeonmind-source",
                        str(root),
                        "--assets",
                        str(root),
                        "--port",
                        "0",
                    ]
                )
            self.assertEqual(result, 130)
            self.assertEqual(observed, [True])
            self.assertEqual(signal.getsignal(signal.SIGTERM), old)


if __name__ == "__main__":
    unittest.main()

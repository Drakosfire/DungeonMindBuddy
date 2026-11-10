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

    def docker_image_metadata(self):
        return {
            "id": self.launcher.PGVECTOR_IMAGE_ID,
            "env": [
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/lib/postgresql/16/bin",
                "GOSU_VERSION=1.19",
                "LANG=en_US.utf8",
                "PG_MAJOR=16",
                "PG_VERSION=16.15-1.pgdg12+2",
                f"PGDATA={self.launcher.PGVECTOR_IMAGE_PGDATA}",
            ],
        }

    def docker_image_inspect(self):
        launcher = self.launcher
        return {
            "Id": launcher.PGVECTOR_IMAGE_ID,
            "RepoDigests": [launcher.PGVECTOR_REPO_DIGEST],
            "RepoTags": [launcher.PGVECTOR_IMAGE_TAG],
            "Config": {
                "Entrypoint": ["docker-entrypoint.sh"],
                "Cmd": ["postgres"],
                "User": "",
                "Env": self.docker_image_metadata()["env"],
                "Volumes": {launcher.PGVECTOR_IMAGE_PGDATA: {}},
            },
            "Os": "linux",
            "Architecture": "amd64",
        }

    def make_container_runner(self, root, container_id="a" * 64):
        state = Path(root)
        self.launcher.owned_state(state)
        runner = self.launcher.DockerPostgresRunner(state, self.docker_image_metadata())
        record = runner._create_record()
        runner._store_container_id(record, container_id)
        return state, runner

    def container_inspect(self, state, runner, container_id, status="exited"):
        mounts = [
            {
                "Type": "bind",
                "Source": str((state / "pgdata").resolve()),
                "Destination": self.launcher.PGVECTOR_IMAGE_PGDATA,
                "RW": True,
                "Mode": "",
                "Propagation": "rprivate",
            },
            {
                "Type": "bind",
                "Source": str((state / "s").resolve()),
                "Destination": str(state / "s"),
                "RW": True,
                "Mode": "",
                "Propagation": "rprivate",
            },
            {
                "Type": "bind",
                "Source": str((state / "container.passwd").resolve()),
                "Destination": "/etc/passwd",
                "RW": False,
                "Mode": "",
                "Propagation": "rprivate",
            },
            {
                "Type": "bind",
                "Source": str((state / "container.group").resolve()),
                "Destination": "/etc/group",
                "RW": False,
                "Mode": "",
                "Propagation": "rprivate",
            },
        ]
        return {
            "Id": container_id,
            "Name": f"/{runner.name}",
            "Image": self.launcher.PGVECTOR_IMAGE_ID,
            "Path": "/bin/sleep",
            "Args": ["infinity"],
            "Config": {
                "Image": self.launcher.PGVECTOR_IMAGE_ID,
                "User": f"{os.getuid()}:{os.getgid()}",
                "Entrypoint": ["/bin/sleep"],
                "Cmd": ["infinity"],
                "Env": self.docker_image_metadata()["env"],
                "Labels": runner.labels,
                "OpenStdin": False,
                "Tty": False,
            },
            "HostConfig": {
                "NetworkMode": "none",
                "PortBindings": None,
                "Privileged": False,
                "ReadonlyRootfs": True,
                "CapAdd": None,
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges:true"],
                "PidMode": "",
                "IpcMode": "private",
                "UTSMode": "",
                "UsernsMode": "",
                "AutoRemove": False,
                "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
                "Devices": None,
                "DeviceRequests": None,
                "Tmpfs": None,
                "Binds": None,
                "VolumesFrom": None,
                "Mounts": [
                    {
                        "Type": "bind",
                        "Source": str((state / "pgdata").resolve()),
                        "Target": self.launcher.PGVECTOR_IMAGE_PGDATA,
                        "ReadOnly": False,
                        "BindOptions": {"Propagation": "rprivate"},
                    },
                    {
                        "Type": "bind",
                        "Source": str((state / "s").resolve()),
                        "Target": str(state / "s"),
                        "ReadOnly": False,
                        "BindOptions": {"Propagation": "rprivate"},
                    },
                    {
                        "Type": "bind",
                        "Source": str((state / "container.passwd").resolve()),
                        "Target": "/etc/passwd",
                        "ReadOnly": True,
                        "BindOptions": {"Propagation": "rprivate"},
                    },
                    {
                        "Type": "bind",
                        "Source": str((state / "container.group").resolve()),
                        "Target": "/etc/group",
                        "ReadOnly": True,
                        "BindOptions": {"Propagation": "rprivate"},
                    },
                ],
            },
            "Mounts": mounts,
            "State": {"Status": status},
            "NetworkSettings": {"Networks": {"none": {}}},
        }

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

    def test_docker_cli_forces_local_endpoint_and_discards_context_overrides(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "DOCKER_HOST": "tcp://untrusted.example:2376",
                        "DOCKER_CONTEXT": "untrusted",
                        "PGHOST": "production.invalid",
                    },
                ),
                mock.patch.object(
                    self.launcher.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ) as run,
            ):
                self.launcher.docker_run(
                    ["image", "inspect", "sha256:abc"], home=Path(temporary)
                )
            argv = run.call_args.args[0]
            environment = run.call_args.kwargs["env"]
            self.assertEqual(argv[1:3], ["--host", self.launcher.DOCKER_ENDPOINT])
            self.assertEqual(set(environment), {"PATH", "HOME", "LANG"})
            self.assertEqual(environment["HOME"], temporary)

    def test_pinned_image_check_is_local_and_rejects_identity_drift(self):
        image = self.docker_image_inspect()
        result = subprocess.CompletedProcess([], 0, json.dumps([image]), "")
        with mock.patch.object(self.launcher, "docker_run", return_value=result) as run:
            verified = self.launcher.verify_docker_image()
        self.assertEqual(verified, self.docker_image_metadata())
        self.assertEqual(
            run.call_args.args[0],
            ["image", "inspect", self.launcher.PGVECTOR_IMAGE_ID],
        )
        self.assertNotIn("pull", run.call_args.args[0])

        image["Config"]["Env"].append("LD_PRELOAD=/tmp/untrusted.so")
        with (
            mock.patch.object(
                self.launcher,
                "docker_run",
                return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps([image]), ""
                ),
            ),
            self.assertRaises(self.launcher.LaunchBlocked),
        ):
            self.launcher.verify_docker_image()

    def test_container_create_uses_exact_mounts_inert_command_and_no_host_network(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state = Path(temporary)
            self.launcher.owned_state(state)
            runner = self.launcher.DockerPostgresRunner(
                state, self.docker_image_metadata()
            )
            runner._state_dirs(create=True)
            self.launcher._container_identity_files(state)
            argv = runner._create_argv()
            self.assertIn("--network", argv)
            self.assertEqual(argv[argv.index("--network") + 1], "none")
            self.assertIn("--pull=never", argv)
            self.assertEqual(argv[argv.index("--restart") + 1], "no")
            self.assertEqual(argv[argv.index("--entrypoint") + 1], "/bin/sleep")
            self.assertEqual(argv[-2:], [self.launcher.PGVECTOR_IMAGE_ID, "infinity"])
            mounts = [
                argv[i + 1] for i, item in enumerate(argv[:-1]) if item == "--mount"
            ]
            self.assertEqual(len(mounts), 4)
            self.assertTrue(
                any("target=/var/lib/postgresql/data" in item for item in mounts)
            )
            self.assertTrue(
                any("target=/etc/passwd,readonly" in item for item in mounts)
            )
            self.assertTrue(
                any("target=/etc/group,readonly" in item for item in mounts)
            )
            self.assertFalse(
                any(
                    item in argv
                    for item in ("--privileged", "-p", "--publish", "--volume")
                )
            )

    def test_existing_unproven_container_is_not_adopted_or_changed(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state = Path(temporary)
            self.launcher.owned_state(state)
            runner = self.launcher.DockerPostgresRunner(
                state, self.docker_image_metadata()
            )
            existing = {"Id": "b" * 64}
            with mock.patch.object(runner, "_inspect", return_value=existing):
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner._ensure_container()
            self.assertFalse(runner.started_by_invocation)
            self.assertFalse((state / "container-owner.json").exists())

    def test_inspect_failure_is_not_treated_as_container_absence(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            with mock.patch.object(
                self.launcher,
                "docker_run",
                return_value=subprocess.CompletedProcess(
                    [], 1, "", "permission denied by daemon"
                ),
            ):
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner._inspect(runner.container_id)

    def test_running_recorded_container_is_refused_without_stop(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            info = self.container_inspect(state, runner, runner.container_id, "running")
            with mock.patch.object(
                runner, "_inspect", side_effect=[info, info]
            ) as inspect:
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner._ensure_container()
            self.assertEqual(inspect.call_count, 2)
            self.assertFalse(runner.started_by_invocation)

    def test_container_reuse_requires_exact_environment_network_and_mounts(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            cases = []
            altered_env = self.container_inspect(state, runner, runner.container_id)
            altered_env["Config"]["Env"].append("LD_PRELOAD=/tmp/injected.so")
            cases.append(altered_env)
            altered_network = self.container_inspect(state, runner, runner.container_id)
            altered_network["NetworkSettings"]["Networks"] = {
                "none": {},
                "bridge": {},
            }
            cases.append(altered_network)
            altered_mount = self.container_inspect(state, runner, runner.container_id)
            altered_mount["Mounts"].append(
                {
                    "Type": "volume",
                    "Source": "unowned",
                    "Destination": "/extra",
                    "RW": True,
                }
            )
            cases.append(altered_mount)
            altered_mount_mode = self.container_inspect(
                state, runner, runner.container_id
            )
            altered_mount_mode["Mounts"][0]["Mode"] = "z"
            cases.append(altered_mount_mode)
            altered_host_mount = self.container_inspect(
                state, runner, runner.container_id
            )
            altered_host_mount["HostConfig"]["Mounts"][2]["ReadOnly"] = False
            cases.append(altered_host_mount)
            extra_host_mount = self.container_inspect(
                state, runner, runner.container_id
            )
            extra_host_mount["HostConfig"]["Mounts"].append(
                {
                    "Type": "bind",
                    "Source": str((state / "pgdata").resolve()),
                    "Target": "/extra",
                    "ReadOnly": False,
                    "BindOptions": {"Propagation": "rprivate"},
                }
            )
            cases.append(extra_host_mount)
            altered_command = self.container_inspect(state, runner, runner.container_id)
            altered_command["Args"] = ["--tcp-only"]
            cases.append(altered_command)
            for info in cases:
                with self.subTest(info=info):
                    with self.assertRaises(self.launcher.LaunchBlocked):
                        runner._validate_inspect(info, expected_id=runner.container_id)

            (state / "container.passwd").write_text(
                "different:x:1000:1000::/:/bin/false\n"
            )
            with self.assertRaises(self.launcher.LaunchBlocked):
                runner._load_record()

    def test_stopped_exact_container_is_started_and_stopped_by_full_id(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            container_id = runner.container_id
            stopped = self.container_inspect(state, runner, container_id, "exited")
            running = self.container_inspect(state, runner, container_id, "running")
            exited = self.container_inspect(state, runner, container_id, "exited")
            with (
                mock.patch.object(
                    runner,
                    "_inspect",
                    side_effect=[stopped, stopped, running, running, exited],
                ),
                mock.patch.object(
                    self.launcher,
                    "docker_run",
                    return_value=subprocess.CompletedProcess([], 0, container_id, ""),
                ) as run,
            ):
                runner.prepare()
                self.assertTrue(runner.started_by_invocation)
                runner.stop_container()
            self.assertFalse(runner.started_by_invocation)
            self.assertEqual(
                run.call_args_list[0].args[0], ["container", "start", container_id]
            )
            self.assertEqual(
                run.call_args_list[1].args[0],
                ["container", "stop", "--time", "10", container_id],
            )

    def test_first_absent_runtime_creates_and_starts_only_pinned_inert_container(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state = Path(temporary)
            self.launcher.owned_state(state)
            runner = self.launcher.DockerPostgresRunner(
                state, self.docker_image_metadata()
            )
            container_id = "d" * 64
            created = self.container_inspect(state, runner, container_id, "created")
            running = self.container_inspect(state, runner, container_id, "running")
            with (
                mock.patch.object(
                    runner, "_inspect", side_effect=[None, created, created, running]
                ),
                mock.patch.object(
                    self.launcher,
                    "docker_run",
                    side_effect=[
                        subprocess.CompletedProcess([], 0, container_id, ""),
                        subprocess.CompletedProcess([], 0, container_id, ""),
                    ],
                ) as run,
            ):
                runner.prepare()
            record = json.loads((state / "container-owner.json").read_text())
            self.assertEqual(record["container_id"], container_id)
            self.assertTrue(runner.started_by_invocation)
            self.assertEqual(
                run.call_args_list[0].args[0][-3:],
                ["/bin/sleep", self.launcher.PGVECTOR_IMAGE_ID, "infinity"],
            )
            self.assertEqual(
                run.call_args_list[1].args[0], ["container", "start", container_id]
            )
            runner.started_by_invocation = False

    def test_uncertain_container_start_is_inspected_once_and_never_stopped(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            container_id = runner.container_id
            stopped = self.container_inspect(state, runner, container_id, "exited")
            running = self.container_inspect(state, runner, container_id, "running")
            with (
                mock.patch.object(
                    runner, "_inspect", side_effect=[stopped, stopped, running]
                ),
                mock.patch.object(
                    self.launcher,
                    "docker_run",
                    return_value=subprocess.CompletedProcess(
                        [], 1, "", "start response lost"
                    ),
                ) as run,
            ):
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner.prepare()
            self.assertFalse(runner.started_by_invocation)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(
                run.call_args.args[0], ["container", "start", container_id]
            )

    def test_uncertain_container_stop_is_inspected_once_and_preserved(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            container_id = runner.container_id
            running = self.container_inspect(state, runner, container_id, "running")
            with (
                mock.patch.object(runner, "_inspect", side_effect=[running, running]),
                mock.patch.object(
                    self.launcher,
                    "docker_run",
                    return_value=subprocess.CompletedProcess(
                        [], 1, "", "stop timed out"
                    ),
                ) as run,
            ):
                runner.started_by_invocation = True
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner.stop_container()
            self.assertTrue(runner.started_by_invocation)
            self.assertEqual(
                run.call_args.args[0],
                ["container", "stop", "--time", "10", container_id],
            )

    def test_uncertain_container_create_is_not_adopted_or_cleaned(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state = Path(temporary)
            self.launcher.owned_state(state)
            runner = self.launcher.DockerPostgresRunner(
                state, self.docker_image_metadata()
            )

            def docker_result(argv, **kwargs):
                if argv[0] == "inspect":
                    return subprocess.CompletedProcess(
                        argv, 1, "", f"Error: No such object: {argv[-1]}"
                    )
                if argv[:2] == ["container", "create"]:
                    return subprocess.CompletedProcess(argv, 1, "", "connection lost")
                self.fail(f"unexpected Docker action: {argv}")

            with mock.patch.object(
                self.launcher, "docker_run", side_effect=docker_result
            ) as run:
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner._ensure_container()
            self.assertIsNone(runner.container_id)
            self.assertFalse(runner.started_by_invocation)
            self.assertFalse(
                any(
                    call.args[0][:2] in (["container", "stop"], ["container", "rm"])
                    for call in run.call_args_list
                )
            )

    def test_successful_create_id_is_recorded_before_inspect(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state = Path(temporary)
            self.launcher.owned_state(state)
            runner = self.launcher.DockerPostgresRunner(
                state, self.docker_image_metadata()
            )
            container_id = "c" * 64

            def docker_result(argv, **kwargs):
                if argv[0] == "inspect" and argv[-1] == runner.name:
                    return subprocess.CompletedProcess(
                        argv, 1, "", f"Error: No such object: {runner.name}"
                    )
                if argv[:2] == ["container", "create"]:
                    return subprocess.CompletedProcess(argv, 0, container_id, "")
                if argv[0] == "inspect" and argv[-1] == container_id:
                    return subprocess.CompletedProcess(
                        argv, 1, "", "daemon unavailable"
                    )
                self.fail(f"unexpected Docker action: {argv}")

            with mock.patch.object(
                self.launcher, "docker_run", side_effect=docker_result
            ) as run:
                with self.assertRaises(self.launcher.LaunchBlocked):
                    runner._ensure_container()
            record = json.loads((state / "container-owner.json").read_text())
            self.assertEqual(record["container_id"], container_id)
            self.assertFalse(runner.started_by_invocation)
            self.assertFalse(
                any(
                    call.args[0][:2]
                    in (
                        ["container", "start"],
                        ["container", "stop"],
                        ["container", "rm"],
                    )
                    for call in run.call_args_list
                )
            )

    def test_container_start_argv_clears_environment_and_keeps_peer_auth(self):
        with tempfile.TemporaryDirectory(prefix="nd-") as temporary:
            state, runner = self.make_container_runner(temporary)
            runner.started_by_invocation = True
            with mock.patch.object(
                self.launcher,
                "docker_run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ) as run:
                runner.run(
                    "initdb",
                    [
                        "-D",
                        self.launcher.PGVECTOR_IMAGE_PGDATA,
                        "--auth-local=peer",
                        "--auth-host=reject",
                    ],
                    env={"PGHOST": "production.invalid", "DATABASE_URL": "secret"},
                    check=True,
                )
            argv = run.call_args.args[0]
            self.assertEqual(
                argv[:4],
                ["exec", "--user", f"{os.getuid()}:{os.getgid()}", runner.container_id],
            )
            self.assertIn("/usr/bin/env", argv)
            self.assertIn("-i", argv)
            self.assertIn(f"{self.launcher.PGVECTOR_BIN_DIR}/initdb", argv)
            self.assertIn("--auth-local=peer", argv)
            self.assertIn("--auth-host=reject", argv)
            self.assertNotIn("production.invalid", argv)
            self.assertNotIn("secret", argv)

    def test_unexpected_prestart_postmaster_is_never_stopped_or_container_cleaned(self):
        class ExistingProcessRunner:
            containerized = True
            started_by_invocation = True

            def __init__(self, status):
                self.status = status
                self.commands = []
                self.container_stopped = False

            def prepare(self):
                return None

            def data_directory(self, state):
                return Path("/var/lib/postgresql/data")

            def run(self, tool, args, **kwargs):
                self.commands.append((tool, args))
                return subprocess.CompletedProcess([], self.status)

            def stop_container(self):
                self.container_stopped = True

        for status in (0, 4):
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory(prefix="nd-") as temporary,
            ):
                runner = ExistingProcessRunner(status)
                generator = self.launcher.isolated_database(
                    Path(temporary), {}, Path(temporary), runner
                )
                with self.assertRaises(self.launcher.LaunchBlocked):
                    next(generator)
                self.assertEqual(
                    runner.commands,
                    [("pg_ctl", ["-D", "/var/lib/postgresql/data", "status"])],
                )
                self.assertFalse(runner.container_stopped)

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
            (root / "pgdata" / "PG_VERSION").write_text("16\n")
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
            (root / "pgdata" / "PG_VERSION").write_text("16\n")
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
            (root / "pgdata" / "PG_VERSION").write_text("16\n")
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

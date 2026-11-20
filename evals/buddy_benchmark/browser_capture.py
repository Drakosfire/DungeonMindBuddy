"""Loopback browser driver for an isolated retained ordinary Plan benchmark."""
from contextlib import contextmanager
from hashlib import sha256
from unittest.mock import patch
from contextvars import ContextVar, copy_context
from functools import wraps
import json
import os
from pathlib import Path
import socket
import subprocess
from threading import Thread
from time import monotonic_ns, sleep
from uuid import UUID, uuid4

import httpx
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse
import uvicorn

from evals.buddy_benchmark import artifacts, workflow
from evals.buddy_benchmark.context_capture import ContextCapture


def browser_inputs(manifest, base):
    """Load the exact browser bundle inventory and retained Jev tapes before dispatch."""
    spec = manifest["browser_capture"]
    bundle = (base / spec["bundle"]).resolve()
    expected = json.loads(workflow.read_pin(spec["bundle_inventory"], base))
    actual = {str(path.relative_to(bundle)): sha256(path.read_bytes()).hexdigest()
              for path in bundle.rglob("*") if path.is_file()}
    if "index.html" not in actual or actual != expected or any(path.is_symlink() for path in bundle.rglob("*")):
        raise ValueError("Browser UI bundle differs from its pinned inventory")
    wire = json.loads(workflow.read_pin(spec["jev_wire"], base))
    if not wire or any(
        row["method"] != "POST" or row["response_status"] != 200
        or not bytes.fromhex(row["request_hex"]) or not bytes.fromhex(row["response_hex"])
        for row in wire
    ):
        raise ValueError("Browser benchmark requires a successful pinned Jev replay")
    settled = spec.get("settled_pane", False)
    if type(settled) is not bool:
        raise ValueError("Invalid browser cache condition")
    return bundle, wire, settled


def browser_capture(application, manifest, case, output, token, inputs, owned_env, *, detail):
    from apps.live_control_server.services import plan_jev_dispatch
    import httpx2

    if (os.environ.get("DMB_DEPLOYMENT_ENVIRONMENT"), os.environ.get("DMB_AUTH_MODE"),
            os.environ.get("DMB_AGENT_GRAPH_AUTH_MODE"), os.environ.get("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT")) != (
            "local", "local_operator", "local_operator", "local"):
        raise ValueError("Browser capture requires explicit local operator auth")
    if any(os.environ.get(key) for key in ("TYPESAFE_JEV_API_KEY", "OPENAI_API_KEY")):
        raise ValueError("Provider-free browser capture requires a credential-free worker process")
    bundle, wire, settled = inputs
    template = manifest["request_template"]
    world = manifest["world"]
    work = template["primary_work"]
    directory = output / case["id"]
    directory.mkdir(mode=0o700)
    replayed = []
    wire_intervals = []

    async def replay(self, request):
        entered = monotonic_ns()
        self.on_dispatch()
        if len(replayed) >= len(wire):
            raise ValueError("Unpinned Jev dispatch")
        row = wire[len(replayed)]
        if (request.method, str(request.url), request.content.hex()) != (
                row["method"], row["url"], row["request_hex"]):
            raise ValueError("Ordinary Jev request differs from its pinned replay")
        response = httpx2.Response(row["response_status"], content=bytes.fromhex(row["response_hex"]),
                                   headers={"Content-Type": row["response_content_type"]})
        replayed.append(sha256(request.content).hexdigest())
        if detail:
            wire_intervals.append({"mode": "replay", "entry_ns": entered, "body_read_ns": monotonic_ns()})
        return response

    sink = ContextCapture(directory, writer_transport=True, detailed_trace=detail)
    browser_request = None
    plan_gets = []
    active_plan_get = ContextVar("benchmark_active_plan_get", default=None)
    plan_get_path = "/api/live/workspace-documents/" + work["object_id"] + "/committed-revision"
    if detail:
        routes = [route for route in application.routes
                  if getattr(route, "path", None) == "/api/live/workspace-documents/{document_id}/committed-revision"
                  and "GET" in getattr(route, "methods", set())]
        if len(routes) != 1:
            raise ValueError("Expected one committed Plan revision route")
        dependant = routes[0].dependant
        run_handler = dependant.call

        @wraps(run_handler)
        def measured_handler(*args, **kwargs):
            row = active_plan_get.get()
            if row is None:
                return run_handler(*args, **kwargs)
            row["handler_start_ns"] = monotonic_ns()
            try:
                return run_handler(*args, **kwargs)
            finally:
                row["handler_end_ns"] = monotonic_ns()

        dependant.call = measured_handler

    async def dispatch(scope, receive, send):
        nonlocal browser_request
        if scope["type"] != "http":
            return await application(scope, receive, send)
        path, method = scope["path"], scope["method"]
        if path == "/__benchmark/clock" and method == "GET":
            return await PlainTextResponse(str(monotonic_ns() / 1e6))(scope, receive, send)
        if not path.startswith(("/api/", "/health/")) and method == "GET":
            target = (bundle / path.lstrip("/")).resolve()
            if target.is_relative_to(bundle) and target.is_file():
                return await FileResponse(target)(scope, receive, send)
            if not path.startswith("/assets/"):
                return await FileResponse(bundle / "index.html")(scope, receive, send)
            return await PlainTextResponse("missing asset", status_code=404)(scope, receive, send)
        if detail and path == plan_get_path and method == "GET":
            row = {"ingress_ns": monotonic_ns()}
            plan_gets.append(row)
            token = active_plan_get.set(row)

            async def observed_send(frame):
                if frame["type"] == "http.response.start":
                    row["headers_ns"] = monotonic_ns()
                    row["status"] = frame["status"]
                elif frame["type"] == "http.response.body" and not frame.get("more_body"):
                    row["response_end_ns"] = monotonic_ns()
                await send(frame)

            try:
                return await application(scope, receive, observed_send)
            finally:
                active_plan_get.reset(token)
        if path == "/api/live/agent/turn" and method == "POST":
            tick = monotonic_ns()
            chunks = []
            while True:
                frame = await receive()
                if frame["type"] != "http.request":
                    raise ValueError("Browser disconnected before dispatch")
                chunks.append(frame["body"])
                if not frame.get("more_body"):
                    break
            body = b"".join(chunks)
            parsed = json.loads(body)
            if (browser_request is not None or parsed.get("message") != case["question"]
                    or parsed.get("surface", {}).get("surface_id") != "plan"
                    or parsed.get("owner_scope") != template["owner_scope"]
                    or parsed.get("primary_work") != work):
                return await JSONResponse({"error": "Benchmark request did not match fixture"}, 409)(scope, receive, send)
            browser_request = parsed
            sink.request_started_monotonic_ns = tick
            async def deliver_body():
                nonlocal body
                if body is None:
                    return await receive()
                raw, body = body, None
                return {"type": "http.request", "body": raw, "more_body": False}
            return await application(scope, deliver_body, send)
        return await application(scope, receive, send)

    async def serve(scope, receive, send):
        from urllib.parse import urljoin, urlsplit

        async def local_response(frame):
            if frame["type"] == "http.response.start":
                for name, value in frame.get("headers", []):
                    if name.lower() == b"location":
                        destination = urlsplit(urljoin(origin, value.decode("latin-1")))
                        if (destination.scheme, destination.netloc) != ("http", sock_host):
                            raise ValueError("Benchmark app attempted a cross-origin redirect")
            await send(frame)

        await dispatch(scope, receive, local_response)

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock_host = f"127.0.0.1:{sock.getsockname()[1]}"
    origin = "http://" + sock_host
    local_env = dict(owned_env, DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN=origin,
                     DMB_AGENT_GRAPH_LOCAL_API_HOST=sock_host,
                     TYPESAFE_JEV_API_KEY="retained-jev-replay",
                     OPENAI_API_KEY="local-writer-transport-sink")
    server = uvicorn.Server(uvicorn.Config(serve, log_level="warning", access_log=False, timeout_graceful_shutdown=10))
    route = "/api/live/agent/worlds/" + world + "/conversation"
    try:
        with (patch.dict(os.environ, local_env),
              patch.object(plan_jev_dispatch._ObservedJevTransport, "handle_async_request", replay),
              sink.install()):
            thread = Thread(target=copy_context().run, args=(server.run,),
                            kwargs={"sockets": [sock]}, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if server.started:
                        break
                    sleep(0.05)
                if not server.started:
                    raise ValueError("Isolated browser server failed to start")
                with httpx.Client(base_url=origin, headers={"Authorization": "Bearer " + token},
                                  timeout=45, trust_env=False) as client:
                    client.get("/health/ready").raise_for_status()
                    workflow.verify_capture_environment(local_env)
                    if plan_jev_dispatch.request_budget() != manifest["provider_policy"]:
                        raise ValueError("Effective ordinary provider policy differs")
                    history = client.get(route).raise_for_status().json()
                    command = {"schema": "dmb_agent_new_conversation_v1", "command_id": str(uuid4()),
                        "expected_pointer_revision": history["pointer_revision"],
                        "expected_active_conversation_id": history["active_conversation_id"]}
                    client.post(route + "/new", json=command).raise_for_status()
                    fresh = client.get(route).raise_for_status().json()
                    if fresh["turns"]:
                        raise ValueError("Browser fixture conversation was not empty")
                    runtime = output / "runtime-artifacts"
                    env = {
                        "PATH": os.defpath, "HOME": str(runtime), "TMPDIR": str(output.parent),
                        "DMB_BENCHMARK_BROWSER_ORIGIN": origin, "DMB_BENCHMARK_BROWSER_TOKEN": token,
                        "DMB_BENCHMARK_DOCUMENT_ID": work["object_id"], "DMB_BENCHMARK_WORLD": world,
                        "DMB_BENCHMARK_QUESTION": case["question"], "DMB_BENCHMARK_PANE_SETTLED": "1" if settled else "0",
                        "DMB_BENCHMARK_BROWSER_RESULT": str(output / "browser-timing.json"),
                        "DMB_BENCHMARK_PLAYWRIGHT": os.environ["DMB_BENCHMARK_PLAYWRIGHT"],
                        "DMB_BENCHMARK_CHROMIUM": os.environ["DMB_BENCHMARK_CHROMIUM"],
                    }
                    driver = Path(__file__).with_name("browser_send.cjs")
                    artifacts.immutable_save(directory, "dispatch", {"state": "dispatching", "automatic_restart": False})
                    run = subprocess.run([os.environ["DMB_BENCHMARK_NODE"], str(driver)], env=env, timeout=100)
                    if run.returncode or browser_request is None:
                        raise ValueError("Ordinary Plan browser Send did not capture the expected request")
                    artifacts.immutable_save(directory, "request", browser_request)
                    after = workflow.response_envelope(
                        client.get(route, params={"include_turn_correlation": "true"}).raise_for_status())
                    turns = workflow._request_turns(after["body"], browser_request, world)
                    if len(turns) != 1:
                        raise ValueError("Browser request has no unique retained Turn")
                    from application_state.agent_conversation import AgentConversationService
                    turn_id = turns[0]["turn_id"]
                    observed = AgentConversationService().inspect_turn(world_id=world, turn_id=UUID(turn_id))
                    if len(replayed) != len(wire):
                        raise ValueError("Ordinary browser turn did not consume its entire Jev tape")
                    sink.finalize(observed)
                    artifacts.immutable_save(directory, "history-after", after)
                    trace = client.get(route + "/turns/" + turn_id + "/context-trace").raise_for_status()
                    artifacts.immutable_save(directory, "context-trace", workflow.response_envelope(trace))
            finally:
                server.should_exit = True
                # Keep the exact-wire and writer guards until the application
                # has left its event loop, including on a browser timeout.
                thread.join()
    finally:
        sock.close()
        if detail:
            artifacts.immutable_save(output, "plan-preflight-intervals", plan_gets)
        artifacts.immutable_save(output, "jev-replay", replayed)
        if detail:
            artifacts.immutable_save(output, "jev-transport-intervals", wire_intervals)

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


def browser_inputs(manifest, base, *, build_fixture=False):
    """Load the exact browser bundle inventory and retained Jev tapes before dispatch."""
    spec = manifest["browser_capture"]
    bundle = (base / spec["bundle"]).resolve()
    expected = json.loads(workflow.read_pin(spec["bundle_inventory"], base))
    actual = {str(path.relative_to(bundle)): sha256(path.read_bytes()).hexdigest()
              for path in bundle.rglob("*") if path.is_file()}
    if "index.html" not in actual or actual != expected or any(path.is_symlink() for path in bundle.rglob("*")):
        raise ValueError("Browser UI bundle differs from its pinned inventory")
    wire = [] if build_fixture else json.loads(workflow.read_pin(spec["jev_wire"], base))
    if not build_fixture and (not wire or any(
        row["method"] != "POST" or row["response_status"] != 200
        or not bytes.fromhex(row["request_hex"]) or not bytes.fromhex(row["response_hex"])
        for row in wire
    )):
        raise ValueError("Browser benchmark requires a successful pinned Jev replay")
    if build_fixture and (not isinstance(spec.get("selection_text"), str) or not spec["selection_text"].strip()):
        raise ValueError("Build fixture requires exact selected text")
    settled = spec.get("settled_pane", False)
    if type(settled) is not bool:
        raise ValueError("Invalid browser cache condition")
    return bundle, wire, settled


def browser_scratch_directory(output):
    """Allow a short socket path on the same filesystem as retained evidence."""
    configured = os.environ.get("DMB_BENCHMARK_BROWSER_TMPDIR")
    if configured is None:
        return output.parent
    scratch = Path(configured)
    if not scratch.is_absolute() or not scratch.is_dir() or scratch.stat().st_dev != output.stat().st_dev:
        raise ValueError("Browser scratch must be an existing absolute directory on the evidence filesystem")
    return scratch.resolve()


def browser_capture(application, manifest, case, output, token, inputs, owned_env, *, detail, build_fixture=False, live_build=False):
    from apps.live_control_server.hosted_worker import with_startup_gc
    from apps.live_control_server.services import plan_jev_dispatch
    import httpx2

    if (os.environ.get("DMB_DEPLOYMENT_ENVIRONMENT"), os.environ.get("DMB_AUTH_MODE"),
            os.environ.get("DMB_AGENT_GRAPH_AUTH_MODE"), os.environ.get("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT")) != (
            "local", "local_operator", "local_operator", "local"):
        raise ValueError("Browser capture requires explicit local operator auth")
    if live_build and (not build_fixture or detail):
        raise ValueError("Live browser delivery requires the Build fixture")
    if not live_build and any(os.environ.get(key) for key in ("TYPESAFE_JEV_API_KEY", "OPENAI_API_KEY")):
        raise ValueError("Provider-free browser capture requires a credential-free worker process")
    scratch = browser_scratch_directory(output)
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
            if build_fixture:
                try:
                    if browser_request is not None:
                        raise ValueError("Only one Build fixture request is allowed")
                    validate_build_browser_request(parsed, world=world, work=work, question=case["question"],
                        selection_text=manifest["browser_capture"]["selection_text"],
                        conversation_id=fresh["active_conversation_id"], pointer_revision=fresh["pointer_revision"])
                except (ValueError, KeyError):
                    return await JSONResponse({"error": "Build fixture request did not match"}, 409)(scope, receive, send)
                browser_request = parsed
                if not live_build:
                    return await JSONResponse({"code": "benchmark_build_fixture_captured"}, 409)(scope, receive, send)
            elif (browser_request is not None or parsed.get("message") != case["question"]
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
            if not live_build:
                return await application(scope, deliver_body, send)
            response_bytes = bytearray()
            transport_status = None
            content_type = ""
            transport_complete = False

            async def retain_build_response(frame):
                nonlocal transport_status, content_type, transport_complete
                if frame["type"] == "http.response.start":
                    transport_status = frame["status"]
                    content_type = dict(frame.get("headers", [])).get(b"content-type", b"").decode("latin-1")
                elif frame["type"] == "http.response.body":
                    response_bytes.extend(frame.get("body", b""))
                    transport_complete = not frame.get("more_body")
                await send(frame)

            try:
                return await application(scope, deliver_body, retain_build_response)
            finally:
                if transport_status is not None:
                    artifacts.immutable_save(directory, "build-wire-response", {
                        "status": transport_status, "content_type": content_type,
                        "transport_complete": transport_complete,
                        "raw_body_hex": response_bytes.hex(),
                        "raw_body_sha256": sha256(response_bytes).hexdigest(),
                        "elapsed_ms": (monotonic_ns() - tick) / 1e6,
                    })

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
                     DMB_AGENT_GRAPH_LOCAL_API_HOST=sock_host)
    if not live_build:
        local_env.update(TYPESAFE_JEV_API_KEY="retained-jev-replay",
                         OPENAI_API_KEY="local-writer-transport-sink")
    server = uvicorn.Server(uvicorn.Config(with_startup_gc(serve), log_level="warning",
                                           access_log=False, timeout_graceful_shutdown=10))
    route = "/api/live/agent/worlds/" + world + "/conversation"
    from contextlib import nullcontext
    jev_guard = (nullcontext() if live_build else
                 patch.object(plan_jev_dispatch._ObservedJevTransport, "handle_async_request", replay))
    writer_guard = nullcontext() if live_build else sink.install()
    try:
        with patch.dict(os.environ, local_env), jev_guard, writer_guard:
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
                        "PATH": os.defpath, "HOME": str(runtime), "TMPDIR": str(scratch),
                        "DMB_BENCHMARK_BROWSER_ORIGIN": origin, "DMB_BENCHMARK_BROWSER_TOKEN": token,
                        "DMB_BENCHMARK_DOCUMENT_ID": work["object_id"], "DMB_BENCHMARK_WORLD": world,
                        "DMB_BENCHMARK_QUESTION": case["question"], "DMB_BENCHMARK_PANE_SETTLED": "1" if settled else "0",
                        "DMB_BENCHMARK_SURFACE": "build" if build_fixture else "plan",
                        "DMB_BENCHMARK_LIVE_BUILD": "1" if live_build else "0",
                        "DMB_BENCHMARK_SELECTION": manifest["browser_capture"].get("selection_text", "") if build_fixture else "",
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
                    if build_fixture and not live_build:
                        after = client.get(route).raise_for_status().json()
                        if after["turns"] or after["active_conversation_id"] != fresh["active_conversation_id"]:
                            raise ValueError("Build fixture preflight unexpectedly created a turn")
                        artifacts.immutable_save(directory, "fixture-result", {
                            "status": "captured", "forwarded_to_application": False,
                            "provider_calls": 0, "selection_text": manifest["browser_capture"]["selection_text"],
                        })
                        return
                    after = workflow.response_envelope(
                        client.get(route, params={"include_turn_correlation": "true"}).raise_for_status())
                    artifacts.immutable_save(directory, "history-after", after)
                    if live_build:
                        wire_response = json.loads((directory / "build-wire-response.json").read_bytes())
                        wire_bytes = bytes.fromhex(wire_response["raw_body_hex"])
                        body, status = build_browser_terminal(
                            wire_bytes, wire_response["status"], wire_response["content_type"], browser_request["turn_id"])
                        raw = json.dumps(body).encode("utf-8")
                        artifacts.immutable_save(directory, "answer-http", {
                            "body": body, "http_status": status, "transport_status": wire_response["status"],
                            "raw_body_hex": raw.hex(), "raw_body_sha256": sha256(raw).hexdigest(),
                            "elapsed_ms": wire_response["elapsed_ms"],
                        })
                    turns = workflow._request_turns(after["body"], browser_request, world)
                    if len(turns) != 1:
                        raise ValueError("Browser request has no unique retained Turn")
                    from application_state.agent_conversation import AgentConversationService
                    turn_id = turns[0]["turn_id"]
                    observed = AgentConversationService().inspect_turn(world_id=world, turn_id=UUID(turn_id))
                    if len(replayed) != len(wire):
                        raise ValueError("Ordinary browser turn did not consume its entire Jev tape")
                    if not live_build:
                        sink.finalize(observed)
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


def build_browser_terminal(raw, status, content_type, turn_id):
    """Read the same terminal result or error consumed by the Build browser."""
    if content_type.split(";", 1)[0].strip().lower() != "text/event-stream":
        return json.loads(raw), status
    for frame in raw.decode("utf-8").replace("\r\n", "\n").split("\n\n")[:-1]:
        data = "\n".join(line[5:].lstrip() for line in frame.splitlines() if line.startswith("data:"))
        if not data:
            continue
        event = json.loads(data)
        if event.get("schema") != "dmb_build_turn_stream_v1" or event.get("client_turn_id") != turn_id:
            raise ValueError("Build event stream belongs to another request")
        if event.get("kind") == "result" and isinstance(event.get("response"), dict):
            return event["response"], status
        if event.get("kind") == "error" and type(event.get("status")) is int:
            return {"detail": event.get("detail")}, event["status"]
    raise ValueError("Build event stream has no terminal result or error")


def validate_build_browser_request(request, *, world, work, question, selection_text,
                                   conversation_id, pointer_revision):
    """Validate a real browser-captured Build request before any model dispatch.

    This validates host bindings only. The caller must obtain the request and
    selected text from the actual browser, not construct an editor capability.
    """
    from apps.live_control_server.models.agent_turn import AgentTurnRequest

    parsed = AgentTurnRequest.model_validate(request)
    if (parsed.surface.surface_id != "build" or parsed.owner_scope is None
            or parsed.owner_scope.world_id != world or parsed.primary_work is None
            or parsed.primary_work.model_dump(mode="json", exclude_none=True) != work
            or parsed.message != question):
        raise ValueError("Build browser request differs from the pinned fixture")
    capability = parsed.build_write_capability
    context = parsed.build_draft_context
    if capability is None or context is None or capability.basis.selection is None:
        raise ValueError("Build browser request lacks its actual selected editor capability")
    basis, snapshot = capability.basis, context.snapshot
    if (str(capability.conversation_id) != str(conversation_id)
            or str(context.conversation_id) != str(conversation_id)
            or capability.expected_pointer_revision != pointer_revision
            or context.expected_pointer_revision != pointer_revision):
        raise ValueError("Build browser request differs from the current conversation")
    if (basis.selection.text != selection_text or not selection_text.strip()
            or snapshot.draft_markdown.count(selection_text) != 1):
        raise ValueError("Build browser selection is absent, ambiguous, or differs")
    if (not basis.editor_sha256 or basis.editor_sha256 != snapshot.editor_sha256
            or basis.draft_sha256 != snapshot.draft_sha256
            or capability.draft_markdown != snapshot.draft_markdown
            or basis.world_id != snapshot.world_id
            or basis.document_id != snapshot.document_id
            or basis.registry_revision != snapshot.registry_revision
            or basis.content_sha256 != snapshot.content_sha256
            or basis.visibility != snapshot.visibility
            or basis.draft_generation != snapshot.draft_generation):
        raise ValueError("Build browser editor capability differs from its working snapshot")
    return parsed

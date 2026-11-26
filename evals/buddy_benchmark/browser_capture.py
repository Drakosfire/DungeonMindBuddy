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
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse
import uvicorn

from evals.buddy_benchmark import artifacts, workflow
from evals.buddy_benchmark.context_capture import ContextCapture


def browser_inputs(manifest, base, *, build_fixture=False, live_plan=False):
    """Load the exact browser bundle inventory and retained Jev tapes before dispatch."""
    spec = manifest["browser_capture"]
    bundle = (base / spec["bundle"]).resolve()
    expected = json.loads(workflow.read_pin(spec["bundle_inventory"], base))
    actual = {str(path.relative_to(bundle)): sha256(path.read_bytes()).hexdigest()
              for path in bundle.rglob("*") if path.is_file()}
    if "index.html" not in actual or actual != expected or any(path.is_symlink() for path in bundle.rglob("*")):
        raise ValueError("Browser UI bundle differs from its pinned inventory")
    unsent_draft = spec.get("unsent_draft", False)
    if type(unsent_draft) is not bool or (unsent_draft and (not build_fixture or live_plan)):
        raise ValueError("Unsent draft requires a Build browser fixture")
    wire = [] if build_fixture or live_plan else json.loads(workflow.read_pin(spec["jev_wire"], base))
    if not (build_fixture or live_plan) and (not wire or any(
        row["method"] != "POST" or row["response_status"] != 200
        or not bytes.fromhex(row["request_hex"]) or not bytes.fromhex(row["response_hex"])
        for row in wire
    )):
        raise ValueError("Browser benchmark requires a successful pinned Jev replay")
    history_pin = spec.get("plan_history")
    if history_pin is not None and not live_plan:
        raise ValueError("A pinned Plan history requires live Plan browser capture")
    history = json.loads(workflow.read_pin(history_pin, base)) if history_pin is not None else None
    caret = spec.get("at_document_start", False)
    if type(caret) is not bool or (caret and (not live_plan or "selection_text" in spec)):
        raise ValueError("Document-start caret requires live Plan without selected text")
    if not unsent_draft and not caret and (build_fixture or live_plan) and (
            not isinstance(spec.get("selection_text"), str) or not spec["selection_text"].strip()
    ):
        raise ValueError("Browser placement fixture requires exact selected text")
    settled = spec.get("settled_pane", False)
    if type(settled) is not bool:
        raise ValueError("Invalid browser cache condition")
    return bundle, wire, settled, history


def browser_scratch_directory(output):
    """Allow a short socket path on the same filesystem as retained evidence."""
    configured = os.environ.get("DMB_BENCHMARK_BROWSER_TMPDIR")
    if configured is None:
        return output.parent
    scratch = Path(configured)
    if not scratch.is_absolute() or not scratch.is_dir() or scratch.stat().st_dev != output.stat().st_dev:
        raise ValueError("Browser scratch must be an existing absolute directory on the evidence filesystem")
    return scratch.resolve()


def browser_capture(application, manifest, case, output, token, inputs, owned_env, *, detail, build_fixture=False, live_build=False, live_plan=False):
    from apps.live_control_server.hosted_worker import with_startup_gc
    from apps.live_control_server.services import plan_jev_dispatch
    import httpx2

    if (os.environ.get("DMB_DEPLOYMENT_ENVIRONMENT"), os.environ.get("DMB_AUTH_MODE"),
            os.environ.get("DMB_AGENT_GRAPH_AUTH_MODE"), os.environ.get("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT")) != (
            "local", "local_operator", "local_operator", "local"):
        raise ValueError("Browser capture requires explicit local operator auth")
    live = live_build or live_plan
    wire_name = "plan-wire-response" if live_plan else "build-wire-response"
    confirm_save = manifest["browser_capture"].get("confirm_save", False)
    lose_confirm_ack = manifest["browser_capture"].get("lose_confirm_ack", False)
    if type(lose_confirm_ack) is not bool or (lose_confirm_ack and (not live_build or confirm_save is not True)):
        raise ValueError("Lost acknowledgement requires live Build confirmation")

    unsent_draft = manifest["browser_capture"].get("unsent_draft", False)
    if unsent_draft and (live or confirm_save or not build_fixture):
        raise ValueError("Unsent draft requires provider-free Build capture")
    turn_posts = 0
    if type(confirm_save) is not bool or (confirm_save and not live_build):
        raise ValueError("Build confirmation requires an explicit live fixture opt-in")
    if live_build and (not build_fixture or detail):
        raise ValueError("Live browser delivery requires the Build fixture")
    if not live and any(os.environ.get(key) for key in ("TYPESAFE_JEV_API_KEY", "OPENAI_API_KEY")):
        raise ValueError("Provider-free browser capture requires a credential-free worker process")
    scratch = browser_scratch_directory(output)
    bundle, wire, settled, pinned_history = inputs
    at_document_start = manifest["browser_capture"].get("at_document_start", False)
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
        nonlocal browser_request, turn_posts
        if scope["type"] != "http":
            return await application(scope, receive, send)
        path, method = scope["path"], scope["method"]
        if live and path == "/__benchmark/browser-response-retained" and method == "GET":
            wire_path = directory / (wire_name + ".json")
            result = {"retained": wire_path.is_file()}
            if confirm_save and result["retained"] and browser_request is not None:
                result["idempotency_key"] = str(uuid5(
                    NAMESPACE_URL, f"dmb-agent-turn:{world}:{browser_request['turn_id']}"))
                result["conversation_id"] = fresh["active_conversation_id"]
                wire = json.loads(wire_path.read_bytes())
                try:
                    body, status = build_browser_terminal(bytes.fromhex(wire["raw_body_hex"]),
                        wire["status"], wire["content_type"], browser_request["turn_id"])
                except BuildStreamWithoutTerminal:
                    pass
                else:
                    if status == 200 and body.get("turn_id") == browser_request["turn_id"]:
                        completion = (body.get("knowledge_context") or {}).get("completion") or {}
                        result["action_id"] = completion.get("action_id")
            return await JSONResponse(result, headers={"Cache-Control": "no-store"})(scope, receive, send)
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
            if unsent_draft:
                turn_posts += 1
                return await JSONResponse({"code": "benchmark_unexpected_draft_dispatch"}, 409)(scope, receive, send)
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
                if not live:
                    return await JSONResponse({"code": "benchmark_build_fixture_captured"}, 409)(scope, receive, send)
            elif live_plan:
                try:
                    if browser_request is not None:
                        raise ValueError("Only one Plan fixture request is allowed")
                    validate_plan_browser_placement(parsed, world=world, work=work, question=case["question"],
                        conversation_id=fresh["active_conversation_id"], pointer_revision=fresh["pointer_revision"],
                        selection_text=manifest["browser_capture"].get("selection_text", ""),
                        at_document_start=at_document_start)
                except (ValueError, KeyError):
                    artifacts.immutable_save(directory, "rejected-browser-request", parsed)
                    return await JSONResponse({"error": "Plan fixture request did not match"}, 409,
                        headers={"X-Benchmark-Placement-Rejected": "1"})(scope, receive, send)
            elif (browser_request is not None or parsed.get("message") != case["question"]
                    or parsed.get("surface", {}).get("surface_id") != "plan"
                    or parsed.get("owner_scope") != template["owner_scope"]
                    or parsed.get("primary_work") != work):
                return await JSONResponse({"error": "Benchmark request did not match fixture"}, 409)(scope, receive, send)
            browser_request = parsed
            sink.request_started_monotonic_ns = tick
            disconnect_ns = None

            async def deliver_body():
                nonlocal body, disconnect_ns
                if body is None:
                    frame = await receive()
                    if frame["type"] == "http.disconnect":
                        disconnect_ns = monotonic_ns()
                    return frame
                raw, body = body, None
                return {"type": "http.request", "body": raw, "more_body": False}
            if not live:
                return await application(scope, deliver_body, send)
            artifacts.immutable_save(directory, "request", parsed)
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
                    artifacts.immutable_save(directory, wire_name, {
                        "status": transport_status, "content_type": content_type,
                        "transport_complete": transport_complete,
                        "client_disconnect_ms": ((disconnect_ns - tick) / 1e6
                                                 if disconnect_ns is not None else None),
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
    if not live:
        local_env.update(TYPESAFE_JEV_API_KEY="retained-jev-replay",
                         OPENAI_API_KEY="local-writer-transport-sink")
    server = uvicorn.Server(uvicorn.Config(with_startup_gc(serve), log_level="warning",
                                           access_log=False, timeout_graceful_shutdown=10))
    route = "/api/live/agent/worlds/" + world + "/conversation"
    from contextlib import nullcontext
    jev_guard = (nullcontext() if live else
                 patch.object(plan_jev_dispatch._ObservedJevTransport, "handle_async_request", replay))
    writer_guard = nullcontext() if live else sink.install()
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
                    fresh = client.get(route).raise_for_status().json()
                    if pinned_history is None:
                        command = {"schema": "dmb_agent_new_conversation_v1", "command_id": str(uuid4()),
                            "expected_pointer_revision": fresh["pointer_revision"],
                            "expected_active_conversation_id": fresh["active_conversation_id"]}
                        client.post(route + "/new", json=command).raise_for_status()
                        fresh = client.get(route).raise_for_status().json()
                        if fresh["turns"]:
                            raise ValueError("Browser fixture conversation was not empty")
                    else:
                        require_plan_history(fresh, pinned_history)
                        artifacts.immutable_save(directory, "history-before", fresh)
                    runtime = output / "runtime-artifacts"
                    env = {
                        "PATH": os.defpath, "HOME": str(runtime), "TMPDIR": str(scratch),
                        "DMB_BENCHMARK_BROWSER_ORIGIN": origin, "DMB_BENCHMARK_BROWSER_TOKEN": token,
                        "DMB_BENCHMARK_DOCUMENT_ID": work["object_id"], "DMB_BENCHMARK_WORLD": world,
                        "DMB_BENCHMARK_QUESTION": case["question"], "DMB_BENCHMARK_PANE_SETTLED": "1" if settled else "0",
                        "DMB_BENCHMARK_SURFACE": "build" if build_fixture else "plan",
                        "DMB_BENCHMARK_LIVE_BROWSER": "1" if live else "0",
                        "DMB_BENCHMARK_UNSENT_DRAFT": "1" if unsent_draft else "0",
                        "DMB_BENCHMARK_CONFIRM_SAVE": "1" if confirm_save else "0",
                        "DMB_BENCHMARK_LOSE_CONFIRM_ACK": "1" if lose_confirm_ack else "0",
                        "DMB_BENCHMARK_DOCUMENT_START": "1" if at_document_start else "0",
                        "DMB_BENCHMARK_SELECTION": manifest["browser_capture"].get("selection_text", "") if build_fixture or live_plan else "",
                        "DMB_BENCHMARK_BROWSER_RESULT": str(output / "browser-timing.json"),
                        "DMB_BENCHMARK_PLAYWRIGHT": os.environ["DMB_BENCHMARK_PLAYWRIGHT"],
                        "DMB_BENCHMARK_CHROMIUM": os.environ["DMB_BENCHMARK_CHROMIUM"],
                    }
                    if live or unsent_draft:
                        page_route = "/api/live/workspace-documents/" + work["object_id"]
                        page_route += "/committed-revision" if live_plan else "/snapshot"
                        page_params = {} if live_plan else {"view": "committed"}
                        page_before = workflow.response_envelope(
                            client.get(page_route, params=page_params).raise_for_status())
                        artifacts.immutable_save(directory, "committed-page-before", page_before)
                        if live_plan:
                            require_plan_fixture_basis(page_before["body"], world, work,
                                                       manifest["browser_capture"].get("selection_text"))
                    driver = Path(__file__).with_name("browser_send.cjs")
                    artifacts.immutable_save(directory, "dispatch", {"state": "dispatching", "automatic_restart": False})
                    try:
                        run = subprocess.run([os.environ["DMB_BENCHMARK_NODE"], str(driver)], env=env,
                                             timeout=140 if lose_confirm_ack else 100)
                        driver_status = {"return_code": run.returncode}
                    except subprocess.TimeoutExpired:
                        driver_status = {"timed_out": True}
                    driver_failed = driver_status != {"return_code": 0}
                    if driver_failed:
                        artifacts.immutable_save(directory, "browser-driver-failure", driver_status)
                    if unsent_draft:
                        timing_path = output / "browser-timing.json"
                        observation = json.loads(timing_path.read_bytes()) if timing_path.is_file() else {}
                        after = client.get(route).raise_for_status().json()
                        page_after = workflow.response_envelope(
                            client.get(page_route, params=page_params).raise_for_status())
                        artifacts.immutable_save(directory, "history-before", fresh)
                        artifacts.immutable_save(directory, "history-after", after)
                        artifacts.immutable_save(directory, "committed-page-after", page_after)
                        draft = observation.get("draft_restore", {})
                        artifacts.immutable_save(directory, "fixture-result", {
                            "status": "incomplete" if driver_failed or not draft else "observed",
                            "draft_restored": draft.get("restored"),
                            "browser_turn_posts": draft.get("attemptedTurnPosts"),
                            "server_turn_posts": turn_posts,
                            "conversation_unchanged": after == fresh,
                            "committed_page_unchanged": page_after["body"] == page_before["body"],
                            "provider_calls": 0,
                        })
                        return
                    if browser_request is None or (driver_failed and not live):
                        raise ValueError("Ordinary browser Send did not capture the expected request")
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
                    def read_history():
                        return workflow.response_envelope(
                            client.get(route, params={"include_turn_correlation": "true"}).raise_for_status())

                    after = read_history()
                    turns = workflow._request_turns(after["body"], browser_request, world, browser_plan=live_plan)
                    if live:
                        deadline = monotonic_ns() + 60_000_000_000
                        while monotonic_ns() < deadline and (not turns or (
                                len(turns) == 1 and turns[0]["lifecycle_status"] in {"accepted", "running"})):
                            sleep(0.5)
                            after = read_history()
                            turns = workflow._request_turns(after["body"], browser_request, world, browser_plan=live_plan)
                    artifacts.immutable_save(directory, "history-after", after)
                    if live:
                        if confirm_save:
                            timing_path = output / "browser-timing.json"
                            timing = json.loads(timing_path.read_bytes()) if timing_path.is_file() else {}
                            confirmation = timing.get("confirmation") or {"status": "unknown"}
                            action_id = confirmation.get("action_id")
                            if action_id is not None:
                                action_id = str(UUID(action_id))
                                review_route = ("/api/live/agent/worlds/" + world +
                                                "/build-proposals/" + action_id + "/review")
                                review_after = client.get(review_route)
                                artifacts.immutable_save(directory, "proposal-review-after",
                                                         workflow.response_envelope(review_after))
                            artifacts.immutable_save(directory, "confirmation", confirmation)
                        page_after = workflow.response_envelope(
                            client.get(page_route, params=page_params).raise_for_status())
                        artifacts.immutable_save(directory, "committed-page-after", page_after)
                        matched_turn = turns[0] if len(turns) == 1 else None
                        lifecycle = matched_turn["lifecycle_status"] if matched_turn is not None else None
                        artifacts.immutable_save(directory, "committed-page-comparison", {
                            "document_id": work["object_id"],
                            "durable_turn_id": matched_turn["turn_id"] if matched_turn is not None else None,
                            "lifecycle_status": lifecycle,
                            "readback_scope": ("through_terminal_turn" if lifecycle in
                                               {"completed", "failed", "interrupted"} else "observed_interval"),
                            "before_sha256": page_before["raw_body_sha256"],
                            "after_sha256": page_after["raw_body_sha256"],
                            "unchanged": page_before["body"] == page_after["body"],
                        })
                    if live and len(turns) == 1:
                        durable_id = turns[0]["turn_id"]
                        trace = client.get(route + "/turns/" + durable_id + "/context-trace")
                        artifacts.immutable_save(directory, "context-trace", workflow.response_envelope(trace))
                    if live:
                        wire_path = directory / (wire_name + ".json")
                        if not wire_path.is_file():
                            raise ValueError("Ordinary browser transport has no retained response")
                        wire_response = json.loads(wire_path.read_bytes())
                        wire_bytes = bytes.fromhex(wire_response["raw_body_hex"])
                        try:
                            body, status = build_browser_terminal(
                                wire_bytes, wire_response["status"], wire_response["content_type"],
                                browser_request["turn_id"])
                        except BuildStreamWithoutTerminal:
                            if (wire_response.get("client_disconnect_ms") is None or len(turns) != 1
                                    or turns[0]["lifecycle_status"] in {"accepted", "running"}):
                                raise
                            return
                        raw = json.dumps(body).encode("utf-8")
                        artifacts.immutable_save(directory, "answer-http", {
                            "body": body, "http_status": status, "transport_status": wire_response["status"],
                            "raw_body_hex": raw.hex(), "raw_body_sha256": sha256(raw).hexdigest(),
                            "elapsed_ms": wire_response["elapsed_ms"],
                        })
                    if live and status == 200 and len(turns) == 1:
                        workflow.retain_citation_readbacks(client, directory, route, world, turns[0]["turn_id"], body)
                    if live_plan and not turns and status >= 400:
                        return
                    if len(turns) != 1:
                        raise ValueError("Browser request has no unique retained Turn")
                    from application_state.agent_conversation import AgentConversationService
                    turn_id = turns[0]["turn_id"]
                    observed = AgentConversationService().inspect_turn(world_id=world, turn_id=UUID(turn_id))
                    if len(replayed) != len(wire):
                        raise ValueError("Ordinary browser turn did not consume its entire Jev tape")
                    if not live:
                        sink.finalize(observed)
                    if not live:
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


class BuildStreamWithoutTerminal(ValueError):
    """A valid stream ended before a terminal event arrived."""


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
    raise BuildStreamWithoutTerminal("Build event stream has no terminal result or error")


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


def validate_plan_browser_placement(request, *, world, work, question, conversation_id, pointer_revision, selection_text=None, at_document_start=False):
    """Bind an observed Plan placement request to the pinned work and fresh conversation."""
    from apps.live_control_server.models.agent_turn import AgentTurnRequest

    parsed = AgentTurnRequest.model_validate(request)
    if (parsed.surface.surface_id != "plan" or parsed.owner_scope is None
            or parsed.owner_scope.world_id != world or parsed.primary_work is None
            or parsed.primary_work.model_dump(mode="json", exclude_none=True) != work
            or parsed.message != question):
        raise ValueError("Plan browser request differs from the pinned fixture")
    capture = parsed.plan_authoring_capture
    if capture is None or parsed.plan_placement_catalog is None:
        raise ValueError("Plan browser request lacks a captured placement")
    if (str(capture.conversation_id) != str(conversation_id)
            or capture.expected_pointer_revision != pointer_revision):
        raise ValueError("Plan browser placement differs from the current conversation")
    if selection_text is not None:
        witness = getattr(capture, "selection_witness_text", capture.selected_text)
        if witness != selection_text:
            raise ValueError("Plan browser selection differs from the pinned passage")
    if at_document_start and ((capture.from_, capture.to) != (1, 1)
                              or capture.draft_sha256 != work["expected_content_sha256"]):
        raise ValueError("Plan fixture requires a document-start caret in the committed text")
    return parsed



def require_plan_history(history, expected):
    """Reject stale or extra turns before dispatch into a restored conversation."""
    def digest(value):
        return sha256(value.encode("utf-8")).hexdigest()

    observed = [
        {"turn_id": turn["turn_id"], "sequence": turn["sequence"],
         "user_text_sha256": digest(turn["user_text"]),
         "assistant_text_sha256": digest(turn["assistant_text"])}
        for turn in history["turns"] if turn["lifecycle_status"] == "completed"
    ]
    if (history["active_conversation_id"] != expected["conversation_id"]
            or not observed or len(observed) != len(history["turns"])
            or observed != expected["prior_turns"]):
        raise ValueError("Active conversation differs from the pinned Plan history")


def require_plan_fixture_basis(committed, world, work, selection):
    """Require the same active committed Plan basis that the ordinary composer uses."""
    expected = {
        "schema_version": "dmb_workspace_committed_revision_v2",
        "scope_mode": "world",
        "campaign_id": None,
        "world_id": world,
        "document_id": work["object_id"],
        "kind": "plan",
        "status": "active",
        "object_revision": work["expected_revision"],
        "revision_n": work["expected_revision_n"],
        "content_sha256": work["expected_content_sha256"],
    }
    if any(key not in committed or committed[key] != value for key, value in expected.items()):
        raise ValueError("Plan fixture is not the pinned active committed Plan")
    if selection is not None and committed["markdown"].count(selection) != 1:
        raise ValueError("Plan fixture selection is absent or ambiguous in the committed Plan")

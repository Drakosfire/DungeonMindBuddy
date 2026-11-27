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
    image_preview = spec.get("image_preview", False)
    if type(image_preview) is not bool or (image_preview and (
            not build_fixture or live_plan or any(
                key in spec for key in ("selection_text", "unsent_draft", "confirm_save", "lose_confirm_ack"))
    )):
        raise ValueError("Image preview requires a Build fixture without selection, draft or confirmation")
    parent = spec.get("image_parent")
    if "image_parent" in spec and (
            not image_preview or not isinstance(parent, dict)
            or set(parent) != {"asset_id", "content_sha256"}
            or not isinstance(parent["asset_id"], str)
            or str(UUID(parent["asset_id"])) != parent["asset_id"]
            or not isinstance(parent["content_sha256"], str)
            or len(parent["content_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in parent["content_sha256"])):
        raise ValueError("Image regeneration requires an exact parent asset and digest")
    placement = spec.get("image_placement_anchor")
    if "image_placement_anchor" in spec and (
            parent is None or not isinstance(placement, str) or not placement.strip()):
        raise ValueError("Image placement requires an exact parent and destination paragraph")
    if "image_lose_save_ack" in spec and (
            spec["image_lose_save_ack"] is not True or placement is None or parent is None):
        raise ValueError("Lost image Save acknowledgement requires exact placement and asset pins")
    unsent_draft = spec.get("unsent_draft", False)
    if type(unsent_draft) is not bool or (unsent_draft and (not build_fixture or live_plan)):
        raise ValueError("Unsent draft requires a Build browser fixture")
    play_choice = spec.get("play_choice")
    if "play_choice" in spec:
        from .play_choice import validate_play_choice
        validate_play_choice(play_choice)
    wire = [] if build_fixture or live_plan or play_choice else json.loads(workflow.read_pin(spec["jev_wire"], base))
    if not (build_fixture or live_plan or play_choice) and (not wire or any(
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
    work_plan = spec.get("reviewed_work_plan")
    if work_plan is not None and (
            not build_fixture or live_plan or not isinstance(work_plan, dict)
            or set(work_plan) != {"conversation_id", "source_turn_id", "step_id", "revision", "objective"}
            or any(str(UUID(work_plan[k])) != work_plan[k]
                   for k in ("conversation_id", "source_turn_id", "step_id"))
            or type(work_plan["revision"]) is not int or work_plan["revision"] < 1
            or not isinstance(work_plan["objective"], str) or not work_plan["objective"].strip()
            or any(key in spec for key in ("image_preview", "selection_text", "confirm_save", "unsent_draft"))):
        raise ValueError("Reviewed continuation requires an exact standalone Build fixture")
    if work_plan is None and not image_preview and not unsent_draft and not caret and (build_fixture or live_plan) and (
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


def require_image_preview_page(snapshot, world, work):
    record = snapshot.get("record") or {}
    if (record.get("world_id"), record.get("document_id"), record.get("revision"),
            snapshot.get("loaded_revision"), snapshot.get("committed_content_sha256")) != (
            world, work["object_id"], work["expected_revision"], work["expected_revision"],
            work["expected_content_sha256"]):
        raise ValueError("Image preview does not target the pinned committed Build page")


def read_image_parent(client, parent):
    """Retain parent metadata and original-byte digest even for negative readbacks."""
    route = "/api/live/media/images/" + parent["asset_id"]
    metadata = workflow.response_envelope(client.get(route + "/metadata"))
    original = client.get(route + "/original")
    digest = sha256(original.content).hexdigest()
    body = metadata["body"] if isinstance(metadata["body"], dict) else {}
    return {
        "metadata": metadata,
        "original_http_status": original.status_code,
        "original_sha256": digest,
        "matches_pin": (
            metadata["http_status"] == 200 and original.status_code == 200
            and body.get("asset_id") == parent["asset_id"]
            and body.get("state") in {"ready", "staged"}
            and body.get("content_sha256") == digest == parent["content_sha256"]),
    }


@contextmanager
def isolated_image_storage(asset_id, calls):
    """Exercise the media owner and fence with a deterministic CDN response."""
    from application_state import media
    from apps.live_control_server.services import media_storage

    save_asset = media_storage.save_asset
    account = "0" * 32
    upload_url = f"https://api.cloudflare.com/client/v4/accounts/{account}/images/v1"

    async def save(candidate, owner, **kwargs):
        if str(candidate) != asset_id or owner != "local_operator" or calls:
            raise ValueError("Unexpected benchmark media Save")
        row = media.get_asset(candidate, owner)
        object_id = media_storage._object_id(row)
        metadata = media_storage._metadata(row)
        result = {"success": True, "result": {"id": object_id, "meta": metadata,
                  "requireSignedURLs": False,
                  "variants": [f"https://imagedelivery.net/benchmark/{object_id}/public"]}}

        def respond(request):
            calls.append(request.method)
            if calls == ["GET"] and str(request.url) == f"{upload_url}/{object_id}":
                return httpx.Response(404)
            if calls == ["GET", "POST"] and str(request.url) == upload_url:
                return httpx.Response(200, json=result)
            if calls == ["GET", "POST", "GET"] and str(request.url) == f"{upload_url}/{object_id}":
                return httpx.Response(200, json=result)
            raise ValueError("Unexpected benchmark CDN request")

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await save_asset(candidate, owner, client=client, **kwargs)

    with patch.dict(os.environ, {"CLOUDFLARE_ACCOUNT_ID": account,
                                "CLOUDFLARE_IMAGES_API_TOKEN": "benchmark-only"}):
        with patch.object(media_storage, "save_asset", save):
            yield


def saved_image_library(client, world):
    """Read all saved assets through the media owner, even when staging shifts a page."""
    cursor = {}
    seen = set()
    saved = []
    while True:
        items = client.get("/api/live/media/images/library", params={"world_id": world, **cursor}).raise_for_status().json()["items"]
        if not items:
            return saved
        saved.extend(item for item in items if item["state"] == "ready")
        last = items[-1]
        boundary = (last["created_at"], last["asset_id"])
        if boundary in seen:
            raise ValueError("Media library pagination did not advance")
        seen.add(boundary)
        cursor = {"before_time": boundary[0], "before_id": boundary[1]}


def browser_capture(application, manifest, case, output, token, inputs, owned_env, *, detail, build_fixture=False, live_build=False, live_plan=False):
    from apps.live_control_server.hosted_worker import with_startup_gc
    from apps.live_control_server.services import plan_jev_dispatch
    import httpx2

    if (os.environ.get("DMB_DEPLOYMENT_ENVIRONMENT"), os.environ.get("DMB_AUTH_MODE"),
            os.environ.get("DMB_AGENT_GRAPH_AUTH_MODE"), os.environ.get("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT")) != (
            "local", "local_operator", "local_operator", "local"):
        raise ValueError("Browser capture requires explicit local operator auth")
    image_preview = manifest["browser_capture"].get("image_preview", False)
    image_parent = manifest["browser_capture"].get("image_parent")
    image_placement = manifest["browser_capture"].get("image_placement_anchor")
    image_lose_save_ack = manifest["browser_capture"].get("image_lose_save_ack", False)
    if image_preview and not live_build:
        raise ValueError("Image preview requires explicit live Build capture")
    live = live_build or live_plan
    reviewed_plan = manifest["browser_capture"].get("reviewed_work_plan")
    if reviewed_plan is not None and not live_build:
        raise ValueError("Reviewed continuation requires live Build capture")
    play_choice = manifest["browser_capture"].get("play_choice")
    play_rejected_writes = []
    wire_name = "plan-wire-response" if live_plan else "build-wire-response"
    confirm_save = manifest["browser_capture"].get("confirm_save", False)
    lose_confirm_ack = manifest["browser_capture"].get("lose_confirm_ack", False)
    if type(lose_confirm_ack) is not bool or (lose_confirm_ack and (not live_build or confirm_save is not True)):
        raise ValueError("Lost acknowledgement requires live Build confirmation")

    terminal_build_failure = manifest["browser_capture"].get("terminal_build_failure", False)
    if type(terminal_build_failure) is not bool or (terminal_build_failure and (
            not live_build or confirm_save or lose_confirm_ack or image_preview)):
        raise ValueError("Terminal failure requires an ordinary Build proposal without Save")
    failed_proposals = []

    unsent_draft = manifest["browser_capture"].get("unsent_draft", False)
    if unsent_draft and (live or confirm_save or not build_fixture):
        raise ValueError("Unsent draft requires provider-free Build capture")
    turn_posts = 0
    image_generation_posts = 0
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
    if reviewed_plan is not None:
        work = prepare_reviewed_work_plan_page(world, work, reviewed_plan, directory)
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
        nonlocal browser_request, turn_posts, image_generation_posts
        if scope["type"] != "http":
            return await application(scope, receive, send)
        path, method = scope["path"], scope["method"]
        if play_choice and (method, path) in {
            ("PUT", "/api/live/world-play-runs/v2/active"),
            ("POST", "/api/live/native-graph-explorer/graph"),
        }:
            from urllib.parse import parse_qs

            frames = []
            while True:
                frame = await receive()
                if frame["type"] != "http.request":
                    return
                frames.append(frame)
                if not frame.get("more_body"):
                    break
            try:
                payload = json.loads(b"".join(frame["body"] for frame in frames))
            except (ValueError, UnicodeError):
                payload = None
            if method == "PUT":
                valid = (parse_qs(scope["query_string"].decode(), keep_blank_values=True) == {"world_id": [world]}
                         and payload == {"run_id": play_choice["run_id"]})
            else:
                valid = isinstance(payload, dict) and payload.get("managed_world_id") == world
            if not valid:
                play_rejected_writes.append({"method": method, "path": path, "reason": "wrong_play_navigation_scope"})
                return await JSONResponse({"code": "benchmark_wrong_play_navigation_scope"}, 409)(scope, receive, send)
            saved_frames = iter(frames)

            async def replay_navigation_body():
                return next(saved_frames, None) or await receive()

            return await application(scope, replay_navigation_body, send)
        if play_choice and method not in {"GET", "HEAD"} and path.startswith("/api/") and (method, path) not in {
            ("POST", "/api/live/agent/turn"),
            ("POST", "/api/live/agent/local-session"),
            ("PUT", "/api/live/world-play-runs/v2/" + play_choice["run_id"] + "/progress"),
        }:
            play_rejected_writes.append({"method": method, "path": path})
            return await JSONResponse({"code": "benchmark_unexpected_play_write"}, 409)(scope, receive, send)
        if (image_lose_save_ack and method == "POST" and path.startswith("/api/live/media/images/")
                and path.endswith("/save") and path != f"/api/live/media/images/{image_parent['asset_id']}/save"):
            return await JSONResponse({"code": "benchmark_wrong_image_save_target"}, 409)(scope, receive, send)
        if (image_placement is not None and method == "POST"
                and path.startswith("/api/live/media/images/")
                and path.rsplit("/", 1)[-1] in {"generate", "regenerate"}):
            image_generation_posts += 1
            return await JSONResponse({"code": "benchmark_unexpected_image_generation"}, 409)(scope, receive, send)
        if live and path == "/__benchmark/browser-response-retained" and method == "GET":
            wire_path = directory / (wire_name + ".json")
            result = {"retained": wire_path.is_file()}
            if (confirm_save or terminal_build_failure) and result["retained"] and browser_request is not None:
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
            turn_posts += 1
            if unsent_draft or image_preview or play_choice:
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
                    if reviewed_plan is not None:
                        from application_state.agent_conversation import work_plan
                        owner = work_plan.read(world, UUID(reviewed_plan["conversation_id"]),
                                               UUID(reviewed_plan["source_turn_id"]))["plan"]
                        validate_reviewed_work_plan_request(parsed, reviewed_plan, owner, work, fresh)
                        artifacts.immutable_save(directory, "reviewed-work-plan-at-dispatch", owner)
                    else:
                        validate_build_browser_request(parsed, world=world, work=work, question=case["question"],
                            selection_text=manifest["browser_capture"]["selection_text"],
                            conversation_id=fresh["active_conversation_id"], pointer_revision=fresh["pointer_revision"])
                except (ValueError, KeyError):
                    if reviewed_plan is not None:
                        artifacts.immutable_save(directory, "rejected-browser-request", parsed)
                        return await JSONResponse({"error": "Reviewed Work Plan request did not match"}, 409,
                            headers={"X-Benchmark-Review-Rejected": "1"})(scope, receive, send)
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
    failure_guard = nullcontext()
    if terminal_build_failure:
        from apps.live_control_server.services.build_document_proposal import BuildComposeError, BuildProposalService
        owner_advance = BuildProposalService.advance

        def stop_after_response(service, world_id, action_id, *, expected_revision, state, **fields):
            if world_id == world and state == "proposed":
                failed_proposals.append(action_id)
                raise BuildComposeError("benchmark_known_failure_after_writer_response")
            return owner_advance(service, world_id, action_id, expected_revision=expected_revision, state=state, **fields)

        failure_guard = patch.object(BuildProposalService, "advance", stop_after_response)

    image_storage_calls = []
    storage_guard = (isolated_image_storage(image_parent["asset_id"], image_storage_calls)
                     if image_lose_save_ack else nullcontext())
    try:
        with patch.dict(os.environ, local_env), jev_guard, writer_guard, failure_guard, storage_guard:
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
                    if reviewed_plan is not None:
                        if fresh["active_conversation_id"] != reviewed_plan["conversation_id"]:
                            command = {"world_id": world, "command_id": str(uuid4()),
                                "expected_pointer_revision": fresh["pointer_revision"],
                                "expected_active_conversation_id": fresh["active_conversation_id"],
                                "conversation_id": reviewed_plan["conversation_id"]}
                            client.post(f"/api/live/agent/worlds/{world}/conversations/{reviewed_plan['conversation_id']}/resume",
                                        json=command).raise_for_status()
                            fresh = client.get(route).raise_for_status().json()
                        if fresh["active_conversation_id"] != reviewed_plan["conversation_id"]:
                            raise ValueError("Reviewed Work Plan conversation did not reopen")
                        artifacts.immutable_save(directory, "history-before", fresh)
                    elif image_preview or play_choice:
                        artifacts.immutable_save(directory, "history-before", fresh)
                    elif pinned_history is None:
                        command = {"schema": "dmb_agent_new_conversation_v1", "command_id": str(uuid4()),
                            "expected_pointer_revision": fresh["pointer_revision"],
                            "expected_active_conversation_id": fresh["active_conversation_id"]}
                        client.post(route + "/new", json=command).raise_for_status()
                        fresh = client.get(route).raise_for_status().json()
                        if fresh["turns"]:
                            raise ValueError("Browser fixture conversation was not empty")
                    else:
                        artifacts.immutable_save(directory, "history-before", fresh)
                        workflow.require_pinned_history(fresh, pinned_history)
                    runtime = output / "runtime-artifacts"
                    env = {
                        "PATH": os.defpath, "HOME": str(runtime), "TMPDIR": str(scratch),
                        "DMB_BENCHMARK_BROWSER_ORIGIN": origin, "DMB_BENCHMARK_BROWSER_TOKEN": token,
                        "DMB_BENCHMARK_DOCUMENT_ID": work["object_id"], "DMB_BENCHMARK_WORLD": world,
                        "DMB_BENCHMARK_QUESTION": case["question"], "DMB_BENCHMARK_PANE_SETTLED": "1" if settled else "0",
                        "DMB_BENCHMARK_SURFACE": "build" if build_fixture else "plan",
                        "DMB_BENCHMARK_LIVE_BROWSER": "1" if live else "0",
                        "DMB_BENCHMARK_IMAGE_PREVIEW": "1" if image_preview else "0",
                        "DMB_BENCHMARK_REVIEWED_WORK_PLAN": json.dumps(reviewed_plan),
                        "DMB_BENCHMARK_UNSENT_DRAFT": "1" if unsent_draft else "0",
                        "DMB_BENCHMARK_CONFIRM_SAVE": "1" if confirm_save else "0",
                        "DMB_BENCHMARK_LOSE_CONFIRM_ACK": "1" if lose_confirm_ack else "0",
                        "DMB_BENCHMARK_TERMINAL_BUILD_FAILURE": "1" if terminal_build_failure else "0",
                        "DMB_BENCHMARK_DOCUMENT_START": "1" if at_document_start else "0",
                        "DMB_BENCHMARK_SELECTION": manifest["browser_capture"].get("selection_text", "") if build_fixture or live_plan else "",
                        "DMB_BENCHMARK_BROWSER_RESULT": str(output / "browser-timing.json"),
                        "DMB_BENCHMARK_PLAYWRIGHT": os.environ["DMB_BENCHMARK_PLAYWRIGHT"],
                        "DMB_BENCHMARK_CHROMIUM": os.environ["DMB_BENCHMARK_CHROMIUM"],
                    }
                    if play_choice:
                        from .play_choice import read_choice_state, record_choice_result
                        choice_before = read_choice_state(client, directory, "play-choice-before", world, play_choice, template)
                        run, plan, active_run = choice_before
                        if (run["world_id"] != world or run["run_id"] != play_choice["run_id"]
                                or run["run_revision"] != play_choice["revision"]
                                or run["lifecycle_status"] != "active"
                                or active_run["run_id"] != play_choice["run_id"]
                                or run["progress"]["current_scene_id"] != play_choice["scene_id"]
                                or run["playable_artifact_id"] != work["object_id"]
                                or plan["sha256"] != work["expected_content_sha256"]
                                or plan["object"]["object_revision"] != work["expected_revision"]
                                or run["progress"]["selections"].get(play_choice["choice_id"]) == play_choice["option_id"]):
                            raise ValueError("Play Choice fixture differs from the pinned Run and saved Plan")
                        run_route = "/api/live/world-play-runs/v2/" + play_choice["run_id"]
                        reference = client.get(run_route + "/reference-manifest", params={"world_id": world}).raise_for_status().json()
                        choice = play_choice["choice_id"]
                        if (not any(row["choice_id"] == choice and row["scene_id"] == play_choice["scene_id"]
                                    for row in reference["choices"])
                                or not any(row["choice_id"] == choice and row["option_id"] == play_choice["option_id"]
                                           for row in reference["options"])):
                            raise ValueError("Play Choice or option is absent from the pinned scene")
                        artifacts.immutable_save(directory, "play-choice-reference", reference)
                        env["DMB_BENCHMARK_PLAY_CHOICE"] = json.dumps(play_choice)
                    if live or unsent_draft:
                        page_route = "/api/live/workspace-documents/" + work["object_id"]
                        page_route += "/committed-revision" if live_plan else "/snapshot"
                        page_params = {} if live_plan else {"view": "committed"}
                        page_before = workflow.response_envelope(
                            client.get(page_route, params=page_params).raise_for_status())
                        artifacts.immutable_save(directory, "committed-page-before", page_before)
                        if live_plan:
                            require_plan_fixture_basis(page_before["body"], world, work,
                                                       manifest["browser_capture"].get("selection_text"),
                                                       require_clean=at_document_start)
                    if image_preview:
                        require_image_preview_page(page_before["body"], world, work)
                        env["DMB_BENCHMARK_IMAGE_PAGE_PIN"] = json.dumps(work)
                        library_before = saved_image_library(client, world)
                        artifacts.immutable_save(directory, "image-library-before", library_before)
                        if image_parent is not None:
                            parent_before = read_image_parent(client, image_parent)
                            artifacts.immutable_save(directory, "image-parent-before", parent_before)
                            if not parent_before["matches_pin"]:
                                raise ValueError("Selected image parent differs from the pinned original")
                            env["DMB_BENCHMARK_IMAGE_PARENT"] = json.dumps(image_parent)
                        if image_placement is not None:
                            markdown = page_before["body"]["committed_markdown"]
                            if (markdown.count(image_placement) != 1
                                    or f"dmb-media:{image_parent['asset_id']}" in markdown):
                                raise ValueError("Image placement needs one unique paragraph and an absent asset")
                            expected_state = "staged" if image_lose_save_ack else "ready"
                            if parent_before["metadata"]["body"]["state"] != expected_state:
                                raise ValueError(f"Image placement requires a {expected_state} library asset")
                            env["DMB_BENCHMARK_IMAGE_PLACEMENT"] = json.dumps({
                                "anchor": image_placement, "lose_save_ack": image_lose_save_ack,
                            })

                    driver = Path(__file__).with_name("browser_send.cjs")
                    artifacts.immutable_save(directory, "dispatch", {"state": "dispatching", "automatic_restart": False})
                    try:
                        run = subprocess.run([os.environ["DMB_BENCHMARK_NODE"], str(driver)], env=env,
                                             timeout=205 if image_preview else 140 if lose_confirm_ack else 100)
                        driver_status = {"return_code": run.returncode}
                    except subprocess.TimeoutExpired:
                        driver_status = {"timed_out": True}
                    driver_failed = driver_status != {"return_code": 0}
                    if driver_failed:
                        artifacts.immutable_save(directory, "browser-driver-failure", driver_status)
                    if play_choice:
                        choice_after = read_choice_state(client, directory, "play-choice-after", world, play_choice, template)
                        record_choice_result(directory, output, choice_before, choice_after, play_choice, driver_failed, turn_posts,
                                             play_rejected_writes)
                        return
                    if image_preview:
                        timing_path = output / "browser-timing.json"
                        observation = json.loads(timing_path.read_bytes()) if timing_path.is_file() else {}
                        page_after = workflow.response_envelope(
                            client.get(page_route, params=page_params).raise_for_status())
                        library_after = saved_image_library(client, world)
                        after = client.get(route).raise_for_status().json()
                        artifacts.immutable_save(directory, "committed-page-after", page_after)
                        artifacts.immutable_save(directory, "image-library-after", library_after)
                        artifacts.immutable_save(directory, "history-after", after)
                        preview = observation.get("preview")
                        owner_asset = None
                        if preview:
                            asset_id = str(UUID(preview["asset"]["asset_id"]))
                            owner_asset = workflow.response_envelope(
                                client.get(f"/api/live/media/images/{asset_id}/metadata"))
                            artifacts.immutable_save(directory, "image-owner-readback", owner_asset)
                        if observation.get("mounted_page") is not None:
                            require_image_preview_page(observation["mounted_page"], world, work)
                        checks = {
                            "mounted_page_pinned": observation.get("mounted_page") is not None,
                            "private_staged_preview": bool(owner_asset and owner_asset["http_status"] == 200
                                and owner_asset["body"]["asset_id"] == asset_id
                                and owner_asset["body"]["state"] == "staged"
                                and owner_asset["body"]["content_sha256"] == preview["sha256"]
                                and not owner_asset["body"].get("delivery_url")),
                            "single_generation": observation.get("generation_posts") == 1,
                            "no_save_or_place_request": observation.get("write_requests") == [],
                            "saved_library_unchanged": library_before == library_after,
                            "committed_page_unchanged": page_after["body"] == page_before["body"],
                            "mounted_editor_unchanged": observation.get("editor_unchanged") is True,
                            "conversation_unchanged": after == fresh and turn_posts == 0
                                and observation.get("turn_posts") == 0,
                        }
                        if image_parent is not None:
                            parent_after = read_image_parent(client, image_parent)
                            artifacts.immutable_save(directory, "image-parent-after", parent_after)
                            child = (owner_asset or {}).get("body") or {}
                            provenance = child.get("provenance", {})
                            checks["parent_unchanged"] = (
                                parent_after["matches_pin"]
                                and parent_before["metadata"]["body"] == parent_after["metadata"]["body"])
                            checks["distinct_child_bound_to_parent"] = (
                                child.get("asset_id") not in (None, image_parent["asset_id"])
                                and provenance.get("parent_asset_id") == image_parent["asset_id"]
                                and provenance.get("parent_content_sha256") == image_parent["content_sha256"]
                                and provenance.get("mode") == "image_to_image"
                                and provenance.get("instructions") == case["question"])
                        if image_placement is not None:
                            placed = observation.get("placement") or {}
                            saved = page_after["body"]
                            prior = page_before["body"]["committed_markdown"]
                            expected = prior.replace(image_placement,
                                image_placement + f"\n\n![Saved artwork](dmb-media:{image_parent['asset_id']})", 1)
                            for key in ("private_staged_preview", "single_generation", "no_save_or_place_request",
                                        "committed_page_unchanged", "mounted_editor_unchanged",
                                        "distinct_child_bound_to_parent"):
                                checks.pop(key)
                            checks.update(
                                zero_generation=observation.get("generation_posts") == 0 and image_generation_posts == 0,
                                no_media_save=isinstance(observation.get("write_requests"), list)
                                    and all(row["path"].startswith("/api/live/workspace-documents/")
                                            for row in observation["write_requests"]),
                                single_document_commit=observation.get("document_commit_posts") == 1,
                                mounted_reopen_exact=placed.get("mounted_reopened_exact") is True,
                                exact_saved_image=saved["committed_markdown"] == expected
                                    and saved["loaded_revision"] == work["expected_revision"] + 1,
                            )
                        if image_lose_save_ack:
                            recovery = observation.get("save_recovery") or {}
                            saves = [row for row in observation.get("write_requests", [])
                                     if row["path"].endswith("/save")]
                            checks.pop("no_media_save")
                            checks.pop("parent_unchanged")
                            checks.pop("saved_library_unchanged")
                            newly_saved = [row for row in library_after
                                           if row["asset_id"] == image_parent["asset_id"]]
                            checks["only_pinned_asset_added_to_saved_library"] = (
                                len(newly_saved) == 1
                                and newly_saved[0]["content_sha256"] == image_parent["content_sha256"]
                                and [row for row in library_after if row not in newly_saved] == library_before)
                            observation["synthetic_cdn_calls"] = image_storage_calls
                            checks["exact_asset_save_recovered"] = (
                                image_storage_calls == ["GET", "POST", "GET"]
                                and saves == [{"method": "POST", "path":
                                          f"/api/live/media/images/{image_parent['asset_id']}/save"}]
                                and recovery.get("asset_id") == image_parent["asset_id"]
                                and recovery.get("save_attempts") == 1
                                and recovery.get("committed_status") == 200
                                and recovery.get("recovered_state") == "ready"
                                and parent_after["matches_pin"]
                                and parent_after["metadata"]["body"]["state"] == "ready")
                        artifacts.immutable_save(directory, "fixture-result", {
                            "status": "observed" if not driver_failed and all(checks.values()) else "incomplete",
                            "checks": checks, "image_preview": observation,
                        })
                        return
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
                    if reviewed_plan is not None:
                        from application_state.agent_conversation import work_plan
                        try:
                            result = work_plan.read(
                                world, UUID(reviewed_plan["conversation_id"]), UUID(reviewed_plan["source_turn_id"]))
                        except Exception as error:
                            result = {"status": "readback_error", "error_type": type(error).__name__}
                        artifacts.immutable_save(directory, "reviewed-work-plan-after", result)
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
                    if terminal_build_failure:
                        timing_path = output / "browser-timing.json"
                        mounted = (json.loads(timing_path.read_bytes()).get("terminal_build_failure")
                                   if timing_path.is_file() else None)
                        proposal = (BuildProposalService().get(world, failed_proposals[0])
                                    if len(failed_proposals) == 1 else None)
                        row = turns[0] if len(turns) == 1 else {}
                        checks = {
                            "known_terminal_proposal": (proposal is not None and proposal.state == "failed"
                                and proposal.raw_response is not None and proposal.proposal is None
                                and str(proposal.action_id) == browser_request["build_write_capability"]["idempotency_key"]),
                            "same_terminal_turn": bool(mounted and row.get("turn_id") == mounted.get("turn_id")
                                and row.get("lifecycle_status") in {"failed", "interrupted"}),
                            "no_automatic_send": bool(mounted and mounted.get("turn_posts") == turn_posts == 1),
                            "page_unchanged": page_before["body"] == page_after["body"],
                        }
                        artifacts.immutable_save(directory, "terminal-build-failure", {
                            "status": "observed" if not driver_failed and all(checks.values()) else "incomplete",
                            "checks": checks, "mounted": mounted,
                            "owner_failure": proposal.failure_code if proposal is not None else None,
                        })
                    if live and len(turns) == 1:
                        durable_id = turns[0]["turn_id"]
                        trace = client.get(route + "/turns/" + durable_id + "/context-trace")
                        artifacts.immutable_save(directory, "context-trace", workflow.response_envelope(trace))
                        if live_build:
                            readback = build_proposal_readback(browser_request, world, turns[0])
                            if readback is not None:
                                artifacts.immutable_save(directory, "build-proposal-readback", readback)
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


def build_proposal_readback(request, world, turn):
    """Read the exact Build proposal before its isolated App is removed."""
    from application_state.build_proposal.service import BuildProposalService
    from application_state.build_proposal.types import BuildProposalBasis
    from application_state.errors import ApplicationStateNotFoundError

    capability = request.get("build_write_capability")
    if not capability or turn["lifecycle_status"] not in {"completed", "failed", "interrupted"}:
        return None
    action_id = UUID(capability["idempotency_key"])
    identity = {"action_id": str(action_id), "durable_turn_id": turn["turn_id"]}
    try:
        record = BuildProposalService().get(world, action_id)
    except ApplicationStateNotFoundError:
        return dict(identity, status="absent")
    except Exception as exc:
        return dict(identity, status="readback_error", error_type=type(exc).__name__)
    reservation = record.reservation
    origin = reservation.origin
    if (record.action_id != action_id
            or str(reservation.conversation_id) != capability["conversation_id"]
            or reservation.expected_pointer_revision != capability["expected_pointer_revision"]
            or reservation.basis.world_id != world
            or reservation.basis != BuildProposalBasis.model_validate(capability["basis"])
            or origin is None
            or str(origin.client_turn_id) != request["turn_id"]
            or str(origin.durable_turn_id) != turn["turn_id"]):
        return dict(identity, status="mismatched")
    return dict(identity, status="observed", state=record.state, revision=record.revision,
                inserted_in_draft=record.inserted_in_draft,
                proposal=record.proposal.model_dump(mode="json") if record.proposal is not None else None)


def prepare_reviewed_work_plan_page(world, work, fixture, directory):
    """Set up one saved card through the Page owner before measuring the browser turn."""
    from application_state.agent_conversation import work_plan
    from application_state.content import pages

    doc = work["object_id"]
    plan = work_plan.read(world, UUID(fixture["conversation_id"]), UUID(fixture["source_turn_id"]))["plan"]
    before = pages.committed_page(doc, world_id=world)
    revision = before.revision
    if (plan["document_id"] != doc or plan["revision"] != fixture["revision"]
            or revision is None or before.page.object_revision != work["expected_revision"]
            or revision.content_sha256 != work["expected_content_sha256"]
            or fixture["source_turn_id"] in revision.markdown):
        raise ValueError("Work Plan fixture page and source differ from their saved pins")
    reference = {"schema": "dmb_surface_work_plan_ref_v1", "world_id": world,
                 "document_id": doc, "conversation_id": fixture["conversation_id"],
                 "source_turn_id": fixture["source_turn_id"],
                 "source_answer_sha256": plan["source_answer_sha256"], "title": "Reviewed work plan"}
    artifacts.immutable_save(directory, "reviewed-work-plan-before", plan)
    markdown = revision.markdown.rstrip() + "\n\n```dmb-work-plan-v1\n" + json.dumps(reference) + "\n```\n"
    prepared_page, prepared = pages.commit_page(doc, markdown, world_id=world,
                                   expected_revision=before.page.object_revision,
                                   expected_working_copy_revision=before.working_copy_revision)
    artifacts.immutable_save(directory, "reviewed-work-plan-fixture-card", {
        "reference": reference, "before": revision.model_dump(mode="json"),
        "prepared": prepared.model_dump(mode="json"),
        "registry_revision_before": before.page.object_revision,
        "registry_revision_prepared": prepared_page.page.object_revision,
    })
    return {**work, "expected_revision": prepared_page.page.object_revision,
            "expected_content_sha256": prepared.content_sha256}


def validate_reviewed_work_plan_request(request, fixture, owner, work, history):
    """Accept the exact owner-reserved discussion from the mounted editor."""
    from apps.live_control_server.models.agent_turn import AgentTurnRequest

    parsed = AgentTurnRequest.model_validate(request)
    if (parsed.reviewed_step is None or parsed.build_draft_context is None
            or parsed.build_write_capability is not None or parsed.primary_work is None
            or parsed.primary_work.model_dump(mode="json", exclude_none=True) != work
            or parsed.owner_scope is None or parsed.owner_scope.world_id != owner["world_id"]
            or owner["document_id"] != work["object_id"]
            or owner["revision"] != fixture["revision"] + 2
            or owner["objective"] != fixture["objective"]):
        raise ValueError("Reviewed discussion differs from the pinned work and review")
    ref = parsed.reviewed_step.model_dump(mode="json")
    context = parsed.build_draft_context
    matches = [d for d in owner["dispatches"] if d["command_id"] == ref["command_id"]]
    if (len(matches) != 1 or ref["conversation_id"] != fixture["conversation_id"]
            or ref["source_turn_id"] != fixture["source_turn_id"]
            or str(context.conversation_id) != fixture["conversation_id"]
            or context.expected_pointer_revision != history["pointer_revision"]):
        raise ValueError("Reviewed discussion has no matching reservation")
    dispatch = matches[0]
    if (dispatch["step_id"] != fixture["step_id"] or dispatch["message"] != parsed.message
            or dispatch["client_turn_id"] != request["turn_id"]
            or dispatch["client_thread_id"] != request["client_thread_id"]
            or dispatch.get("scope", {}).get("task", {}).get("kind") != "discuss"):
        raise ValueError("Reviewed discussion differs from the reserved step")


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



def require_plan_fixture_basis(committed, world, work, selection, *, require_clean=False):
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
    if require_clean and committed.get("has_divergent_working_copy") is not False:
        raise ValueError("Document-start placement requires a clean committed Plan")
    if selection is not None and committed["markdown"].count(selection) != 1:
        raise ValueError("Plan fixture selection is absent or ambiguous in the committed Plan")

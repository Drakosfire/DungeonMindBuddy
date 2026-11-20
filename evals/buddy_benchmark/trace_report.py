"""Render retained benchmark timestamps without exposing the captured prompt."""
from html import escape
import os
from collections import defaultdict
import json
from pathlib import Path

from .artifacts import immutable_save
from .context_capture import summarize_host_trace, validate_context_packet

WRAPPERS = {"runtime_dispatch", "runtime_to_admission", "controller_round"}


def read(path):
    return json.loads(path.read_text())


def build(root, case, *, world, question):
    capture = root if (root / case).is_dir() else root / "capture"
    detail = read(capture / case / "detailed-host-trace.json")
    ready = read(capture / case / "context-ready.json")
    request_packet = read(capture / case / "context-request.json")
    terminal = read(capture / case / "context-stop.json")
    validated = validate_context_packet(ready, request_packet, terminal)
    turn = validated["turn"]
    if (turn.world_id, turn.user_text) != (world, question):
        raise ValueError("Trace capture differs from the manifest case")
    summarize_host_trace(detail, ready, terminal)
    browser_file = capture / "browser-timing.json"
    browser = read(browser_file) if browser_file.is_file() else None
    if browser is not None:
        from apps.live_control_server.services.agent_turn_service import _turn_idempotency_key
        request_body = browser["request"]
        if (request_body != read(capture / case / "request.json")
                or request_body["owner_scope"]["world_id"] != turn.world_id
                or request_body["message"] != turn.user_text
                or _turn_idempotency_key(turn.world_id, request_body["turn_id"]) != turn.idempotency_key):
            raise ValueError("Browser clock capture has a different durable case request")
    if detail["truncated"]:
        raise ValueError("Cannot attribute a truncated trace")
    bounds = browser["before"] + browser["after"] if browser is not None else [(0, 0)]
    lower = max(pair[0] for pair in bounds)
    upper = min(pair[1] for pair in bounds)
    if lower > upper:
        raise ValueError("Browser clocks did not produce compatible bounds")

    def tick(value):
        return round((value + (lower + upper) / 2) * 1e6)

    ingress, sink = detail["start_monotonic_ns"], detail["end_monotonic_ns"]
    marks = browser["browserMarks"] if browser is not None else {}
    click, request = ((tick(marks["click"]), tick(marks["request"]))
                      if browser is not None else (ingress, ingress))
    if not click <= request <= ingress <= sink:
        raise ValueError("Browser and host milestones are out of order")
    host_spans = [(s["name"], s["start_monotonic_ns"], s["end_monotonic_ns"])
                  for s in detail["intervals"]]
    spans = [(name, first, last) for name, first, last in host_spans
             if name not in WRAPPERS and first < last]
    measured_host_count = len(spans)
    if browser is not None:
        spans += [("browser Send handling", click, request), ("browser to ASGI transit", request, ingress)]
    for entry in marks.get("preflight", []):
        first, last = tick(entry["start"]), min(request, tick(entry["end"]))
        if not click <= first <= request or last < first:
            raise ValueError("Browser preflight starts outside Send preparation")
        if first < last:
            spans.append(("browser " + entry["phase"], first, last))
    wire_path = root / "jev-transport-intervals.json"
    if wire_path.is_file():
        wire = read(wire_path)
        dispatch_entry = next((s["start_monotonic_ns"] for s in detail["intervals"]
                               if s["name"] == "first_jev_transport_entry"), None)
        if wire and (dispatch_entry is None or
                     not wire[0]["entry_ns"] <= dispatch_entry <= wire[0]["body_read_ns"]):
            raise ValueError("Jev transport does not join the case's first dispatch")
        previous = ingress
        for phase in wire:
            if phase["mode"] not in {"live", "replay"} or phase["mode"] != wire[0]["mode"]:
                raise ValueError("Unknown Jev timing boundary")
            first, last = phase["entry_ns"], phase["body_read_ns"]
            if not previous <= first <= last <= sink:
                raise ValueError("Jev transport outside the measured host boundary")
            previous = last
            if first < last:
                spans.append(("Jev " + phase["mode"] + " transport", first, last))

    points = sorted({click, sink, *(p for _, a, b in spans for p in (a, b))})
    intervals, totals, exclusive = [], defaultdict(int), defaultdict(int)
    for first, last in zip(points, points[1:]):
        active = [span for span in spans if span[1] <= first and last <= span[2]]
        leaves = [span for span in active if not any(span[1] <= child[1] and child[2] <= span[2]
                  and span[1:] != child[1:] for child in active)]
        names = sorted({span[0] for span in leaves})
        label = " / ".join(names) or "Unattributed"
        if len(names) == 1:
            exclusive[names[0]] += last - first
        totals[label] += last - first
        if intervals and intervals[-1]["label"] == label:
            intervals[-1]["end_ms"] = (last - click) / 1e6
        else:
            intervals.append({"label": label, "start_ms": (first - click) / 1e6, "end_ms": (last - click) / 1e6})

    durations = defaultdict(list)
    for name, first, last in host_spans + spans[measured_host_count:]:
        durations[name].append(last - first)
    operations = [
        {"name": name, "calls": sum(value > 0 for value in samples), "markers": samples.count(0),
         "inclusive_ms": sum(samples) / 1e6,
         "max_call_ms": max(samples) / 1e6, "exclusive_ms": exclusive[name] / 1e6,
         "wrapper_excluded": name in WRAPPERS}
        for name, samples in durations.items()
    ]
    operations.sort(key=lambda row: (-row["exclusive_ms"], row["name"]))

    wall = sink - click
    if wall <= 0:
        raise ValueError("Trace has no measured duration")
    return {"case": case, "trace_id": detail["trace_id"], "wall_ms": wall / 1e6,
            "start_boundary": "browser_send" if browser is not None else "request_start",
            "end_boundary": "writer_transport_sink" if terminal.get("transport_sink") else "writer_ready",
            "request_to_writer_ready_ms": validated["request_to_ready_ms"],
            "calibration_width_ms": upper - lower,
            "observed_duration_percent": 100 * (1 - totals["Unattributed"] / wall),
            "unattributed_ms": totals["Unattributed"] / 1e6,
            "allocated_ms": {key: value / 1e6 for key, value in sorted(totals.items(), key=lambda row: -row[1])},
            "operations": operations, "intervals": intervals}


def render(report):
    rows = []
    wall = report["wall_ms"]
    for entry in report["intervals"]:
        start, end = entry["start_ms"], entry["end_ms"]
        label = escape(entry["label"])
        kind = "gap" if label == "Unattributed" else ""
        rows.append(f'<tr><th scope="row">{label}</th><td class="track"><span class="{kind}" '
                    f'style="left:{100 * start / wall:.3f}%;width:{100 * (end - start) / wall:.3f}%">'
                    f'</span></td><td>{start:,.2f}</td><td>{end - start:,.2f}</td></tr>')
    operations = []
    for operation in report["operations"]:
        label = escape(operation["name"])
        if operation["wrapper_excluded"]:
            label += " (wrapper)"
        operations.append(f'<tr><th scope="row">{label}</th><td>{operation["calls"]}</td><td>{operation["markers"]}</td>'
                          f'<td>{operation["inclusive_ms"]:,.2f}</td><td>{operation["exclusive_ms"]:,.2f}</td>'
                          f'<td>{operation["max_call_ms"]:,.2f}</td></tr>')
    case = escape(report["case"])
    start = escape(report["start_boundary"].replace("_", " "))
    end = escape(report["end_boundary"].replace("_", " "))
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        f'<title>{case} latency waterfall</title>'
        '<style>body{margin:2rem auto;padding:0 1rem;max-width:75rem;font:16px system-ui;color:#17252f}'
        'table{width:100%;border-collapse:collapse}th,td{padding:.4rem;border-bottom:1px solid #e1e6ea;'
        'text-align:left;font-variant-numeric:tabular-nums}.track{position:relative;width:45%;background:#f3f6f8}'
        '.track span{position:absolute;top:22%;bottom:22%;background:#25798a}.track .gap{background:#a9562a}</style>'
        f'<h1>{case} latency waterfall</h1><p>{start} to {end} · {wall:,.1f} ms · '
        f'{report["observed_duration_percent"]:.2f}% attributed</p><p><a href="trace-report.json">'
        'Machine-readable report</a></p><h2>Operation totals</h2>'
        '<p>Inclusive times can overlap. Exclusive times exclude wrappers and time shared by different operations.</p>'
        '<table><thead><tr><th>Operation</th><th>Calls</th><th>Markers</th><th>Inclusive (ms)</th><th>Exclusive (ms)</th>'
        '<th>Max call (ms)</th></tr></thead><tbody>' + "".join(operations) +
        '</tbody></table><h2>Waterfall</h2><table><thead><tr><th>Operation</th><th>Relative time</th>'
        '<th>Start (ms)</th><th>Duration (ms)</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></html>\n"
    )


def write_report(root, case, output, *, world, question):
    report = build(root, case, world=world, question=question)
    html = render(report)
    immutable_save(output, "trace-report", report)
    target = output / "trace-report.html"
    if target.exists():
        if target.read_text() != html:
            raise ValueError("checkpoint collision: trace-report.html")
        return
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(html)

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
    if browser is not None and browser["request"] != read(capture / case / "request.json"):
        raise ValueError("Browser clock capture has a different case request")
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
    spans = [(s["name"], s["start_monotonic_ns"], s["end_monotonic_ns"])
             for s in detail["intervals"] if s["name"] not in WRAPPERS
             and s["start_monotonic_ns"] < s["end_monotonic_ns"]]
    if browser is not None:
        spans += [("browser Send handling", click, request), ("browser to ASGI transit", request, ingress)]
    for entry in marks.get("preflight", []):
        first, last = tick(entry["start"]), min(request, tick(entry["end"]))
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
        for phase in wire:
            if phase["mode"] not in {"live", "replay"}:
                raise ValueError("Unknown Jev timing boundary")
            first, last = phase["entry_ns"], phase["body_read_ns"]
            if not ingress <= first <= last <= sink:
                raise ValueError("Jev transport outside the measured host boundary")
            if first < last:
                spans.append(("Jev " + phase["mode"] + " transport", first, last))

    points = sorted({click, sink, *(p for _, a, b in spans for p in (a, b))})
    intervals, totals = [], defaultdict(int)
    for first, last in zip(points, points[1:]):
        active = [span for span in spans if span[1] <= first and last <= span[2]]
        leaves = [span for span in active if not any(span[1] <= child[1] and child[2] <= span[2]
                  and span[1:] != child[1:] for child in active)]
        label = " / ".join(sorted({span[0] for span in leaves})) or "Unattributed"
        totals[label] += last - first
        if intervals and intervals[-1]["label"] == label:
            intervals[-1]["end_ms"] = (last - click) / 1e6
        else:
            intervals.append({"label": label, "start_ms": (first - click) / 1e6, "end_ms": (last - click) / 1e6})

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
            "intervals": intervals}


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
        'Machine-readable report</a></p><table><thead><tr><th>Operation</th><th>Relative time</th>'
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

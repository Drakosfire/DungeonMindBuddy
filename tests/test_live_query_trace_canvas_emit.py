from __future__ import annotations

import json
from pathlib import Path

from evals.c2_live_prep.live_query_trace_canvas_emit import (
    canvas_data_path,
    emit_from_trace,
    emit_from_traces,
    parse_trace_spec,
    write_data_sidecar,
)
from evals.c2_live_prep.live_query_trace_canvas_payload import (
    build_multi_query_canvas_payload,
    load_trace_payload,
)

_REPO = Path(__file__).resolve().parents[1]
_TUNED_TELEMETRY = (
    _REPO
    / "evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_tuned_telemetry.json"
)
_FRESH = (
    _REPO
    / "evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_fresh_ingested_lexical.json"
)
_KARSEMINE = (
    _REPO
    / "evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_karsemine_heard_at_night.json"
)


def test_load_tuned_trace_payload_quality_aligned() -> None:
    payload = load_trace_payload(_TUNED_TELEMETRY)
    assert payload["format"] == "telemetry"
    assert payload["quality"]["label"] == "aligned"
    assert payload["quality"]["session22_closing_beat_signal"] is True
    assert payload["retrieval"]["retrieval_trace_summary"] is None


def test_build_multi_query_payload_collapsed_and_expanded() -> None:
    detail = load_trace_payload(_TUNED_TELEMETRY)
    canvas_payload = build_multi_query_canvas_payload([(detail, False), (detail, True)])
    assert len(canvas_payload["queries"]) == 2
    assert canvas_payload["queries"][0]["default_expanded"] is False
    assert canvas_payload["queries"][0]["detail"] is not None
    assert canvas_payload["queries"][1]["default_expanded"] is True
    assert canvas_payload["queries"][1]["detail"] is not None


def test_parse_trace_spec_collapsed_suffix() -> None:
    spec = parse_trace_spec("evals/foo.json:collapsed")
    assert spec.explicit_expanded is False
    assert spec.path == Path("evals/foo.json")


def test_parse_trace_spec_expanded_suffix() -> None:
    spec = parse_trace_spec("evals/foo.json:expanded")
    assert spec.explicit_expanded is True


def test_load_karsemine_telemetry_without_step1_has_evidence_and_answer() -> None:
    payload = load_trace_payload(_KARSEMINE)
    assert payload["format"] == "telemetry"
    assert payload["retrieval"]["admitted_count"] == 12
    assert len(payload["retrieval"]["top_admitted"]) >= 5
    assert "rhythmic sound" in payload["answer"]["text"].lower()
    assert len(payload["citations"]) >= 1


def test_load_fresh_telemetry_payload_quality_drift() -> None:
    payload = load_trace_payload(_FRESH)
    assert payload["format"] == "telemetry"
    assert payload["quality"]["label"] == "drift"
    assert payload["quality"]["conical_hill_drift_signal"] is True


def test_emit_writes_data_sidecar(tmp_path: Path) -> None:
    canvas = tmp_path / "live-query-telemetry-trace-session22.canvas.tsx"
    canvas.write_text("// shell\n", encoding="utf-8")
    detail = load_trace_payload(_TUNED_TELEMETRY)
    payload = build_multi_query_canvas_payload([(detail, False)])
    sidecar = write_data_sidecar(
        canvas_tsx=canvas,
        payload=payload,
        trace_specs=[parse_trace_spec(str(_TUNED_TELEMETRY))],
    )
    assert sidecar == canvas_data_path(canvas)
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    row = data["liveQueryTracePayload"]["queries"][0]
    assert row["summary"]["quality_label"] == "aligned"
    assert "Lysandro" in row["detail"]["answer"]["text"]


def test_emit_from_trace_bootstraps_shell_and_data(tmp_path: Path) -> None:
    canvas = tmp_path / "canvases" / "live-query-telemetry-trace-session22.canvas.tsx"
    summary = emit_from_traces(
        trace_specs=[
            parse_trace_spec(f"{_TUNED_TELEMETRY}:collapsed"),
            parse_trace_spec(str(_FRESH)),
        ],
        canvas_paths=[canvas],
        bootstrap=True,
    )
    assert summary["query_count"] == 2
    assert not summary["errors"]
    assert canvas.is_file()
    sidecar = canvas_data_path(canvas)
    assert sidecar.is_file()
    shell = canvas.read_text(encoding="utf-8")
    assert "useCanvasState" in shell
    assert "liveQueryTracePayload" in shell
    assert "BEGIN GENERATED" not in shell

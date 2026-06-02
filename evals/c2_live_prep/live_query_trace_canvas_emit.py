#!/usr/bin/env python3
"""Emit / refresh the live-query trace review canvas from one or more trace artifacts.

Writes a multi-query payload to the canvas data sidecar (``*.canvas.data.json``)
and syncs the static shell (``*.canvas.tsx``). Targets both Buddy-only and
monorepo workspace canvas directories when present.

Example::

  uv run python -m evals.c2_live_prep.live_query_trace_canvas_emit \\
    --trace evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_tuned_telemetry.json:collapsed \\
    --trace evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_karsemine_heard_at_night.json
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.c2_live_prep.live_query_trace_canvas_payload import (
    build_multi_query_canvas_payload,
    build_payload,
    load_trace_payload,
)
from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import (
    cursor_canvases_dir,
    default_cursor_canvas_path,
    ensure_canvas_file_for_patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE = Path(__file__).resolve().parent / "canvas_templates" / "live-query-telemetry-trace-session22.canvas.tsx"
_DEFAULT_TRACE = (
    _REPO_ROOT
    / "evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_tuned_retrieval_alignment.json"
)
_CANVAS_FILENAME = "live-query-telemetry-trace-session22.canvas.tsx"
_DATA_KEY = "liveQueryTracePayload"
_META_KEY = "_live_query_trace_emit_meta"


@dataclass(frozen=True)
class TraceSpec:
    path: Path
    explicit_expanded: bool | None = None


def parse_trace_spec(raw: str) -> TraceSpec:
    text = raw.strip()
    explicit: bool | None = None
    if text.endswith(":collapsed"):
        explicit = False
        text = text[: -len(":collapsed")].strip()
    elif text.endswith(":expanded"):
        explicit = True
        text = text[: -len(":expanded")].strip()
    return TraceSpec(path=Path(text), explicit_expanded=explicit)


def canvas_data_path(canvas_tsx: Path) -> Path:
    name = canvas_tsx.name
    if not name.endswith(".canvas.tsx"):
        raise ValueError(f"expected *.canvas.tsx, got {canvas_tsx}")
    return canvas_tsx.with_name(name.replace(".canvas.tsx", ".canvas.data.json"))


def default_canvas_targets() -> list[Path]:
    """Buddy workspace + monorepo root (when different)."""
    roots = [_REPO_ROOT, _REPO_ROOT.parent]
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        p = default_cursor_canvas_path(_CANVAS_FILENAME, workspace_root=root)
        key = str(p.parent)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def bootstrap_canvas(*, canvas_path: Path) -> Path:
    target = canvas_path.expanduser().resolve()
    if not _TEMPLATE.is_file():
        raise FileNotFoundError(f"Missing canvas shell template: {_TEMPLATE}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_TEMPLATE, target)
    return target


def build_canvas_payload(trace_specs: list[TraceSpec]) -> dict[str, Any]:
    entries: list[tuple[dict[str, Any], bool]] = []
    last_idx = len(trace_specs) - 1
    for idx, spec in enumerate(trace_specs):
        detail = load_trace_payload(spec.path)
        if spec.explicit_expanded is not None:
            default_expanded = spec.explicit_expanded
        else:
            default_expanded = idx == last_idx
        entries.append((detail, default_expanded))
    return build_multi_query_canvas_payload(entries)


def write_data_sidecar(
    *,
    canvas_tsx: Path,
    payload: dict[str, Any],
    trace_specs: list[TraceSpec],
) -> Path:
    sidecar = canvas_data_path(canvas_tsx)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if sidecar.is_file():
        raw = json.loads(sidecar.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            existing = raw
    existing[_DATA_KEY] = payload
    existing[_META_KEY] = {
        "trace_paths": [str(spec.path.resolve()) for spec in trace_specs],
        "query_count": len(payload.get("queries") or []),
        "canvas_tsx": str(canvas_tsx.resolve()),
        "canvas_data_json": str(sidecar.resolve()),
        "canvases_dir": str(canvas_tsx.parent.resolve()),
    }
    sidecar.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sidecar


def sync_canvas_shell(canvas_tsx: Path) -> str:
    target = canvas_tsx.expanduser().resolve()
    template_text = _TEMPLATE.read_text(encoding="utf-8")
    if target.is_file():
        current = target.read_text(encoding="utf-8")
        if current == template_text:
            return "canvas_unchanged"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_TEMPLATE, target)
    return "canvas_updated"


def emit_from_traces(
    *,
    trace_specs: list[TraceSpec],
    canvas_paths: list[Path] | None = None,
    bootstrap: bool = False,
) -> dict[str, Any]:
    if not trace_specs:
        raise ValueError("at least one --trace is required")

    targets = [p.expanduser().resolve() for p in (canvas_paths or default_canvas_targets())]
    payload = build_canvas_payload(trace_specs)

    per_target: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for canvas_tsx in targets:
        row: dict[str, Any] = {
            "canvases_dir": str(canvas_tsx.parent),
            "canvas_tsx": str(canvas_tsx),
        }
        try:
            if bootstrap or not canvas_tsx.is_file():
                bootstrap_canvas(canvas_path=canvas_tsx)
                row["canvas_bootstrap"] = True
            else:
                ensure_canvas_file_for_patch(canvas_tsx)
            row["canvas_shell"] = sync_canvas_shell(canvas_tsx)
            sidecar = write_data_sidecar(canvas_tsx=canvas_tsx, payload=payload, trace_specs=trace_specs)
            row["canvas_data_json"] = str(sidecar)
            row["data_updated"] = True
        except OSError as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            errors.append(row)
        except FileNotFoundError as exc:
            row["error"] = str(exc)
            errors.append(row)
        per_target.append(row)

    queries = list(payload.get("queries") or [])
    return {
        "trace_paths": [str(spec.path.resolve()) for spec in trace_specs],
        "query_count": len(queries),
        "queries": [
            {
                "query_id": q.get("query_id"),
                "default_expanded": q.get("default_expanded"),
                "question": (q.get("summary") or {}).get("question"),
                "quality_label": (q.get("summary") or {}).get("quality_label"),
            }
            for q in queries
            if isinstance(q, dict)
        ],
        "buddy_canvases_dir": str(cursor_canvases_dir(_REPO_ROOT)),
        "monorepo_canvases_dir": str(cursor_canvases_dir(_REPO_ROOT.parent)),
        "targets": per_target,
        "errors": errors,
    }


def emit_from_trace(
    *,
    trace_path: Path,
    canvas_paths: list[Path] | None = None,
    bootstrap: bool = False,
    collapsed: bool = False,
) -> dict[str, Any]:
    return emit_from_traces(
        trace_specs=[TraceSpec(path=trace_path, collapsed=collapsed)],
        canvas_paths=canvas_paths,
        bootstrap=bootstrap,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace",
        action="append",
        default=[],
        help="Trace artifact path. Append ':collapsed' for summary-only row.",
    )
    parser.add_argument(
        "--canvas-tsx",
        type=Path,
        action="append",
        dest="canvas_tsx_list",
        default=None,
        help="Target canvas (repeatable). Default: Buddy + monorepo canvas dirs.",
    )
    parser.add_argument(
        "--bootstrap-canvas",
        action="store_true",
        help="Force copy repo shell into target canvases/ before writing data sidecar.",
    )
    args = parser.parse_args()

    if args.trace:
        trace_specs = [parse_trace_spec(raw) for raw in args.trace]
    else:
        trace_specs = [TraceSpec(path=_DEFAULT_TRACE)]

    summary = emit_from_traces(
        trace_specs=trace_specs,
        canvas_paths=[p for p in args.canvas_tsx_list] if args.canvas_tsx_list else None,
        bootstrap=args.bootstrap_canvas,
    )
    print(json.dumps(summary, indent=2))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

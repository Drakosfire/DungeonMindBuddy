"""Shared benchmark-review canvas style for sentence-routing eval emitters.

Canonical layout and helpers for C1S2-style review canvases: artifact pointers,
summary stats, gate table, collapsible per-scenario cards, and a single generated
JSON block. See ``.cursor/skills/benchmark-review-canvas/SKILL.md``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONTEXT_CLIP = 16000

TSX_IMPORTS = """import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
} from 'cursor/canvas';
"""

TSX_PRE_SMALL_CONST = """const preSmall = {
  margin: 0,
  whiteSpace: 'pre-wrap' as const,
  fontFamily: 'var(--font-mono, ui-monospace, monospace)',
  fontSize: 12,
  lineHeight: 1.45,
};
"""

TSX_LIST_HELPERS = """function joinList(values: readonly string[]) {
  return values.length ? values.join(', ') : '—';
}

function formatHits(hits: readonly HitRow[]) {
  return hits.map((h) => [
    h.unit_id,
    h.line_span,
    String(h.score),
    h.routes.length ? h.routes.slice(0, 2).join(', ') : '—',
    h.why_matched.length ? h.why_matched.slice(0, 3).join(', ') : '—',
  ]);
}

function verdictPill(verdict: string) {
  if (verdict === 'regressed') return <Pill tone="danger">REGRESSED</Pill>;
  if (verdict === 'improved') return <Pill tone="success">IMPROVED</Pill>;
  if (verdict === 'unchanged_pass') return <Pill tone="success">UNCHANGED_PASS</Pill>;
  return <Pill tone="warning">UNCHANGED_FAIL</Pill>;
}
"""

TSX_HIT_ROW_TYPE = """type HitRow = {
  unit_id: string;
  line_span: string;
  score: number;
  routes: readonly string[];
  why_matched: readonly string[];
};
"""

TSX_PAGE_SHELL_OPEN = """export default function BenchmarkReviewCanvas() {
  return (
    <Stack gap={20} padding={16}>
"""

TSX_PAGE_SHELL_CLOSE = """    </Stack>
  );
}
"""


def generated_block(*, begin: str, end: str, const_name: str, payload: dict[str, Any]) -> str:
    return (
        f"{begin}\n"
        f"const {const_name} = {json.dumps(payload, indent=2)} as const;\n"
        f"{end}"
    )


def write_canvas(*, template: str, block: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.format(block=block), encoding="utf-8")


def clip_context(text: str, *, limit: int = DEFAULT_CONTEXT_CLIP) -> str:
    return text[:limit]


def results_by_id(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in report.get("results") or []:
        if isinstance(row, dict):
            out[str(row.get("scenario_id") or "")] = row
    return out


def context_from_result(result: dict[str, Any] | None, *, limit: int = DEFAULT_CONTEXT_CLIP) -> tuple[str, str]:
    if not result:
        return "", ""
    promoted = clip_context(str(result.get("retrieved_context") or ""), limit=limit)
    full = clip_context(str(result.get("retrieval_hit_context_full") or ""), limit=limit)
    return promoted, full


def compact_hit_rows(raw_hits: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hit in raw_hits[:limit]:
        routes = [
            str(route.get("normalized_route") or "")
            for route in list(hit.get("routes") or [])
            if isinstance(route, dict)
        ]
        rows.append(
            {
                "unit_id": str(hit.get("unit_id") or ""),
                "line_span": f"L{int(hit.get('line_start') or 0)}-{int(hit.get('line_end') or 0)}",
                "score": int(hit.get("score") or 0),
                "routes": [route for route in routes if route],
                "why_matched": [str(x) for x in (hit.get("why_matched") or [])],
            }
        )
    return rows


def missed_detail_rows(*, violations: list[str], arm: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = [["gate violation", violation] for violation in violations]
    for token in arm.get("context_must_hits_missing") or []:
        rows.append(["must_hit keyword", str(token)])
    for item in arm.get("expected_route_substring_breakdown") or []:
        if isinstance(item, dict) and not bool(item.get("matched")):
            rows.append(["expected corpus route", str(item.get("substring") or "")])
    return rows


def delta_missed_rows(delta: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for unit in delta.get("topk_units_swapped_out") or []:
        rows.append(["ranking unit (top-k out)", str(unit)])
    for unit in delta.get("topk_units_swapped_in") or []:
        rows.append(["ranking unit (top-k in)", str(unit)])
    for unit in delta.get("full_units_swapped_out") or []:
        rows.append(["full ranking unit (out)", str(unit)])
    for unit in delta.get("full_units_swapped_in") or []:
        rows.append(["full ranking unit (in)", str(unit)])
    for substring in delta.get("substrings_flipped_lost") or []:
        rows.append(["route substring lost", str(substring)])
    for substring in delta.get("substrings_flipped_gained") or []:
        rows.append(["route substring gained", str(substring)])
    for token in delta.get("tokens_added_by_equivalences") or []:
        rows.append(["query token added", str(token)])
    for token in delta.get("tokens_removed_by_equivalences") or []:
        rows.append(["query token removed", str(token)])
    return rows


def artifact_pointer_lines(pointers: dict[str, str]) -> str:
    lines: list[str] = []
    for const_name, path in pointers.items():
        lines.append(f"const {const_name} = {json.dumps(path)};")
    return "\n\n".join(lines)

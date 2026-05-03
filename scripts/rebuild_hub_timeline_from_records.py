#!/usr/bin/env python3
"""Deterministically rebuild a hub timeline from session-memory records JSONL.

This writer is intentionally mechanical: filter rows by hub-route substring,
sort by (session_number, line_start, unit_id), and emit one markdown table with
unit ids plus lexical text.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_records(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _has_hub_route(row: dict[str, Any], hub_route_substring: str) -> bool:
    needle = hub_route_substring.strip().lower()
    if not needle:
        return False
    for route in row.get("routes") or []:
        normalized = str(route.get("normalized_route") or "").lower()
        if needle in normalized:
            return True
    return False


def _sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    return (
        int(row.get("session_number") or -1),
        int(row.get("line_start") or -1),
        str(row.get("unit_id") or ""),
    )


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _render(
    *,
    title: str,
    records_path: Path,
    hub_route_substring: str,
    rows: list[dict[str, Any]],
) -> str:
    by_session: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_session[int(row.get("session_number") or -1)].append(row)

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(
        "Deterministic hub timeline generated from `dmb_session_memory_record_v1` rows."
    )
    lines.append(
        f"Filter: routes containing `{hub_route_substring}` | Source: `{records_path}`"
    )
    lines.append("")
    lines.append("| Session | Order | Unit ID | Recap file | Text |")
    lines.append("| --- | ---: | --- | --- | --- |")

    for session in sorted(s for s in by_session.keys() if s >= 0):
        session_rows = sorted(by_session[session], key=_sort_key)
        for idx, row in enumerate(session_rows, start=1):
            unit_id = str(row.get("unit_id") or "")
            recap = str(row.get("source_recap_path") or "")
            recap_name = Path(recap).name if recap else ""
            text = _escape_cell(str(row.get("lexical_plain") or ""))
            lines.append(
                f"| {session} | {idx} | `{unit_id}` | `{recap_name}` | {text} |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-jsonl", type=Path, required=True)
    parser.add_argument("--hub-route-substring", type=str, required=True)
    parser.add_argument("--timeline-md", type=Path, required=True)
    parser.add_argument(
        "--title",
        type=str,
        default="Lysandra Ironveil — Campaign 2 timeline",
        help="Top-level markdown title.",
    )
    parser.add_argument(
        "--session",
        type=int,
        default=None,
        help="Optional single-session filter (e.g. 20).",
    )
    args = parser.parse_args()

    records = _load_records(args.records_jsonl)
    filtered = [r for r in records if _has_hub_route(r, args.hub_route_substring)]
    if args.session is not None:
        filtered = [r for r in filtered if int(r.get("session_number") or -1) == args.session]

    rendered = _render(
        title=args.title,
        records_path=args.records_jsonl,
        hub_route_substring=args.hub_route_substring,
        rows=filtered,
    )
    args.timeline_md.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.timeline_md),
                "rows": len(filtered),
                "session": args.session,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

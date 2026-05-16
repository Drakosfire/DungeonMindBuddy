from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.c1s4_preplanning_vertical_slice.expected_context_canvas_payload import (
    build_payload,
    load_gold,
    load_report,
    render_generated_block,
    update_canvas_text,
    validate_payload,
)
from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import (
    default_cursor_canvas_path,
    ensure_canvas_file_for_patch,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--payload-out", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--canvas-tsx",
        type=Path,
        default=default_cursor_canvas_path("c1s4-expected-context-benchmark.canvas.tsx"),
    )
    args = parser.parse_args()

    report = load_report(args.report)
    gold = load_gold(args.gold) if args.gold else None
    payload = build_payload(report=report, gold=gold, report_path=str(args.report), gold_path=str(args.gold) if args.gold else None)
    errs = validate_payload(payload)
    if errs:
        raise SystemExit("\n".join(errs))

    generated = render_generated_block(payload)
    canvas_path = ensure_canvas_file_for_patch(args.canvas_tsx)
    before = canvas_path.read_text(encoding="utf-8")
    after = update_canvas_text(before, generated)

    if args.payload_out:
        args.payload_out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if args.check:
        if before != after:
            print(f"stale generated block: {canvas_path}")
            return 1
        print(f"up to date: {canvas_path}")
        return 0

    if before != after:
        canvas_path.write_text(after, encoding="utf-8")
        print(f"updated: {canvas_path}")
    else:
        print(f"no change: {canvas_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

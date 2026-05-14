---
name: benchmark-review-canvas
description: >-
  Canon style for sentence-routing benchmark review canvases (C1S2 / C1S13 holdout
  deep-dive). Use when creating or refreshing eval benchmark `.canvas.tsx` files,
  wiring canvas emitters, or extending per-question review cards without rewriting
  layout from scratch.
---

# Benchmark review canvas style

## Where canvases live

- **Only path:** `~/.cursor/projects/<workspace-slug>/canvases/<name>.canvas.tsx` (Cursor-managed). Override the parent directory with `DMB_CURSOR_CANVAS_DIR` if needed.
- **Path helper:** `evals/sentence_routing_retrieval_falsification/cursor_canvas_paths.py` (`default_cursor_canvas_path`, `ensure_canvas_file_for_patch`).
- **General canvas SDK rules:** `~/.cursor/skills-cursor/canvas/SKILL.md`.

## Two emitter patterns

| Pattern | When | Example |
|--------|------|---------|
| **Patch** | Stable hand-authored shell; refresh data only | `c1s2_benchmark_canvas_emit.py` → `BEGIN GENERATED C1S2_HARNESS_DETAIL` |
| **Full emit** | New cohort deep-dive; shell + data from one command | `c1s13_holdout_l3_deep_dive_canvas_emit.py` |

Both patterns share the same **layout contract** and **generated-block** rules below.

## Layout contract (top → bottom)

1. **Title + one paragraph** — what the canvas is for.
2. **Artifact pointers** — `const` paths as `<Code>` (repo-relative; no `/tmp`).
3. **Headline stats** — `Grid` of `Stat` for counts only (numeric or short tokens).
4. **Gate table** — one row per scenario/question with verdict + pass/fail columns.
5. **Cohort callout** — interpret non-obvious gates (e.g. `context_must_hit` vs route coverage).
6. **Per-item cards** — `Card collapsible` per gold question / scenario:
   - Lane pills + baseline/equivalence pass pills
   - Question, expected answer, **expected context** (`preSmall`)
   - Must-hit + expected-route lists (`preSmall`)
   - **Stats:** `context_must_hit` ratios only
   - **Violations:** `Callout` + `Text size="small"` (never long strings in `Stat`)
   - **Explicit missed breakout** — `Table` axes: gate / must_hit / expected route / delta movement
   - **Retrieved context** — promoted slot + full `retrieval_hit_context` side by side
   - **Retrieval comparison** — route tables + compact hit tables

Open failing cards by default (`regressed`, `improved`, or `unchanged_fail` with failing baseline).

## Generated block

- Single JSON payload between markers: `// BEGIN GENERATED <ID>` … `// END GENERATED <ID>`.
- Build payload in Python; `json.dumps(..., indent=2)` into `const <name> = … as const;`.
- **Do not** hand-edit inside the block after emit.
- Hand-edit **outside** the block for layout experiments; promote repeated layout into `benchmark_review_canvas_template.py`.

## Shared code (do not copy-paste)

`evals/sentence_routing_retrieval_falsification/benchmark_review_canvas_template.py`

- TSX: `TSX_IMPORTS`, `TSX_PRE_SMALL_CONST`, `TSX_LIST_HELPERS`, `TSX_HIT_ROW_TYPE`
- Python: `generated_block`, `write_canvas`, `compact_hit_rows`, `missed_detail_rows`, `delta_missed_rows`, `context_from_result`, `results_by_id`, `clip_context`

New emitters: import helpers; add only cohort-specific payload + card JSX.

## Verification

- Unit test: emit to `tmp_path`, assert markers + headline strings + `question_count` (or scenario count).
- After `--refresh-reports`, spot-check one row: retrieved context non-empty when report JSON has `retrieved_context`.

## Anti-patterns

- Writing benchmark canvases anywhere except the Cursor-managed directory from `default_cursor_canvas_path` (or an explicit `--canvas-tsx` you intend).
- `/tmp` or ad-hoc artifact paths in embedded pointer `const`s.
- `Stat` for violation prose or expected answers.
- Treating `context_support_ratio === 1.0` as overall PASS without route gate context.

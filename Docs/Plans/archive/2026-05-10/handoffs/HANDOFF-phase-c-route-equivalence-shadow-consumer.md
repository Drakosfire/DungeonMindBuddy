# HANDOFF — Phase C entry: route-equivalence shadow consumer in `breadcrumb_query_run`

> **COMPLETED — 2026-05-10T16:22Z.** Shipped via [PR #4](https://github.com/Drakosfire/DungeonMindBuddy/pull/4) (`main` merge commit `21e84392da03095377b4de36defb82edfc37c741`). Round-2 commit `a5f3c1c` added the two harness-boundary safety tests (`test_route_equivalence_flag_is_additive_only_at_harness_boundary` and `test_route_equivalence_load_failure_emits_error_payload_and_run_survives`) that the round-1 loader-only test set was missing — and that gap is now codified as the new rubric bullet "test the boundary that owns the rubric" in `.cursor/rules/external-agent-pr-loop.mdc` and in `external_pull_requests[github-pr-4].rubric_when_we_judge`. Post-merge doc-sync landed in `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (v10) and `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (top-of-file PR header + Reanchor block + Phase C Evidence + new session-log entry). Known follow-up, not blocking: `shadow_route_equivalences.source_paths` stores `Path.__str__` of the resolved input which is machine-dependent — fold into the manifest-hash / provenance lane. **Archived for historical reference; do not re-dispatch.**

**Created:** 2026-05-10 (UTC).
**Status:** COMPLETED — see banner above. (Was: ACTIVE — dispatched to one external Codex subagent.)
**Parent agent:** Cursor agent; dispatcher is responsible for the post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, transitioning to **Phase C entry**, milestone progress **M2 in_progress → M3 not_started**). This handoff opens the M3 lane.

---

## §1 Mission

Wire the `breadcrumb_query_run` natural-gold harness to **consume the committed `route_equivalence_longmont_c*_v1.jsonl`** artifacts behind an explicit CLI flag, **shadow-only** — emitting a new per-scenario diagnostic field — without changing the legacy lexical seeds path or any retrieval/grading behavior.

## §2 Why this slice (context for the subagent)

- PR #3 (merged `98c09aaf0fead2aaaf4b3a7c90afcb09bae8026f`, 2026-05-10T05:06Z) committed canonical route-equivalence JSONL under `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/` plus `scripts/build_route_equivalence_manifests.py --check` and a byte-stable regression test. The artifacts are produced but **not consumed** anywhere in the harness or runtime today (`rg route_equivalence src` only lights up `src/lexicon_phase_b/`).
- This slice converts those artifacts from "produced" to "consumed" — but only as **shadow diagnostics**, alongside the existing `shadow_token_resolution` field. The legacy `build_campaign_lexicon` / benchmark seeds path remains the active source for retrieval and grading.
- This is the smallest possible Phase C entry: a flag, a loader, a per-scenario diagnostic, and tests. No retriever rewiring, no grading change, no new gold.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — the §4 allowlist / §5 denylist / §7 verification contract that this PR will be reviewed against.
2. **`src/lexicon_phase_b/schemas.py`** — `RouteEquivalenceRecord`, `EntityKind`, `AuthorityEffect`. Read-only; the loader you write returns these.
3. **`src/lexicon_phase_b/route_equivalence_manifest.py`** — the deterministic builder. Read-only; do not modify. The writer's canonical sort is `sorted(records, key=lambda r: r.record_id)`; your loader must preserve that order.
4. **`src/lexicon_phase_b/__init__.py`** — current `__all__`. You will extend it.
5. **`evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`** and **`…_c2_v1.jsonl`** — the committed artifacts you will load. Each line is a `RouteEquivalenceRecord` JSON with `schema_version: "0.2.0"`, `authority_effect: "routing_only"`. Read-only; **do not regenerate or rewrite**.
6. **`tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`** — read this for the existing parametrized `CASES` list and assertion style. Mirror it.
7. **`evals/sentence_routing_retrieval_falsification/token_resolver_shadow.py`** — the legacy shadow module. Read-only here. Read it to understand the "shadow-only, no scoring change" pattern. Your new shadow module should mirror its shape (small dataclass-style helpers, deterministic, no mutation of inputs).
8. **`evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`**, lines around **593–845** (argparse), **1009–1046** (`shadow_lexicon = build_campaign_lexicon(...)`), and **1122–1133** (where `row["shadow_token_resolution"]` is set). Your CLI flag and per-scenario emission slot in there.
9. **`evals/sentence_routing_retrieval_falsification/README.md`** — section "Route equivalence manifests (Phase B)" (around line 213). You will extend it with a "Shadow consumption (Phase C entry)" subsection.
10. **`tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`** — existing harness-wiring test file; you will extend it.
11. **`tests/conftest.py`** — confirm session-autouse `load_dungeonmindbuddy_dotenv()` is wired so live-tests don't need exported keys (see `.cursor/rules/dungeonbuddy-environment.mdc`).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| **Create** | `src/lexicon_phase_b/route_equivalence_loader.py` | Pure JSONL→`RouteEquivalenceRecord` loader. Lexicon-only. |
| **Modify** | `src/lexicon_phase_b/__init__.py` | Add `load_route_equivalence_manifest`, `load_route_equivalence_manifests` to `__all__`. **No other change.** |
| **Create** | `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Per-scenario shadow payload builder. Mirrors the shape of `token_resolver_shadow.py` (small, deterministic, no scoring effect). |
| **Modify** | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Add **one** CLI flag `--route-equivalence-jsonl PATH` (repeatable; `action="append"`). Load once (after `shadow_lexicon` build, before the per-scenario loop). Emit `row["shadow_route_equivalences"]` only inside the natural-gold branch (alongside the existing `row["shadow_token_resolution"]` set at lines 1122–1133). **No other behavioral edits.** |
| **Create** | `tests/lexicon_phase_b/test_route_equivalence_loader.py` | Lexicon-only tests for the loader (per the `tests/lexicon_phase_b/` rubric established in PR #2). |
| **Modify** | `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Append new tests for the shadow payload helper, exercised against C1S1–C1S3 campaign IDs. **Do not delete or rewrite the two existing tests.** |
| **Modify** | `evals/sentence_routing_retrieval_falsification/README.md` | Add a **Shadow consumption (Phase C entry)** subsection under the existing "Route equivalence manifests (Phase B)" section (around line 213). One paragraph + one example invocation. |

Your `git diff --stat origin/main...HEAD` MUST be expressible from these seven entries and **only** these seven entries. Anything else is scope creep — see §5.

## §5 Files explicitly OUT OF SCOPE (denylist + concrete collision risks)

You will be tempted to "fix while I'm here." Resist. Each item below has a concrete risk attached.

| Path | Why out of scope | Concrete collision/regression risk |
|---|---|---|
| `src/lexicon_phase_b/schemas.py` | Schema is committed and shipped via PR #2/PR #3. | Any field rename will break `route_equivalence_longmont_c*_v1.jsonl` byte-stability and fail `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`. |
| `src/lexicon_phase_b/route_equivalence_manifest.py` | Builder is committed; PR #3's CLI depends on its output bytes. | Reordering helpers or touching `_path_to_route_id` will silently shift `from_route_id` strings and break the byte-stable test. |
| `scripts/build_route_equivalence_manifests.py` | Stable CLI; the parent uses `--check` as the main next-gate command. | Any change here cascades into `out/` directory expectations across machines. |
| `evals/.../artifacts/lexicon/route_equivalence_longmont_c*_v1.jsonl` | Canonical committed artifacts. | **Do not regenerate.** Your loader reads these; the byte-stable test pins them to the registry. |
| `evals/.../artifacts/lexicon/benchmark_lexicon_seeds_v1.json` | Legacy benchmark seeds; the contract for this slice is **legacy stays the active source**. | Merging route-equivalence content into seeds **breaks the shadow-only contract** of this PR and re-litigates the Phase B/C split. |
| `evals/sentence_routing_retrieval_falsification/token_resolver_shadow.py` | Legacy shadow module; do not pipe route-equivalences through `compute_shadow_diff`. | The shape of `shadow_token_resolution` is consumed downstream; widening it changes a contract that's not part of this slice. Add a **sibling** module instead (`route_equivalence_shadow.py`). |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | Grader uses the legacy lexicon for scoring decisions. | Any change here makes this PR a grading-change PR and breaks the shadow-only invariant. |
| `src/agent/session_memory_query.py` | Planner-runtime path. | This slice is benchmark-shadow only. Wiring runtime is a later, separate slice (Phase C proper). |
| `src/contracts/npc_registry.py` | Used by the manifest builder; not relevant to a loader-only consumer. | Touching this risks PR #2/PR #3 regression. |
| `tests/test_token_resolution_*.py`, `tests/test_benchmark_lexicon_seeds.py` | These already exist on `main` with **token-resolution test layout** that PR #1 collided with. | **Hard collision risk.** PR #1 was closed precisely because it created basenames that conflicted with these. Do not touch them. Do not create new tests at any `tests/test_token_resolution_*` basename. |
| `tests/lexicon_phase_b/test_route_equivalence_*` (existing 5 files) | They lock PR #2/#3 contract. | Edit only the **new** `test_route_equivalence_loader.py` file you create. |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`, `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Plan/checklist sync is the **parent agent's** atomic post-merge job. | If the subagent edits these, the parent will revert and re-brief. |
| Any `Docs/Plans/HANDOFF-*.md` other than this one | Each handoff names exactly one slice. | Editing other handoffs muddles the active-vs-archived boundary. |
| Any `Docs/Plans/archive/**` | Archived material is historical. | Read-only. |
| Any `corpus/**` | Corpus is GM-private; benchmark consumers must not mutate it. | See `.cursor/rules/corpus-pii-and-llm-payloads.mdc`. |
| Any `.cursor/rules/*.mdc` | Rules are parent-managed. | Out of scope for this PR. |

**Naming hard rules:**
- Lexicon-only tests live under `tests/lexicon_phase_b/` (PR #2 rubric).
- Harness-wiring tests live under `tests/` root (this is the seam between lexicon and harness; the existing `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` is the canonical home).
- Do **not** create tests under any `tests/test_token_resolution_*` basename. **Do not** create a sibling test file named `tests/test_route_equivalence_*` at the `tests/` root either — that name belongs under `tests/lexicon_phase_b/`.

## §6 Implementation contract

### 6.1 Loader — `src/lexicon_phase_b/route_equivalence_loader.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .schemas import RouteEquivalenceRecord

# Schema versions this loader can deserialize. Keep in sync with
# RouteEquivalenceRecord.schema_version. Add new versions explicitly when
# the writer schema bumps.
SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS: frozenset[str] = frozenset({"0.2.0"})


def load_route_equivalence_manifest(path: Path) -> list[RouteEquivalenceRecord]:
    """Load a single committed `route_equivalence_*_v1.jsonl` artifact.

    - Skips blank lines.
    - Validates each row's `schema_version` is in
      ``SUPPORTED_ROUTE_EQUIVALENCE_SCHEMA_VERSIONS``; raises ``ValueError``
      with the offending value, line number (1-based), and path otherwise.
    - Returns records in the file's natural order. The writer emits
      ``sorted(records, key=lambda r: r.record_id)``, so consumers can rely
      on canonical order without a re-sort.
    - Raises ``FileNotFoundError`` if ``path`` is not a file.
    """


def load_route_equivalence_manifests(
    paths: Sequence[Path],
) -> list[RouteEquivalenceRecord]:
    """Load and concatenate multiple manifests deterministically.

    - Calls ``load_route_equivalence_manifest`` for each path in order.
    - Dedupes by ``record_id`` (first occurrence wins).
    - Returns the deduped list **sorted by ``record_id``** so callers
      get the same ordering whether they passed [c1, c2] or [c2, c1].
    - Empty ``paths`` returns ``[]``.
    """
```

### 6.2 Shadow payload — `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.lexicon_phase_b.route_equivalence_loader import (
    load_route_equivalence_manifests,
)
from src.lexicon_phase_b.schemas import RouteEquivalenceRecord

ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1 = "dmb_route_equivalence_shadow_v1"


def load_route_equivalence_shadow_records(
    paths: Sequence[Path],
) -> list[RouteEquivalenceRecord]:
    """Resolve each path to a real file, then call the lexicon-loader concat.

    Raises ``FileNotFoundError`` for any missing path. Order-preserving;
    delegates dedup + record sort to ``load_route_equivalence_manifests``.
    """


def build_route_equivalence_shadow_payload(
    *,
    scenario_campaign_id: str,
    records: Sequence[RouteEquivalenceRecord],
    source_paths: Sequence[Path],
) -> dict[str, Any]:
    """Build the per-scenario shadow diagnostic.

    Pure / deterministic for fixed inputs. Does not mutate inputs.
    Returns dict with keys (in this exact order, JSON-friendly):

        {
            "schema": ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
            "scenario_campaign_id": scenario_campaign_id.strip(),
            "edges_total": len(records),
            "edges_for_scenario_campaign": <int — records whose campaign_id
                                              equals scenario_campaign_id>,
            "campaign_ids": <sorted list[str] of unique campaign_ids in records>,
            "source_paths": [str(p) for p in source_paths],   # input order
        }

    If ``records`` is empty, ``edges_total`` and
    ``edges_for_scenario_campaign`` are 0; ``campaign_ids`` is ``[]``.
    """
```

**Determinism rule:** for any fixed `(scenario_campaign_id, records, source_paths)`, this function returns dict-equal output across calls. No timestamps, no UUIDs, no environment reads.

### 6.3 Harness wiring — `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`

**One** new CLI flag, registered at the same indentation/style as existing args around lines 656–820:

```python
parser.add_argument(
    "--route-equivalence-jsonl",
    type=Path,
    action="append",
    default=None,
    help=(
        "Path to a committed route_equivalence_*_v1.jsonl artifact. May be "
        "passed multiple times to combine campaigns (e.g. C1 + C2). "
        "Shadow-only: when set, each natural-gold scenario row gains a "
        "'shadow_route_equivalences' diagnostic field. Legacy lexicon "
        "seeds remain the active source; no retrieval or grading change."
    ),
)
```

**Loading site:** after the existing `shadow_lexicon = build_campaign_lexicon(...)` block (around lines 1033–1045 in the natural-gold branch) and **before** `for scenario in gold.get("scenarios") or []:`, add:

```python
route_equivalence_records = None
route_equivalence_paths_resolved: list[Path] = []
route_equivalence_load_error = ""
if args.route_equivalence_jsonl:
    try:
        route_equivalence_paths_resolved = [
            Path(p).resolve() for p in args.route_equivalence_jsonl
        ]
        route_equivalence_records = load_route_equivalence_shadow_records(
            route_equivalence_paths_resolved
        )
    except (OSError, ValueError) as exc:  # shadow mode must never break the run
        route_equivalence_records = None
        route_equivalence_load_error = f"{type(exc).__name__}: {exc}"
```

**Emission site:** inside the per-scenario loop, immediately after the existing block that sets `row["shadow_token_resolution"]` (the `if shadow_lexicon is not None: ... else: ...` block ending around line 1133), add:

```python
if route_equivalence_records is not None:
    row["shadow_route_equivalences"] = build_route_equivalence_shadow_payload(
        scenario_campaign_id=str(scen.get("campaign_id") or default_campaign),
        records=route_equivalence_records,
        source_paths=route_equivalence_paths_resolved,
    )
elif args.route_equivalence_jsonl:
    row["shadow_route_equivalences"] = {
        "schema": ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
        "error": route_equivalence_load_error or "load_failed",
    }
# When the flag is unset, the field is intentionally omitted from the row
# so default natural-gold runs remain byte-identical to current main.
```

**Imports:** add to the existing import block near `from evals.sentence_routing_retrieval_falsification.token_resolver_shadow import (...)`:

```python
from evals.sentence_routing_retrieval_falsification.route_equivalence_shadow import (
    ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
    build_route_equivalence_shadow_payload,
    load_route_equivalence_shadow_records,
)
```

**Invariant:** when `--route-equivalence-jsonl` is **not** set, every other field on every row in the output is **byte-identical** to current `main` for the same `--records-jsonl` + `--gold` inputs. The diagnostic is purely additive when the flag is on.

### 6.4 Tests — `tests/lexicon_phase_b/test_route_equivalence_loader.py` (NEW)

Mirror the shape of `test_route_equivalence_artifacts_byte_stable.py` (parametrized `CASES`, `pytest`, no third-party fixtures). Required tests:

1. `test_loader_returns_canonical_record_id_order_for_committed_artifact` — for each campaign in `CASES`, load via `load_route_equivalence_manifest` and assert `[r.record_id for r in records] == sorted([r.record_id for r in records])`. (No magic counts; uses the artifact itself as ground truth.)
2. `test_loader_concat_dedupes_and_sorts_by_record_id` — pass `[c1_path, c2_path, c1_path]` to `load_route_equivalence_manifests`; assert the result equals the union deduped and sorted by `record_id`. Confirms first-occurrence wins by checking object identity / equality on a known duplicate.
3. `test_loader_rejects_unsupported_schema_version` — write a synthetic JSONL via `tmp_path` with `{"schema_version": "9.9.9", ...}` (one valid line plus this bad line); assert `ValueError` whose message includes the bad version and the file path. Use the rest of the row from a `RouteEquivalenceRecord(...).model_dump(mode="json")` to keep it well-formed apart from the bumped version.
4. `test_loader_skips_blank_lines` — write a JSONL with blank lines interleaved between two valid rows; assert exactly 2 records are returned.
5. `test_loader_raises_for_missing_path` — `tmp_path / "nope.jsonl"`, expect `FileNotFoundError`.

### 6.5 Tests — `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` (EXTEND)

Append the following (do **not** delete or rewrite the two existing tests). Use `Path(__file__).resolve().parents[1]` as `_REPO_ROOT` (already established in the file):

1. `test_route_equivalence_shadow_payload_is_deterministic` — load both committed artifacts via `load_route_equivalence_shadow_records`; call `build_route_equivalence_shadow_payload` twice with `scenario_campaign_id="longmont-c1"` and identical inputs; assert the two dicts are equal.
2. `test_route_equivalence_shadow_payload_for_c1s1_campaign_id` — `scenario_campaign_id="longmont-c1"`, both artifacts loaded; assert:
   - `payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1`
   - `payload["scenario_campaign_id"] == "longmont-c1"`
   - `payload["edges_total"] == len(records)` (computed from the loader, not hardcoded)
   - `payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")`
   - `payload["campaign_ids"] == sorted({r.campaign_id for r in records})`
   - `payload["source_paths"] == [str(p) for p in source_paths]`
3. `test_route_equivalence_shadow_payload_for_c1s2_campaign_id` — same shape with `scenario_campaign_id="longmont-c1"` (Campaign 1 sessions 1–3 all live in `longmont-c1`).
4. `test_route_equivalence_shadow_payload_for_c1s3_campaign_id` — same shape, same campaign.
5. `test_route_equivalence_shadow_payload_unknown_campaign_returns_zero_match` — `scenario_campaign_id="longmont-c99"`; assert `edges_for_scenario_campaign == 0` and `edges_total > 0` and `campaign_ids` lists the real campaigns from the records.
6. `test_breadcrumb_query_run_help_advertises_route_equivalence_jsonl_flag` — call `subprocess.run(["uv", "run", "python", "-m", "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run", "--help"], capture_output=True, text=True, check=True)` and assert `"--route-equivalence-jsonl"` is in stdout. **Skip if `subprocess` is sandboxed** by checking `shutil.which("uv")` and emitting `pytest.skip("uv not available")` — do not hard-fail the suite for environment reasons.

C1S1, C1S2, C1S3 all share `campaign_id="longmont-c1"`; tests #2–#4 are intentionally redundant on the campaign axis to lock the invariant that the payload is **identical** across the three sessions for fixed inputs (the user explicitly named C1S1–C1S3, so we keep three named tests rather than one parametrized one — easier to grep and easier to debug a regression).

### 6.6 README update — `evals/sentence_routing_retrieval_falsification/README.md`

Add the following subsection **immediately after** the existing "Route equivalence manifests (Phase B)" block (current line ~213) and **before** the `Example 3-run acceptance loop` example. Title and content shape:

```markdown
##### Shadow consumption (Phase C entry)

Pass `--route-equivalence-jsonl` (repeatable) to `breadcrumb_query_run` to load
the committed `route_equivalence_*_v1.jsonl` artifacts as a shadow diagnostic.
Each natural-gold scenario row gains a `shadow_route_equivalences` field with
schema `dmb_route_equivalence_shadow_v1`: edge counts, the full set of campaign
IDs present, and the source paths in input order. **Shadow-only:** retrieval,
grading, and the existing `shadow_token_resolution` field are unchanged; legacy
lexical seeds remain the active source. The field is omitted entirely when the
flag is unset (default runs remain byte-identical to current main).

Example:

​```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl evals/sentence_routing_retrieval_falsification/artifacts/last_session1_c1_breadcrumb_records.jsonl \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json \
  --retrieval-only \
  --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl \
  --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl
​```
```

(Replace the zero-width spaces in the inner triple-backticks with normal triple-backticks when copying.)

## §7 Verification command (run all of these; paste output in the PR body)

Run from the repo root after your changes are staged. **Do not** filter or summarize — paste the literal command output.

```bash
# 1. Lexicon-only loader tests (new file)
uv run pytest tests/lexicon_phase_b/test_route_equivalence_loader.py -q

# 2. Existing Phase B byte-stable regression must still pass (regression guard)
uv run pytest tests/lexicon_phase_b/ -q

# 3. Harness-wiring shadow payload tests (extends existing file; existing two tests must still pass)
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# 4. Manifest CLI determinism still green (regression guard for PR #3)
uv run python scripts/build_route_equivalence_manifests.py --check

# 5. CLI flag visible from --help (smoke that argparse wiring is real)
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run --help 2>&1 | grep -- '--route-equivalence-jsonl'

# 6. Token-resolution + benchmark-seeds suite untouched (collision guard for PR #1 lesson)
uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q
```

**Acceptance:**

- (1) and (3) report the new tests passing alongside the pre-existing ones.
- (2) reports `>=21 passed` (16 existing + your 5 new loader tests).
- (4) prints `OK <path>` lines for both campaigns.
- (5) prints **at least one line** containing `--route-equivalence-jsonl`.
- (6) reports `28 passed` (unchanged from PR #2/PR #3 baseline).

If any command fails, **do not** open the PR. Iterate locally until all six are green, then paste the literal output in the PR body.

## §8 Reporting contract (in the PR body)

Include exactly these sections, in this order:

1. **`git diff --stat origin/main...HEAD`** — pasted verbatim. Should list **only** the seven entries from §4. Any other path is scope creep; revert it.
2. **§7 verification output** — all six commands' stdout, including any pytest summary lines.
3. **One-paragraph summary** of behavior: what the new flag does, what the new field looks like (one example payload value), and the explicit statement: *"With the flag unset, output is byte-identical to current main."*
4. **Scope-confirmation checklist** — paste this and tick each box:
   - [ ] No edits to `src/lexicon_phase_b/schemas.py` or `route_equivalence_manifest.py`.
   - [ ] No edits to `scripts/build_route_equivalence_manifests.py`.
   - [ ] No edits to any committed JSONL under `evals/.../artifacts/lexicon/`.
   - [ ] No edits to `token_resolver_shadow.py` or `breadcrumb_query_grader.py`.
   - [ ] No edits to `src/agent/session_memory_query.py` or any planner-runtime code.
   - [ ] No new tests at `tests/test_token_resolution_*` or `tests/test_route_equivalence_*` basenames at the `tests/` root.
   - [ ] No edits to `Docs/Plans/PLAN-*.md`, `Docs/Plans/CHECKLIST-*.md`, or any other handoff under `Docs/Plans/HANDOFF-*.md` or `Docs/Plans/archive/**`.
   - [ ] No edits to any `.cursor/rules/*.mdc` or `corpus/**` path.

If any checkbox is unchecked, the PR will be closed and re-briefed.

## §9 Rubric we will judge by (parent will copy this into `external_pull_requests[].rubric_when_we_judge` after merge)

- The `--route-equivalence-jsonl` flag is **shadow-only**: with the flag unset, output is byte-identical to current `main` for the same `--records-jsonl` + `--gold` inputs.
- The new lexicon loader lives under `src/lexicon_phase_b/`; lexicon-only tests for it live under `tests/lexicon_phase_b/`. (PR #2 rubric carryover.)
- Harness-wiring tests live in `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` (extends existing file; does not collide with `tests/test_token_resolution_*` basenames). (PR #1 supersession lesson.)
- Test-side counts are computed from the loaded artifacts (no hardcoded magic numbers) so the suite stays correct as the registry grows.
- `shadow_route_equivalences` schema is `dmb_route_equivalence_shadow_v1`; field is **omitted** when the flag is unset, **populated** with an `error` payload when load fails, **populated** with the diagnostic dict when load succeeds — and never raises into the run.
- README documents the flag + schema + the explicit "shadow-only, legacy seeds active" contract.

---

**Dispatch model:** `composer-2` (mechanical work; design is settled in §6).
**Estimated diff size:** ~250–350 LOC across 7 files, ~150 LOC of which is tests.
**Out-of-band channel for blockers:** if any §6 contract is genuinely impossible (e.g. an upstream type doesn't exist), stop and report — do **not** improvise an alternative shape. The cost of one extra round-trip is far less than the cost of a supersession PR.

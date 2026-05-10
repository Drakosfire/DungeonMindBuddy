# HANDOFF — Make `shadow_route_equivalences.source_paths` workspace-relative (CWD-invariant) at the harness boundary

> **COMPLETED — 2026-05-10T21:09Z.** Shipped via [PR #5](https://github.com/Drakosfire/DungeonMindBuddy/pull/5) (`main` merge commit `40be747a87d0eecb4dc1c865f236f3728cf1d4d4`). Single round of review (commit `ec1f55fa`); APPROVE was demoted to a `COMMENTED` verdict banner under the standard self-review fallback (`pullrequestreview-4259919574`). Diff held to exactly the §4 allowlist (3 files, 87 +/4 -). Adds `_workspace_relative_posix(path, workspace_root)` to `route_equivalence_shadow.py`; `build_route_equivalence_shadow_payload` gains a required `workspace_root: Path` kwarg; the harness wires `_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]`. New harness-boundary test `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` spawns `breadcrumb_query_run` from `_REPO_ROOT` and from `_REPO_ROOT / "tests"` via `uv run --directory _REPO_ROOT …` and asserts full-payload byte-identity (count `10 → 11`). All §7 commands green at PR HEAD; producer-side untouched (`tests/lexicon_phase_b/ -q` unchanged at 22 passed both sides; `--check` OK both manifests). Post-merge doc-sync landed in `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (v11) and `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (top-of-file PR header + Reanchor + Phase C provenance-hardening evidence + new session-log entry). New rubric bullet captured in `external_pull_requests[github-pr-5].rubric_when_we_judge`: provenance fields in shadow diagnostics must be rendered at the harness boundary, with CWD-invariance tested by spawning subprocesses from at least two different CWDs and asserting full-payload equality. **Archived for historical reference; do not re-dispatch.**

**Created:** 2026-05-10 (UTC).
**Status:** COMPLETED — see banner above. (Was: ACTIVE — dispatch this to one external/Codex subagent. **One PR.** Do not split into multiple PRs.)
**Parent agent:** Cursor agent; dispatcher is responsible for the post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, milestone progress **M2 in_progress · M3 in_progress**). This handoff closes the **PR #4 known follow-up** and is the **precondition** for the cohort-baseline slice (Phase 4 diagnostics input / promotion-gate input).

---

## §1 Mission

Make `shadow_route_equivalences.source_paths` (emitted by `breadcrumb_query_run` when `--route-equivalence-jsonl …` is passed) **workspace-relative POSIX strings** so the field is byte-identical regardless of operator CWD, absolute install path, or `Path.resolve()` differences across machines.

## §2 Why this slice (context for the subagent)

- **PR #4** (`main` merge commit `21e84392da03095377b4de36defb82edfc37c741`, 2026-05-10T16:22Z) shipped the Phase C **entry** shadow consumer: `--route-equivalence-jsonl PATH` (repeatable) loads the committed JSONL artifacts from PR #3 and emits a per-scenario `shadow_route_equivalences` (`dmb_route_equivalence_shadow_v1`) field. Legacy retrieval and grading are unchanged.
- The merged code calls `Path(p).resolve()` and stores `[str(p) for p in source_paths]` in the payload (`evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py:46`, fed by `breadcrumb_query_run.py:1066–1077`). This means **`source_paths` is CWD-dependent and absolute** — the harness output diverges between operators even with identical inputs. PR #4's `judgment_record.notes` flagged this:
  > the `shadow_route_equivalences.source_paths` field stores `Path.__str__` of the resolved input which is machine-dependent (absolute vs relative depends on the operator's CWD). Capture as a follow-up to make provenance fields workspace-relative when manifest-hash / provenance lane lands.
- **Why now:** the **next** planned slice is committing a **cohort `shadow_route_equivalences` baseline** for C1S1–C1S3 (the priority `(a)` in `next_gate_command`). That baseline needs a byte-stable regression contract identical to the one PR #3 established for the source artifacts. With `source_paths` machine-dependent, no baseline can be byte-stable.
- **Scope honesty — what this slice does NOT do:**
  - No retriever rewiring (still Phase C **exit**, separate slice).
  - No grading change.
  - No new gold.
  - No producer-side change to the committed JSONL artifacts (no `manifest_hash`, no provenance fields). That's a sibling slice on a different lane.
  - No new CLI flags. The contract is purely how the existing field is rendered.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — the §4 allowlist / §5 denylist / §7 verification contract, and the "**test the boundary that owns the rubric**" invariant that this PR will be reviewed against.
2. **`evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py`** (the whole file — 47 lines) — the consumer-side module you will modify. Note the existing `source_paths: Sequence[Path]` parameter and the `[str(p) for p in source_paths]` line at the end of the payload dict.
3. **`evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`** lines **1065–1078** (load + resolve) and **1167–1178** (per-scenario emission, where `build_route_equivalence_shadow_payload` is called and where the `error` payload also emits). Read these line ranges, not the whole 1400-line file.
4. **`tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`** — the existing 246-line test module you will extend. Read in particular:
   - lines **85–146** (the deterministic-payload tests; they assert `payload["source_paths"] == [str(p) for p in source_paths]` — those assertions need to migrate to the new representation).
   - lines **181–245** (`_run_breadcrumb_query_run_subprocess`, `test_route_equivalence_flag_is_additive_only_at_harness_boundary`, `test_route_equivalence_load_failure_emits_error_payload_and_run_survives`) — your new harness-boundary CWD-invariance test mirrors the subprocess shape and uses `cwd=…` to vary working directories.
5. **`src/bootstrap_env.py`** — read lines **1–15**. The module-level `_REPO_ROOT = Path(__file__).resolve().parents[1]` is the canonical pattern in this repo for deriving the workspace root from a known module file. Use the same shape.
6. **`tests/conftest.py`** — confirm session-autouse `load_dungeonmindbuddy_dotenv()` is wired (live tests don't need exported keys; see `.cursor/rules/dungeonbuddy-environment.mdc`). You should not need to touch this; just verify it's present.
7. **`Docs/Plans/archive/2026-05-10/handoffs/HANDOFF-phase-c-route-equivalence-shadow-consumer.md`** — historical context for what PR #4 *did* land. **Do not edit it.** This handoff intentionally does not repeat the schema discussion from there; the `dmb_route_equivalence_shadow_v1` payload shape (with the new path representation) is the only shape that exists.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| **Modify** | `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Render `source_paths` as repo-root-relative POSIX strings via a single helper. Accept an explicit `workspace_root: Path` keyword-only parameter (see §6.1). **No other behavioral change.** |
| **Modify** | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | At the call site (~lines 1167–1178) pass an explicit `workspace_root=` derived once at the top of the run (see §6.2). The argparse surface, the error-payload branch, and every other line stay byte-identical. |
| **Modify** | `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Update the four existing `assert payload["source_paths"] == [str(p) for p in source_paths]` assertions in lines 85–146 to the new representation, and **append** the new harness-boundary CWD-invariance test described in §6.3. **Do not delete or rewrite** the two existing harness-boundary tests (`…flag_is_additive_only_at_harness_boundary`, `…load_failure_emits_error_payload_and_run_survives`). |

Your `git diff --stat origin/main...HEAD` MUST be expressible from these **three** entries and **only** these three entries. Anything else is scope creep — see §5.

## §5 Files explicitly OUT OF SCOPE (denylist + concrete collision risks)

You will be tempted to "fix while I'm here." Resist. Each item below has a concrete risk attached.

| Path | Why out of scope | Concrete collision/regression risk |
|---|---|---|
| `src/lexicon_phase_b/schemas.py` | Schema is committed and consumed by the byte-stable artifact tests. | Any field rename breaks `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`. The shadow payload reads `record.campaign_id`; that's it. Don't touch the dataclass. |
| `src/lexicon_phase_b/route_equivalence_loader.py` | Loader is pure JSONL → records; this slice changes only **provenance rendering** at the harness boundary. | Adding repo-root logic into the loader leaks workspace concerns into a lexicon-only module that has no business knowing them. **Do the rendering at the consumer, not the loader.** |
| `src/lexicon_phase_b/route_equivalence_manifest.py` | Producer-side. | Touching this puts you on the manifest-hash lane, which is a separate PR. |
| `src/lexicon_phase_b/__init__.py` | No new exports needed for this slice. | Adding exports here suggests producer-side scope creep; revert it during review. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c*_v1.jsonl` | Canonical committed artifacts. | **Do not regenerate.** Producer-side; outside this slice's contract. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/benchmark_lexicon_seeds_v1.json` | Legacy benchmark seeds. | Anything here re-litigates the Phase B/C split. |
| `evals/sentence_routing_retrieval_falsification/token_resolver_shadow.py` | Legacy shadow module — separate diagnostic with its own provenance shape. | Don't "while you're in there" port `shadow_token_resolution` paths to be repo-root-relative as well. That's a separate decision and a separate PR. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | Grader. | Any change makes this a grading-change PR. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_canvas_payload.py`, `…breadcrumb_query_rank_report.py`, `…c1s*_benchmark_canvas_emit.py` | Canvas / report consumers. | Out of scope; canvases haven't read `shadow_route_equivalences` yet (Phase 4 work). |
| `scripts/build_route_equivalence_manifests.py` | Producer-side CLI. | The dispatcher uses `--check` as a regression gate; do not perturb it. |
| `tests/lexicon_phase_b/**` | Lexicon-only tests. The byte-stable artifact tests, loader tests, manifest tests, route-id tests, and entity-kind tests all live here. | Any change here implies a producer-side scope shift. The harness-boundary tests for this slice live in `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`. |
| `tests/test_token_resolution_*.py`, `tests/test_benchmark_lexicon_seeds.py` | Unrelated existing suites. | **Hard collision risk.** PR #1 was closed precisely because it touched this namespace. Do not create new tests at any `tests/test_token_resolution_*` basename. |
| `src/agent/session_memory_query.py` | Planner-runtime path. | Phase C **exit** wiring; not this slice. |
| `src/contracts/npc_registry.py`, `src/bootstrap_env.py` | Read-only references. | `bootstrap_env._REPO_ROOT` is a **pattern** to mirror, not a symbol to import (the consumer module is one extra `parents[]` level deeper than `bootstrap_env`). |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`, `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Plan/checklist sync is the **parent agent's** atomic post-merge job. | If the subagent edits these, the parent will revert and re-brief. |
| `Docs/Plans/archive/**` | Archived material is historical. | Read-only. |
| Any `Docs/Plans/HANDOFF-*.md` other than this one | Each handoff names exactly one slice. | Editing other handoffs muddles the active-vs-archived boundary. |
| Any `corpus/**` | Corpus is GM-private. | See `.cursor/rules/corpus-pii-and-llm-payloads.mdc`. |
| Any `.cursor/rules/*.mdc`, `.cursor/skills/**` | Rules and skills are parent-managed. | Out of scope. |
| Any `evals/sentence_routing_retrieval_falsification/README.md` text | The existing prose still describes the harness correctly. | If a doc tweak feels unavoidable, surface it in the PR description and let the dispatcher decide whether it's in scope. Default answer: no. |

**Naming hard rules:**
- The harness-boundary CWD-invariance test you add **belongs in** the existing `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` (alongside the two PR #4 round-2 tests it mirrors structurally).
- Do **not** create a new `tests/test_route_equivalence_*` file at the `tests/` root; that name belongs under `tests/lexicon_phase_b/`, and this slice has no lexicon-only tests to add.

## §6 Implementation contract

### 6.1 `route_equivalence_shadow.py`

Add a small helper and one keyword-only parameter to the existing builder. Do not add new classes; do not change the schema id; do not change any other field in the payload.

```python
# evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py
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
    # Unchanged from current main.
    ...


def _workspace_relative_posix(path: Path, workspace_root: Path) -> str:
    """Render ``path`` as a workspace-relative POSIX string when possible.

    Falls back to ``path.name`` when ``path`` is **not** under
    ``workspace_root`` (e.g. an operator passes a path from a sibling
    checkout). The fallback is deterministic and CWD-invariant: it
    drops provenance hierarchy but preserves the filename so the
    diagnostic still names what was loaded.
    """
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.name


def build_route_equivalence_shadow_payload(
    *,
    scenario_campaign_id: str,
    records: Sequence[RouteEquivalenceRecord],
    source_paths: Sequence[Path],
    workspace_root: Path,
) -> dict[str, Any]:
    """Build the per-scenario shadow diagnostic.

    ``source_paths`` is rendered as workspace-relative POSIX strings
    (``forward/slash/style.jsonl``) so the field is byte-identical
    across operator CWDs and absolute install paths. Falls back to
    ``Path.name`` for any path outside ``workspace_root`` (rare).
    """
    normalized_campaign_id = scenario_campaign_id.strip()
    campaign_ids = sorted({r.campaign_id for r in records})
    edges_for_scenario = sum(
        1 for r in records if r.campaign_id == normalized_campaign_id
    )
    return {
        "schema": ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
        "scenario_campaign_id": normalized_campaign_id,
        "edges_total": len(records),
        "edges_for_scenario_campaign": edges_for_scenario,
        "campaign_ids": campaign_ids,
        "source_paths": [
            _workspace_relative_posix(p, workspace_root) for p in source_paths
        ],
    }
```

Determinism / ordering rules:
- The five existing top-level keys (`schema`, `scenario_campaign_id`, `edges_total`, `edges_for_scenario_campaign`, `campaign_ids`, `source_paths`) and their order are preserved exactly. The schema id stays `dmb_route_equivalence_shadow_v1` (no version bump).
- `source_paths` order matches the order of the input `source_paths` argument. **Do not** sort — caller-supplied order is the contract (matches the order of `--route-equivalence-jsonl` flags on the CLI).
- POSIX style means forward slashes via `Path.as_posix()`. Do not use `os.sep` or `str(Path(...))` (Windows paths leak through `__str__`).

### 6.2 `breadcrumb_query_run.py`

Derive the workspace root once and thread it through the two existing call sites. Mirror the `bootstrap_env._REPO_ROOT` pattern but compute it locally — `breadcrumb_query_run.py` lives at `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`, so `Path(__file__).resolve().parents[2]` is the repo root.

Inside `main()` (or wherever the run-scoped state is currently assembled in the natural-gold branch — same scope as `route_equivalence_paths_resolved`), add:

```python
# breadcrumb_query_run.py — top of the natural-gold branch, near route_equivalence_paths_resolved
_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
```

Then **at the existing call site** (currently lines ~1167–1172), add a single keyword arg:

```python
if route_equivalence_records is not None:
    row["shadow_route_equivalences"] = build_route_equivalence_shadow_payload(
        scenario_campaign_id=str(scen.get("campaign_id") or default_campaign),
        records=route_equivalence_records,
        source_paths=route_equivalence_paths_resolved,
        workspace_root=_HARNESS_WORKSPACE_ROOT,  # NEW
    )
```

Do **not** change the error-payload branch (~lines 1173–1177) — the error payload doesn't include `source_paths`, so it's unaffected.

Do **not** add a new CLI flag for the workspace root. The harness pins it to the repo root from `__file__`; that's the contract.

### 6.3 `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`

Three categories of changes:

**A. Update existing payload-shape assertions (lines 85–146).** The four tests `test_route_equivalence_shadow_payload_is_deterministic`, `…for_c1s1_campaign_id`, `…for_c1s2_campaign_id`, `…for_c1s3_campaign_id` currently assert:

```python
assert payload["source_paths"] == [str(p) for p in source_paths]
```

Replace each with the new contract. Pass the explicit `workspace_root=_REPO_ROOT` at the call sites and assert against POSIX-style repo-relative strings. The expected list for the standard fixture is:

```python
expected_source_paths = [
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl",
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl",
]
assert payload["source_paths"] == expected_source_paths
```

Do **not** add a `Sequence`-of-`Path` round-trip via `Path(s)` in the assertion — assert raw POSIX strings.

`test_route_equivalence_shadow_payload_unknown_campaign_returns_zero_match` (lines ~149–159) does not currently assert on `source_paths`; you only need to update its `build_route_equivalence_shadow_payload(...)` call to pass `workspace_root=_REPO_ROOT`.

**B. Do not modify** the two existing harness-boundary tests (`…flag_is_additive_only_at_harness_boundary` at line 200, `…load_failure_emits_error_payload_and_run_survives` at line 228). They continue to pass because:
- Test A still calls the harness twice (with and without the flag), still pops `shadow_route_equivalences` from the flagged row, and still asserts byte-identity of all *other* fields. The new `source_paths` representation is itself byte-stable across runs from the **same** CWD, so the test does not need updating to keep passing.
- Test B does not depend on `source_paths` (the error branch doesn't emit it).

**C. Add ONE new harness-boundary test** that exercises the §9 "byte-identical across CWDs" guarantee. Mirror the shape of `test_route_equivalence_flag_is_additive_only_at_harness_boundary`. Skeleton:

```python
def test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant(
    tmp_path: Path,
) -> None:
    """`shadow_route_equivalences.source_paths` must be byte-identical
    across operator CWDs (regression for the PR #4 follow-up)."""
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_a = tmp_path / "from_repo_root.json"
    out_b = tmp_path / "from_subdir.json"

    extra_args = [
        "--route-equivalence-jsonl",
        str(_route_equivalence_paths()[0]),
        "--route-equivalence-jsonl",
        str(_route_equivalence_paths()[1]),
    ]

    # Run 1: from the repo root.
    run_a = _run_breadcrumb_query_run_subprocess_with_cwd(
        output_path=out_a, extra_args=extra_args, cwd=_REPO_ROOT,
    )
    # Run 2: from an unrelated subdirectory of the repo (e.g. tests/).
    cwd_subdir = _REPO_ROOT / "tests"
    assert cwd_subdir.is_dir()
    run_b = _run_breadcrumb_query_run_subprocess_with_cwd(
        output_path=out_b, extra_args=extra_args, cwd=cwd_subdir,
    )
    assert run_a.returncode == 0, run_a.stderr
    assert run_b.returncode == 0, run_b.stderr

    rows_a = json.loads(out_a.read_text(encoding="utf-8"))["results"]
    rows_b = json.loads(out_b.read_text(encoding="utf-8"))["results"]
    assert len(rows_a) == len(rows_b) > 0

    expected_source_paths = [
        "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl",
        "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl",
    ]
    for row_a, row_b in zip(rows_a, rows_b, strict=True):
        payload_a = row_a["shadow_route_equivalences"]
        payload_b = row_b["shadow_route_equivalences"]
        assert payload_a == payload_b, "shadow payload must be CWD-invariant"
        assert payload_a["source_paths"] == expected_source_paths
```

You will need a small variant of the existing helper, e.g.:

```python
def _run_breadcrumb_query_run_subprocess_with_cwd(
    *, output_path: Path, extra_args: list[str], cwd: Path,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "uv", "run", "python", "-m",
        "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run",
        "--records-jsonl", str(_FIXTURE_JSONL),
        "--gold", str(_NATURAL_GOLD_C1S1),
        "--retrieval-only",
        "--output", str(output_path),
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
```

Place the helper alongside `_run_breadcrumb_query_run_subprocess` (do **not** modify the existing helper — the two existing tests still call it). Pass absolute paths (already done by `_FIXTURE_JSONL` / `_NATURAL_GOLD_C1S1` / `_route_equivalence_paths()`) so the args themselves are CWD-independent — the test is about how `source_paths` is *rendered* in the payload.

## §7 Verification commands

The worker must run **every** command and paste the output into the PR body. The reviewer reruns each. **Every behavioral guarantee in §9 below must be exercised by at least one command here, at the boundary the guarantee describes.**

```bash
# Sanity: producer-side surfaces are unchanged.
uv run pytest tests/lexicon_phase_b/ -q

# Harness-boundary suite, including the new CWD-invariance test (count goes 10 -> 11).
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# Targeted run of just the new boundary test (proves the new contract in isolation).
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py::test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant -q

# Producer-side regression gate — committed JSONL must remain byte-stable.
uv run python scripts/build_route_equivalence_manifests.py --check

# Smoke: run from the repo root and from tests/, eyeball the source_paths field.
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl evals/sentence_routing_retrieval_falsification/artifacts/last_session1_c1_breadcrumb_records.jsonl \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json \
  --retrieval-only \
  --output /tmp/pr5-smoke-from-root.json \
  --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl \
  --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl
python -c "import json; r=json.load(open('/tmp/pr5-smoke-from-root.json'))['results']; print(r[0]['shadow_route_equivalences']['source_paths'])"
```

The smoke command's printed `source_paths` MUST be exactly:

```python
['evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl', 'evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl']
```

…regardless of the operator's absolute install path or current working directory.

## §8 Reporting contract

In the PR body the worker MUST include:

1. **`git diff --stat origin/main...HEAD` filtered to the §4 allowlist paths only.** Three files. Anything else is scope creep.
2. **Verbatim §7 output** — pass/fail counts (e.g. `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q -> 11 passed`), and the raw `source_paths` printout from the smoke step.
3. **One-paragraph "what stayed unchanged"** — call out at least: (a) the schema id (`dmb_route_equivalence_shadow_v1`) and the five non-`source_paths` payload keys; (b) PR #4's two harness-boundary tests still pass without modification; (c) producer-side artifacts (`route_equivalence_longmont_c*_v1.jsonl`) are untouched and `--check` is OK.

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet names the §7 command that verifies it. **Behavioral guarantees are paired with commands at the boundary the guarantee describes** (`.cursor/rules/external-agent-pr-loop.mdc` invariant #2).

- [ ] **`source_paths` is rendered as repo-root-relative POSIX strings** in the payload — verified by the new test `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` and by the smoke-step printout.
- [ ] **`source_paths` is byte-identical across operator CWDs** for the same harness invocation — verified at the **harness boundary** by `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` (subprocess run from `_REPO_ROOT` and from `_REPO_ROOT / "tests"`, payload equality asserted). Not just verified by a unit-level call to `build_route_equivalence_shadow_payload`.
- [ ] **Schema id and payload key set are unchanged.** Schema is still `dmb_route_equivalence_shadow_v1`; the payload still has exactly `{schema, scenario_campaign_id, edges_total, edges_for_scenario_campaign, campaign_ids, source_paths}` and key order is preserved — verified by the four updated `test_route_equivalence_shadow_payload_*` tests.
- [ ] **PR #4 byte-identity-when-flag-unset invariant survives unchanged** — verified by `test_route_equivalence_flag_is_additive_only_at_harness_boundary` continuing to pass without modification.
- [ ] **PR #4 load-failure-emits-error invariant survives unchanged** — verified by `test_route_equivalence_load_failure_emits_error_payload_and_run_survives` continuing to pass without modification.
- [ ] **Producer-side artifacts and tests are untouched.** `uv run python scripts/build_route_equivalence_manifests.py --check` is OK; `uv run pytest tests/lexicon_phase_b/ -q` is `17 passed`.
- [ ] **No files outside §4 are touched.** Verified by `git diff --stat origin/main...HEAD` filtered to §4 (must be exactly three paths).

> **Reviewer reminder:** if a bullet describes a behavioral guarantee at a particular boundary (harness, dispatcher, writer), the §7 command that verifies it MUST exercise it at that boundary. Loader-side or unit-side coverage is necessary but not sufficient. This rubric was tightened by PR #4's round-1 trap; do not regress.

## §10 Out-of-band notes (optional)

- This slice intentionally does **not** address producer-side `manifest_hash` / provenance fields on the JSONL artifacts. That's the next M2-broader slice and will be its own handoff. After that lands, a `manifest_hash` field will likely appear in the consumer payload too (alongside the now-stable `source_paths`); this slice deliberately does not pre-shape the schema for that.
- This slice also does **not** commit a cohort `shadow_route_equivalences` baseline for C1S1–C1S3. That's the **next** consumer-side slice; **PR 5 is the byte-stability precondition** for that baseline. Once PR 5 lands, the baseline slice can pin the per-scenario `shadow_route_equivalences` payloads byte-for-byte.
- If the worker hits a sandbox / `gh pr create` issue, post the PR-body markdown back to the dispatcher and the dispatcher will open the PR by hand. Do **not** widen scope to "fix the sandbox while I'm here."

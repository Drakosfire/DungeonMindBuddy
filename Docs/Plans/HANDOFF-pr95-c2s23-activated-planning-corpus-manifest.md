---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description. Reviewers and parallel agents see one stable shape.
pr_body_template: |
  ## Summary
  Build a read-only C2S23 activated planning corpus manifest that composes existing recap/session-memory/prep/live-workspace/roll-table/hub sources into one session-scoped contract (source_role + authority + session scope + routes + allowed/forbidden uses). No retrieval, no admission, no corpus mutation.

  ## Verification (verbatim §7)
  {{paste command outputs after running §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{git diff --stat origin/main...HEAD, filtered to §4}}
  ```
---

# HANDOFF — PR95: C2S23 Activated Planning Corpus Manifest

**Created:** 2026-05-30 (UTC).
**Status:** ACTIVE — dispatch this to one external/Codex subagent. One PR. Do not split.
**Parent agent:** Cursor agent; dispatcher owns the post-merge doc-sync of `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md`, `Docs/Plans/CAPABILITY-INVENTORY-c2s23-planning-artifact-actions.md`, and `Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md` (roadmap step "PR92 — C2S23 Activated Planning Corpus Manifest"; git PR number is 95). Charter: `Docs/Plans/BENCHMARK-c2s23-dogfood-planning-charter.md` (PR94, merged).

---

## §1 Mission

Build a deterministic, **read-only** builder + CLI that emits a session-scoped C2S23 *activated planning corpus manifest* (canonical JSON + optional markdown mirror) enumerating every in-bounds planning source with its `source_role`, `authority`, session scope, routes, and allowed/forbidden uses.

## §2 Why this slice (context for the subagent)

- PR94 (`docs/eval: define C2S23 dogfood benchmark and capability inventory`, draft → merged on `main`) defined the benchmark charter, 22 seed questions, the manual baseline template, and the capability inventory. The inventory marks **"manifest-like source activation"** as `missing` and tags it **PR95**. The seed question `manifest-01` directly probes "can I query all relevant S23 sources in one pass with correct roles" and currently has no path.
- This slice converts "the operator must mentally compose corpus tree + session memory + prep scaffold + live workspace + roll tables + hub evidence" into **one machine-checkable activation object**. It defines *what is in bounds and what each source may prove* — the precondition for the later query/admission slice (roadmap PR93) and the instrumented dogfood re-run (roadmap PR94).
- This slice does **NOT**: implement retrieval, implement admission/ranking, mutate the corpus, embed anything, write route-equivalence records, or add any live-control feature/route/pane. It is a composition + validation + emission artifact only. The manifest *references* sources by route; it never copies corpus prose into itself.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — the §4 allowlist / §5 denylist / §7 verification contract this PR is reviewed against.
2. **`Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md`** — § "Source Role and Authority Axis" defines the two-axis vocabulary the manifest MUST carry (`source_role` table + `authority` table). This is the canonical schema source. Read-only here.
3. **`Docs/Plans/BENCHMARK-c2s23-dogfood-planning-charter.md`** — § "Source authority roles" (the 7-role authority vocabulary: `pre_canonical_evidence`, `canon_play`, `derived_memory`, `planning_scaffold`, `reference_tool`, `live_observation`, `audit`) and forbidden-for-play-fact rules. The manifest's `authority` axis MUST use exactly these values.
4. **`src/corpus/session_recap_paths.py`** — canonical helpers for recap-derivative routes (`normalized_recap_relpath`, `breadcrumbed_relpath`, `session_memory_jsonl_relpath`, `session_memory_meta_relpath`, `session_recaps_prefix`). Use these to resolve routes; do not hand-build recap paths.
5. **`src/live_play/session_bootstrap.py`** — mirror its CLI shape (argparse, `repo_root()` usage, deterministic JSON emission, `--out` / `--write` style). The manifest CLI should feel like a sibling of bootstrap.
6. **`evals/c2_live_prep/live/session_22/live_packet.json`** — the live workspace shape; read `campaign_id`, `session`, `known_roll_tables`, `context_packets`, `surface_catalog`. The manifest enumerates live-workspace files and registered roll tables from here.
7. **`evals/c2_live_prep/live/schemas/live_packet.schema.json`** — example of the repo's JSON-schema style; the new manifest schema should match its conventions (`$schema`, `required`, `additionalProperties: false`).
8. **`tests/conftest.py`** — confirm session-autouse `load_dungeonmindbuddy_dotenv()` is wired (no exported keys needed). NOTE: this builder is **deterministic and offline** — it must not call OpenAI. If you import anything that constructs an `OpenAI()` client at import time, isolate it.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/live_play/planning_corpus_manifest.py` | Builder + CLI: compose in-bounds C2S23 sources into the manifest object; emit canonical JSON (+ optional markdown mirror). Read-only. |
| Create | `tests/test_planning_corpus_manifest.py` | Unit + boundary tests (schema validity, role/authority correctness, route resolvability, no-mutation invariant, deterministic output). |
| Create | `evals/c2_live_prep/live/schemas/planning_corpus_manifest.schema.json` | JSON schema for `dmb_c2s23_planning_corpus_manifest_v0`. |
| Create | `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json` | Committed generated manifest artifact for C2S23 (the canonical example, schema-valid). |
| Create | `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.md` | Optional human-readable markdown mirror generated by the CLI. |
| Modify | `Docs/Plans/CAPABILITY-INVENTORY-c2s23-planning-artifact-actions.md` | Flip "manifest-like source activation" from `missing` to `supported`/`partial`; point at the new builder. |
| Modify | `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` | Reanchor block: set last green artifact + next gate (query/admission over manifest). |

> The agent's expected `git diff --stat` MUST be expressible from this allowlist. Any path not in this table will be reverted during review.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these:

| Path | Why this PR must not touch it |
|---|---|
| `src/agent/corpus_writer.py` | Manifest build is read-only; no write path may be added or imported for mutation. |
| `src/live_play/recap_ingest_pipeline.py` | Ingestion is upstream (PR92); the manifest consumes its *outputs* by route, it does not re-run or modify ingest. |
| `apps/live_control_server/**` | No new route/endpoint. Query/admission over the manifest is the NEXT slice, not this one. |
| `apps/live-control-ui/**` | No UI. This is a backend composition artifact only. |
| `src/lexicon_phase_b/**` | Route-equivalence *records* may be referenced by route, but this PR writes no equivalence artifacts and does not modify the manifest builders there. |
| `corpus/eldyrwild-markdown/**` | Campaign corpus is never mutated by this PR. The manifest references corpus files by relative route; it copies no prose. |
| `src/prompts/*.py` | No planner/prompt changes; manifest is not in the LLM-facing path here. |
| `evals/*/gold/*.json`, `evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json` | Benchmark gold/seed is frozen (PR94). "While I'm here" edits silently change the rubric. |

If the worker believes one of these is genuinely needed, stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### `src/live_play/planning_corpus_manifest.py`

A deterministic builder. No network, no corpus writes. The manifest **references** sources by relative route and never inlines corpus content.

```python
SCHEMA_ID = "dmb_c2s23_planning_corpus_manifest_v0"

# Closed vocab — mirror ROADMAP § "Source Role and Authority Axis".
SOURCE_ROLE = Literal[
    "table_notes", "play_recap", "session_memory", "prep_scaffold",
    "roll_table", "live_packet", "live_event", "fresh_recap", "hub_evidence",
]
# Closed vocab — mirror BENCHMARK charter § "Source authority roles".
AUTHORITY = Literal[
    "pre_canonical_evidence", "canon_play", "derived_memory",
    "planning_scaffold", "reference_tool", "live_observation", "audit",
]

@dataclass(frozen=True)
class ManifestEntry:
    source_id: str               # stable, deterministic id
    source_role: SOURCE_ROLE
    authority: AUTHORITY
    session_scope: list[int]     # e.g. [22] or [21, 22]
    route: str                   # corpus-relative or live-workspace-relative path
    route_exists: bool           # resolved against roots at build time
    allowed_uses: list[str]      # e.g. ["play_facts", "open_loops", "planning_context"]
    forbidden_uses: list[str]    # e.g. ["play_facts"] for prep_scaffold / roll_table
    notes: str | None = None     # corpus-rationale only; no per-task navigation hints

def build_planning_corpus_manifest(
    *,
    campaign_id: str,            # "longmont-c2"
    planning_session: int,       # 23
    source_sessions: list[int],  # [21, 22]
    corpus_root: Path,
    live_workspace_dir: Path | None,
) -> dict[str, Any]:
    """Compose in-bounds sources into the manifest dict. Pure + deterministic.

    Enumerates, per source_session: play_recap (canon_play), normalized recap
    (canon_play), breadcrumbed recap (canon_play_routed → authority canon_play),
    session_memory JSONL/meta (derived_memory). Plus: Session Prep docs
    (prep_scaffold/planning_scaffold), live_packet + event_log + plan_view for
    the planning session (live_packet/live_event), registered known_roll_tables
    (roll_table/reference_tool), and relevant campaign hub READMEs (hub_evidence).
    Routes are resolved via src.corpus.session_recap_paths helpers. Missing files
    are recorded with route_exists=false (NOT dropped) so the manifest is honest
    about gaps. Never raises on a missing source; raises only on bad inputs
    (unknown campaign_id, empty source_sessions).
    """

def render_manifest_markdown(manifest: dict[str, Any]) -> str:
    """Deterministic GM-readable mirror grouped by source_role then session."""

def main(argv: list[str] | None = None) -> int:
    """CLI: --campaign-id --planning-session --source-sessions 21 22
    --corpus-root --live-workspace-dir --out <json> [--markdown-out <md>].
    Prints JSON to stdout when --out omitted. Writes ONLY to --out/--markdown-out.
    """
```

Determinism / ordering rules:
- Entries sorted by `(source_role, min(session_scope), source_id)`. Stable across runs.
- `source_id` is derived deterministically from role + session + route basename; no UUIDs, no timestamps in the entry body.
- A top-level `generated_at` UTC field is allowed for provenance, but exclude it from any equality/golden comparison in tests (compare the `entries` list, not the wrapper timestamp).
- The builder MUST NOT mutate inputs and MUST NOT write to any path other than `--out` / `--markdown-out`.
- `authority` per role follows the charter mapping. In particular: `table_notes → pre_canonical_evidence`, `play_recap → canon_play`, `session_memory → derived_memory`, `prep_scaffold → planning_scaffold`, `roll_table → reference_tool`, `live_event → live_observation`, write/system evidence → `audit`. `forbidden_uses` MUST include `"play_facts"` for `prep_scaffold`, `roll_table`, and `table_notes` (once a play_recap for that session exists in the manifest).

### `evals/c2_live_prep/live/schemas/planning_corpus_manifest.schema.json`

JSON Schema (draft 2020-12 or match repo style) for `dmb_c2s23_planning_corpus_manifest_v0`: top-level `schema`, `campaign_id`, `planning_session`, `source_sessions`, `entries[]`; each entry requires `source_id`, `source_role`, `authority`, `session_scope`, `route`, `route_exists`, `allowed_uses`, `forbidden_uses`. `additionalProperties: false` on entries; closed `enum`s for `source_role` and `authority`.

## §7 Verification commands

Run **every** command; paste output into the PR body. Reviewer reruns each.

```bash
# Builder + render unit tests, role/authority correctness, deterministic ordering.
uv run pytest tests/test_planning_corpus_manifest.py -q

# Adjacent regressions must stay green (paths + bootstrap + schemas).
uv run pytest tests/test_live_session_bootstrap.py tests/test_live_play_schemas.py -q

# Build the real C2S23 manifest end-to-end and emit the committed artifact.
uv run python -m src.live_play.planning_corpus_manifest \
  --campaign-id longmont-c2 \
  --planning-session 23 \
  --source-sessions 21 22 \
  --corpus-root corpus/eldyrwild-markdown \
  --live-workspace-dir evals/c2_live_prep/live/session_22 \
  --out evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json \
  --markdown-out evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.md

# Validate the emitted artifact against the new schema (boundary check).
# Use the repo's existing Draft202012Validator pattern (see tests/test_live_play_schemas.py).
uv run python -c "import json; from jsonschema import Draft202012Validator; \
m=json.load(open('evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json')); \
s=json.load(open('evals/c2_live_prep/live/schemas/planning_corpus_manifest.schema.json')); \
Draft202012Validator(s).validate(m); print('schema OK', len(m['entries']), 'entries')"

# No-mutation proof: corpus fingerprint unchanged after a build.
uv run python -c "from pathlib import Path; from src.agent.planner_cache import corpus_fingerprint; \
print(corpus_fingerprint(Path('corpus/eldyrwild-markdown')))"
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. **`git diff --stat` filtered to the §4 allowlist paths only.** Not the whole-tree stat.
2. **Verbatim §7 output** — pass/fail counts; last 20 lines on any failure; the manifest entry count + schema-OK line.
3. **One-paragraph "what stayed unchanged"** — explicitly: no corpus files mutated (fingerprint identical before/after build), no live-control route/UI added, no retrieval/admission/embedding code, manifest references sources by route and inlines no corpus prose.

## §9 Acceptance rubric

Accept ONLY if every bullet is true; each is paired with its §7 command.

- [ ] Manifest validates against `dmb_c2s23_planning_corpus_manifest_v0` schema — verified by the `jsonschema.validate` boundary command.
- [ ] Every entry carries a `source_role` AND an `authority` from the closed vocabularies, and `prep_scaffold` / `roll_table` / post-recap `table_notes` entries list `"play_facts"` in `forbidden_uses` — verified by `tests/test_planning_corpus_manifest.py`.
- [ ] Missing sources are recorded with `route_exists: false` (not silently dropped); builder does not raise on a missing file — verified by `tests/test_planning_corpus_manifest.py`.
- [ ] Output is deterministic: two builds produce identical `entries` (timestamp wrapper excluded) — verified by `tests/test_planning_corpus_manifest.py`.
- [ ] Build is read-only: corpus fingerprint identical before and after, and the builder writes only to `--out` / `--markdown-out` — verified by the no-mutation fingerprint command + a test asserting no writes outside the out paths.
- [ ] No files outside §4 are touched — verified by `git diff --stat origin/main...HEAD` filtered to §4.
- [ ] No retrieval, admission, embedding, route-equivalence write, corpus mutation, or live-control route/UI is introduced — verified by the denylist check in `scripts/review_external_pr.py fetch` + reviewer read.

> **Reviewer reminder:** the schema-validity and no-mutation guarantees are owned by the *emitted artifact* and the *corpus root*, respectively — verify them at those boundaries (validate the committed JSON; fingerprint the real corpus), not only via unit fixtures.

## §10 Out-of-band notes (optional)

- The manifest is the **composition** layer. Query/admission *over* the manifest (knowing both what is in bounds and how each source may be used) is the deliberately-separate next slice (roadmap PR93 / git PR96). Do not pre-build retrieval here, even partially.
- `--live-workspace-dir` defaults to the Session 22 dogfood workspace today; once a Session 23 workspace is bootstrapped, the same CLI re-points with no code change. Keep the dir a CLI arg, not a hardcoded path.
- `jsonschema` is already a dependency: `tests/test_live_play_schemas.py` validates with `Draft202012Validator` against schema files in `evals/c2_live_prep/live/schemas/`. Mirror that pattern (loader + `Draft202012Validator(schema).validate(doc)`) — do not add a new validation dependency, and put the new schema in the same `schemas/` dir so the existing `_validator(...)` helper can pick it up.
- If the worker hits a sandbox issue with `gh pr create`, post the PR-body markdown back to the dispatcher and the dispatcher will open the PR by hand.

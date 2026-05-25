# HANDOFF — PR 74: C2 Live Control Surface L2 Roll Resolver + Live Classifier

**Created:** 2026-05-25 (UTC).  
**Status:** ACTIVE — dispatch this to one fresh external/Codex agent. One PR. Do not split into multiple PRs.  
**Parent agent:** Cursor agent; parent owns review, merge, and atomic doc-sync after the PR lands.  
**Plan anchor:** `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` (`execution_state.active_slice: L2_roll_resolver_classifier`).  
**Checklist anchor:** `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` Phase L2.  
**Substrate anchor:** PR #72 merged L1 file-backed substrate.

---

## §0 Re-anchor Before Writing

This handoff assumes PR #72 is merged on `main` and L1 is complete. Do not infer current state from chat history.

Read in this order:

1. `.cursor/rules/external-agent-pr-loop.mdc` — mandatory allowlist / denylist / verification contract.
2. `.cursor/rules/anchor.mdc` — re-anchor discipline for fresh agents.
3. `AGENTS.md` — repo operating policy, UV usage, RTK preference, git verification, and external-agent PR loop conventions.
4. `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` — confirm `execution_state.active_slice: L2_roll_resolver_classifier`.
5. `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` — Phase L2 is authoritative for file scope and seed examples.
6. `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` — fast-live vs slow-architecture boundary.
7. `Docs/Plans/archive/2026-05-25/handoffs/HANDOFF-pr72-c2-live-packet-event-job-schema.md` — L1 substrate contract.
8. `evals/c2_live_prep/live/session_22/live_packet.json` — live packet, roll stack, known roll tables, surface catalog.
9. `evals/c2_live_prep/live/session_22/event_log.jsonl`, `job_queue.jsonl`, `current_state.json` — seed state surfaces to preserve; do not mutate them in tests.
10. Relevant roll-table corpus files referenced by the packet, especially:
    - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/travel_storm_weather_d20.md`
    - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22/mireward_gate_dilemma_d6.md`
    - `corpus/eldyrwild-markdown/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md`

Current-state hypothesis to carry into the PR:

- L1 substrate is complete and merged.
- L2 has not started.
- This PR creates local Python logic only: roll-table registry, deterministic roll resolver, live-turn classifier, and a no-HTTP live turn handler.
- FastAPI server, React UI, retrieval rebuilds, corpus writes, recap writes, and post-session propagation execution are later slices.

---

## §1 Mission

Implement the non-HTTP live-play logic needed for Session 22 examples:

1. A roll-table registry that maps `live_packet.known_roll_tables` entries to source files and table metadata.
2. A deterministic roll resolver that can resolve common Session 22 roll prompts from the packet's roll table registry.
3. A lightweight live-turn classifier that separates roll results, skill checks, canon commits, canon corrections, open-loop updates, context questions, and prep requests.
4. A `handle_live_turn(packet, text) -> LiveTurnResult` function that returns answer text, classification, events to write, jobs to queue, next suggestions, and provenance without invoking FastAPI or writing corpus files.
5. Tests built from the Session 22 transcript/product examples.

This PR should make L3 boring: the future server should mostly load files, call `handle_live_turn`, append returned events/jobs, and return a JSON response.

---

## §2 Why This Slice

L1 established the file-backed substrate: packet, surface layout, event schema, job schema, derived current state, JSON/JSONL helpers, and layout invariants.

L2 turns that substrate into a local live-play decision loop without web transport. It must prove that common GM inputs can be classified and converted into structured outputs before adding a server or UI. If this layer is clean, L3 and L4 become adapters over tested logic rather than places where product behavior hides.

The main boundary is latency discipline:

- `fast_live` is deterministic and local.
- `context_lookup` may route to packet/source lookup later, but this PR does not build retrieval.
- `prep_architect` and `post_session` are routed/queued, not executed inline.

---

## §3 Files In Scope (Allowlist)

The worker's expected `git diff --stat` must be expressible from this table.

| Action | Path | Purpose |
|---|---|---|
| Create | `src/live_play/roll_table_registry.py` | Load/normalize roll-table metadata from a live packet and parse supported table row shapes from corpus Markdown. |
| Create | `src/live_play/resolve_roll.py` | Parse roll commands and resolve rows against the registry with provenance. |
| Create | `src/live_play/classify_live_turn.py` | Classify raw GM text into live event/latency categories without LLM calls. |
| Create | `src/live_play/live_turn.py` | Compose classifier + resolver into `handle_live_turn(packet, text) -> LiveTurnResult` without HTTP or file mutation. |
| Modify only if necessary | `src/live_play/__init__.py` | Optional exports only; no behavior. |
| Create | `tests/test_live_play_resolve_roll.py` | Resolver tests for pipe-row and R5 band/paragraph tables. |
| Create | `tests/test_live_play_classify_turn.py` | Classifier tests for Session 22 examples. |
| Create | `tests/test_live_play_turn_loop.py` | End-to-end no-HTTP turn handler tests. |

Do not add new package roots or application directories in this PR.

---

## §4 Files Explicitly Out Of Scope (Denylist)

Do not touch any of these.

| Path | Why this PR must not touch it |
|---|---|
| `apps/live-control-server/**` | FastAPI/local server belongs to L3. |
| `apps/live-control-ui/**` | React/Vite UI belongs to L4. |
| `Docs/Plans/PLAN-c2-live-control-surface-query-pane.md` | Parent doc-sync owns plan updates after review/merge. |
| `Docs/Plans/CHECKLIST-c2-live-control-surface-query-pane.md` | Parent doc-sync owns checklist updates after review/merge. |
| `Docs/Plans/STUDY-c2-live-play-cursor-handoff-process.md` | Product-friction study is read-only. |
| `Docs/Plans/README-c2-live-control-ui.md` | UI planning README is sibling documentation, not L2 implementation. |
| `evals/c2_live_prep/live/schemas/**` | L1 schemas are accepted; do not mutate them for convenience. |
| `evals/c2_live_prep/live/session_22/*.json` | L1 seed packet/state/layout are inputs, not regenerated outputs. |
| `evals/c2_live_prep/live/session_22/*.jsonl` | Tests may use temp copies, but must not append to committed seed logs. |
| `corpus/**` | This PR reads roll tables only; no corpus promotion, correction, or recap writes. |
| `evals/c2_live_prep/artifacts/**` | Existing smoke artifacts are inputs/evidence, not regenerated outputs. |
| `evals/sentence_routing_retrieval_falsification/**` | Sibling retrieval/autonomy workstream. |

If a denylisted path appears necessary, stop and report the blocker in the PR body instead of editing it.

---

## §5 Implementation Contract

### Public types

Prefer simple dataclasses or typed dictionaries. Keep the contract stable and testable. Suggested names:

```python
@dataclass(frozen=True)
class RollTableRef:
    table_id: str
    title: str
    dice: str
    source_path: str
    status: str
    default_latency_mode: str | None = None

@dataclass(frozen=True)
class ResolvedRoll:
    table_id: str
    roll: int
    title: str
    row_text: str
    source_path: str
    row_locator: str
    provenance: dict[str, object]

@dataclass(frozen=True)
class TurnClassification:
    latency_mode: str
    event_type: str
    intent: str
    table_id: str | None = None
    roll: int | None = None
    skill_check: dict[str, object] | None = None
    confidence: str = "deterministic"

@dataclass(frozen=True)
class LiveTurnResult:
    answer: str
    classification: TurnClassification
    events_to_write: list[dict[str, object]]
    jobs_to_queue: list[dict[str, object]]
    next_suggestions: list[str]
    provenance: dict[str, object]
    diagnostics: list[str]
```

The exact class names may vary, but tests must pin a clear return shape. Avoid unstructured tuples.

### `roll_table_registry.py`

Required behavior:

- Build registry entries from `packet["known_roll_tables"]`.
- Validate that referenced source files exist relative to repo root or an injected root path.
- Parse supported Markdown roll table shapes:
  - pipe-table rows, such as `T-WX` d20 storm weather table
  - d100 band/paragraph rows, such as `R5` Mireward Reach road table
- Preserve source provenance: `source_path`, table ID, row locator, and title.
- Do not depend on global current working directory in tests; accept `root: Path` where useful.

R5 handling is required for this PR because the checklist includes `R5 54.` as a seed example. For R5, resolve roll 54 to the 51–60 band and the fourth paragraph in that band: `Crowd hums one note before they know why; it passes. No harm? Or rehearsal?`.

### `resolve_roll.py`

Required behavior:

- Parse at least these command shapes:
  - `Weather 7.` → table `T-WX`, roll `7`
  - `Weather 16.` → table `T-WX`, roll `16`
  - `R5 54.` → table `R5`, roll `54`
  - optional: direct table IDs such as `T-WX 7`, `T-DIL-G 4`
- Validate roll ranges from dice notation (`d20`, `d100`, `d6`, etc.).
- Return a structured diagnostic for unknown tables, unsupported table shapes, and out-of-range rolls.
- Never perform repo-wide search.
- Never write files.

Resolver output should include enough information for a fast response and event provenance:

- table ID
- table title
- roll value
- row text
- source path
- row locator, e.g. `pipe_row:d20=7` or `band:51-60:item=54`

### `classify_live_turn.py`

Required behavior:

Classify the seed examples deterministically:

| Text | Required classification |
|---|---|
| `Weather 7. Caelynn Nature 19.` | `latency_mode=fast_live`, `event_type=roll_result`, captures table `T-WX`, roll `7`, and skill check `{actor: Caelynn, skill: Nature, total: 19}`. |
| `Weather 16.` | `latency_mode=fast_live`, `event_type=roll_result`, table `T-WX`, roll `16`. |
| `R5 54.` | `latency_mode=fast_live`, `event_type=roll_result`, table `R5`, roll `54`. |
| `Grobnok does not call in the morning.` | `latency_mode=fast_live`, `event_type=open_loop_update`; preserve that evening contact remains owed. |
| `Lysandro is her father.` | `latency_mode=fast_live`, `event_type=canon_correction`; queue post-session propagation in the turn handler. |
| `Caelynn bottles the puddle water.` | `latency_mode=fast_live`, `event_type=canon_commit`; queue staging append / benchmark candidate. |
| `What is Lysandra feeling at the gate?` | `latency_mode=context_lookup`, `event_type=context_question`; do not route to roll resolver. |

Classifier should be rule-based for this PR. Do not call an LLM. Do not build retrieval.

### `live_turn.py`

Required behavior:

`handle_live_turn(packet, text)` must:

- call the classifier
- call the roll resolver only for roll-result classifications
- produce one or more event rows compatible with `live_event.schema.json`
- produce zero or more job payloads compatible with `live_job.schema.json` or `jobs_to_queue` embedded event payload shape
- return answer text suitable for the future Chat module
- return next suggestions suitable for the future UI
- return provenance and diagnostics
- not write event/job JSONL files directly
- not mutate the input packet
- not call FastAPI, React, external APIs, retrieval rebuilds, or corpus write tools

Event rows must include:

- `schema_version`
- `id`
- `created_at`
- `campaign_id`
- `session`
- `session_clock`
- `event_type`
- `event_origin`
- `latency_mode`
- `input_text`
- `summary`
- `derived_fields`
- `provenance`
- `jobs_to_queue`

Use deterministic IDs and timestamps in tests. Implementation may accept injected `now` / ID factory values to avoid flaky tests.

### Jobs and side effects

For this PR, jobs are returned, not executed.

Expected job behavior:

- canon correction → queue `post_session_propagation` and likely `manual_review`
- canon commit → queue `append_staging` and/or `benchmark_candidate`
- roll examples → may queue `benchmark_candidate` if useful, but do not overproduce jobs
- context question → no retrieval execution; return classification/provenance/diagnostic indicating it should be handled by future context lookup

---

## §6 Required Test Cases

Use the exact seed examples from the checklist and study.

### Resolver tests

`tests/test_live_play_resolve_roll.py` must cover:

- `Weather 7.` resolves `T-WX` row 7 and includes `Hail dent` in row text.
- `Weather 16.` resolves `T-WX` row 16 and includes `Fixed-distance front` in row text.
- `R5 54.` resolves `R5` band 51–60 and includes `Crowd hums one note` in row text.
- Out-of-range weather roll, e.g. `Weather 99.`, returns or raises a structured diagnostic.
- Unknown table ID returns or raises a structured diagnostic.
- Resolver does not mutate committed JSON/JSONL files.

### Classifier tests

`tests/test_live_play_classify_turn.py` must cover every row in the Phase L2 seed examples table.

At minimum assert:

- latency mode
- event type
- table ID / roll where applicable
- skill check extraction for `Weather 7. Caelynn Nature 19.`
- `What is Lysandra feeling at the gate?` is `context_lookup`, not roll resolution
- `Lysandro is her father.` is a canon correction, not a generic state note

### Turn-loop tests

`tests/test_live_play_turn_loop.py` must cover:

- `handle_live_turn(packet, "Weather 7. Caelynn Nature 19.")` returns:
  - answer containing the resolved weather row
  - classification `fast_live` / `roll_result`
  - event row with valid event schema shape
  - skill check in derived fields
  - next suggestions including at least one of `T-NPC`, `R5`, or `T-DIL`
- `handle_live_turn(packet, "Grobnok does not call in the morning.")` returns open-loop update and preserves evening contact as owed in answer/derived fields.
- `handle_live_turn(packet, "Lysandro is her father.")` returns canon correction event plus queued post-session propagation job payload.
- `handle_live_turn(packet, "What is Lysandra feeling at the gate?")` returns context lookup classification and does not attempt roll resolution.
- returned event rows validate against `evals/c2_live_prep/live/schemas/live_event.schema.json` with format checking enabled.

---

## §7 Verification Commands

The worker must run every command and paste the output into the PR body. The reviewer will rerun each.

```bash
uv run pytest tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py -q
```

```bash
uv run pytest tests/test_live_play_schemas.py tests/test_live_play_resolve_roll.py tests/test_live_play_classify_turn.py tests/test_live_play_turn_loop.py -q
```

```bash
git diff --name-only
```

```bash
git diff --stat -- \
  src/live_play/roll_table_registry.py \
  src/live_play/resolve_roll.py \
  src/live_play/classify_live_turn.py \
  src/live_play/live_turn.py \
  src/live_play/__init__.py \
  tests/test_live_play_resolve_roll.py \
  tests/test_live_play_classify_turn.py \
  tests/test_live_play_turn_loop.py
```

If `src/live_play/__init__.py` is not touched, it may be absent from the filtered diff output.

---

## §8 Reporting Contract

In the PR body the worker must include:

1. Verbatim output for every §7 command.
2. Complete `git diff --name-only` output for all changed files.
3. Filtered `git diff --stat` for the §3 allowlist.
4. One paragraph confirming no FastAPI, no UI, no schema mutation, no corpus writes, no retrieval rebuild, and no committed JSONL seed mutation.
5. A short note on R5 d100 band/paragraph handling: implemented vs diagnostic. For this handoff, implemented is expected for `R5 54.` unless a blocker is discovered.
6. Any design judgment where the worker intentionally deviates from the suggested dataclass names or return shape.

---

## §9 Acceptance Rubric

The reviewer will accept only if every bullet below is true.

- [ ] L2 files stay inside the §3 allowlist.
- [ ] No FastAPI/server files, React/UI files, schema files, corpus files, or committed seed JSON/JSONL files are modified.
- [ ] `Weather 7. Caelynn Nature 19.` resolves T-WX row 7, extracts skill check, emits a valid event row, and suggests next beats.
- [ ] `Weather 16.` resolves T-WX row 16.
- [ ] `R5 54.` resolves the R5 51–60 band and specific paragraph row.
- [ ] `Grobnok does not call in the morning.` is classified as an open-loop update and preserves evening contact as owed.
- [ ] `Lysandro is her father.` is classified as a canon correction and queues post-session propagation.
- [ ] `Caelynn bottles the puddle water.` is classified as a canon commit and queues staging append and/or benchmark candidate.
- [ ] `What is Lysandra feeling at the gate?` routes to `context_lookup` and does not invoke roll resolution.
- [ ] `handle_live_turn` is pure with respect to repo files: it returns events/jobs but does not write them.
- [ ] Returned event rows validate against the accepted L1 event schema.
- [ ] L1 schema tests still pass alongside L2 tests.

---

## §10 Out-of-Band Notes

- This is not a retrieval PR. Context lookup classification is enough; source lookup/retrieval can land later.
- This is not a server PR. The future API should wrap this logic, not contain it.
- This is not a UI PR. The UI README and L4 surface shell are sibling/future work.
- This is not a canon PR. `canon_commit` and `canon_correction` events/jobs are queueable intent, not immediate corpus edits.
- Keep the resolver deterministic and boring. The goal is trustable live latency, not general intelligence.

pr_body_template: |
  ## Summary
  Implement C2 L2 local live-play logic: roll table registry, roll resolver, live turn classifier, and no-HTTP turn handler.

  ## Verification
  Paste the verbatim output from every §7 command here.

  ## `git diff --name-only`
  ```text
  Paste the complete changed-file list here.
  ```

  ## `git diff --stat` (§3 paths only)
  ```text
  Paste a diff stat filtered to the §3 allowlist here.
  ```

  ## Scope confirmation
  No FastAPI/server files, UI files, schema files, corpus files, retrieval artifacts, or committed seed JSONL logs were modified.

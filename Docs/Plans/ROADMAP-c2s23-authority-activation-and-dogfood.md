---
document_id: dmb-roadmap-c2s23-authority-activation-and-dogfood
title: C2S23 Authority Activation and Dogfood Roadmap
document_class: roadmap
status: active
version: 0.2
created_at: "2026-05-30T03:45:00Z"
last_updated_at: "2026-05-30T21:15:00Z"
---

# C2S23 Authority Activation and Dogfood Roadmap

## Changelog

- **2026-05-30** (`02c0f9f`): **PR95 merged** — C2S23 activated planning corpus manifest (`src.live_play.planning_corpus_manifest`, schema-valid artifact, bootstrapped `session_23` workspace). Next: Step 0 Session 22 ingest completion (breadcrumb → session memory) then query/admission over manifest (git PR96 / roadmap PR93).

## Purpose

PR90 made live-control dogfooding possible by adding fresh recap ingestion and session workspace bootstrap.

The next problem is not building a new corpus system. The project already has corpus tree navigation, recap context, session memory records, campaign corpus records, route equivalence, live workspace files, and roll-table references.

The next problem is defining an activation boundary for planning Session 23.

An activated planning corpus answers:

```text
For campaign C2, planning Session 23, what sources are in bounds, what role does each source play, what authority does each source have, and what is each source allowed to prove?
```

## Content State

Session 22 was played, and its table notes are staged at:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md
```

Ingesting Session 22 is a content operation, not a prerequisite software PR.

Expected path:

```text
session_22 notes
→ recap-write pass
→ normalized recap
→ breadcrumbed recap
→ session memory JSONL
→ eligible play/canon source for C2S23 planning
```

## Authority Boundary

The danger is flattening authority.

Planning Session 23 requires reasoning across played history and GM scaffold without treating both as the same kind of truth.

Keep these distinct:

```text
table notes          → evidence awaiting recap-write
played recap         → canon/play memory after recap-write
session memory       → derived retrieval records from played recap
planning anchor      → GM scaffold, not canon
prep brief/runbook   → intended possibility space, not canon
roll tables          → prep tools, not happened facts
live workspace       → active planning surface / observations
```

## Source Role and Authority Axis

PR92 should define one shared axis across campaign corpus files and live workspace files.

Suggested source roles:

| source_role | Meaning | Normal use |
|---|---|---|
| table_notes | Table notes before recap-write | provenance only after recap exists |
| play_recap | Post-session recap of what happened | answer play facts, derive open loops, planning context |
| session_memory | Retrieval records derived from recap | search/routing/evidence support |
| prep_scaffold | GM planning anchor, brief, runbook, unused prep | planning context, reusable prep, not play facts |
| roll_table | Prep tool table | table use/patching, not happened facts |
| live_packet | Active live-control packet | active session orientation |
| live_event | Event log row | observed play, planning observations, audit evidence |
| fresh_recap | Recap input used to bootstrap workspace | planning input until promoted/ingested |
| hub_evidence | Campaign hub section/chunk | broader context with route/role metadata |

Suggested authority values:

| authority | Meaning |
|---|---|
| pre_canonical_evidence | Evidence that must pass recap-write before normal use |
| canon_play | Happened in play / committed recap memory |
| derived_memory | Derived retrieval representation of a source |
| planning_scaffold | GM intent, prep possibility, or planned beats |
| planning_input | Active planning-session input not yet promoted to canon |
| live_observation | Human/agent observation appended during live-control use |
| audit | Write evidence or system event |
| reference_tool | Roll table / utility / reusable table aid |

## Roadmap

### Step 0 — Ingest Session 22

**Status:** in progress (2026-05-30). CLI apply+normalize landed canonical recap `Session 22 - Mireward Gate Lysandro Ironveil.md`; pipeline stopped at **`breadcrumb_required`** (expected). Next: bless/generate breadcrumb, then `--materialize-session-memory`.

Run the existing content operation on staged Session 22 notes, then normalize, breadcrumb, and generate session memory.

If the notes are not final, mark PR91 as using a projected post-ingest state.

### PR91 — C2S23 Dogfood Planning Benchmark + Manual Baseline

Author 15–25 Session 23 planning questions from GM intent.

Do not author questions by surveying source files. That risks oracle leakage.

Capture manual baseline answers and friction using the current workflow.

### PR92 — C2S23 Activated Planning Corpus Manifest

**Status:** ✅ merged as git **PR #95** (`02c0f9f`, 2026-05-30).

Build the session-scoped activation manifest.

This is a composition layer, not a new ingestion layer and not retrieval.

It should include Session 21/22 recap memory, Session 22 prep scaffold that may carry forward, Session 23 live workspace files, allowed roll tables, relevant hub/campaign corpus records, and route-equivalence records where available.

It should emit a canonical JSON manifest and optional generated markdown mirror.

### PR93 — Query / Admission over Activated Planning Corpus

Wire query/admission to consume the activation manifest.

The query layer should know both what is in bounds and how each source may be used.

### PR94 — Instrumented Dogfood Re-run

Re-run the PR91 questions against manifest-backed query/admission.

Compare against the manual baseline.

## Benchmark Focus

The benchmark should include authority traps intentionally:

- What actually happened by the end of Session 22?
- Which Session 22 prep elements are still available for Session 23?
- What should I prepare for the start of Session 23?
- What facts are confirmed, and what is only GM intent?

## Metrics

- Evidence recall.
- Role correctness.
- Temporal correctness.
- Canon discipline.
- Planning usefulness.
- Route grounding.
- Friction reduction.

## Invariants

- Do not flatten prep into canon.
- Do not treat table notes as normal retrieval once the recap exists.
- Do not treat roll tables as evidence that something happened.
- Do not build a second corpus ingestion system.
- Do not add retrieval to PR92.
- Do not let question gold be reverse-engineered from source files.
- Preserve source_role, authority, session scope, lifecycle state, routes, and allowed/forbidden uses.

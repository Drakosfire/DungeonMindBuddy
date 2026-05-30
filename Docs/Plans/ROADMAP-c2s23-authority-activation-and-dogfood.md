---
document_id: dmb-roadmap-c2s23-authority-activation-and-dogfood
title: C2S23 Authority Activation and Dogfood Roadmap
document_class: roadmap
status: active
version: 0.1
created_at: "2026-05-30T03:45:00Z"
---

# C2S23 Authority Activation and Dogfood Roadmap

## Reanchor

PR90 made live-control dogfooding possible by adding deterministic fresh recap ingestion and session workspace bootstrap.

The next problem is not building a new corpus system. The project already has corpus tree navigation, recap context, session memory records, campaign corpus records, route equivalence, live workspace files, and roll-table references.

The next problem is defining an activation boundary for planning Session 23.

An activated planning corpus answers:

```text
For campaign C2, planning Session 23, what sources are in bounds, what role does each source play, what authority does each source have, and what is each source allowed to prove?
```

## Decisive Content State

Session 22 was played, and its raw table notes are staged at:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md
```

That means ingesting Session 22 is a content operation, not a prerequisite software PR.

The expected content path is:

```text
session_22_raw_notes.md
→ recap-write pass
→ normalized recap
→ breadcrumbed recap
→ session memory JSONL
→ eligible play/canon source for C2S23 planning
```

The latest committed recap/session-memory before that operation is Session 21.

## Core Authority Problem

The danger is not missing files. The danger is flattening authority.

Planning Session 23 requires reasoning across played history and GM scaffold without treating both as the same kind of truth.

The key distinction:

```text
raw table notes      → evidence awaiting recap-write
played recap         → canon/play memory after recap-write
session memory       → derived retrieval records from played recap

planning anchor      → GM scaffold, not canon
prep brief/runbook   → intended possibility space, not canon
roll tables          → prep tools, not happened facts
live workspace       → active planning surface / observations
```

The manifest/query layer must preserve this distinction.

## Source Role and Authority Axis

PR92 should define one shared axis across campaign corpus files and live workspace files.

Suggested source roles:

| source_role | Meaning | Normal use |
|---|---|---|
| raw_table_notes | Table notes before recap-write | provenance only; excluded from normal answers after recap exists |
| play_recap | Post-session recap of what happened | answer play facts, derive open loops, planning context |
| session_memory | Retrieval records derived from recap | search/routing/evidence support |
| prep_scaffold | GM planning anchor, brief, runbook, unused prep | planning context, reusable prep, not play facts |
| roll_table | Prep tool table | table use/patching; not happened facts |
| live_packet | Active live-control packet | active session orientation |
| live_event | Event log row | observed play / planning observations / audit evidence |
| fresh_recap | Recap input used to bootstrap workspace | planning input until promoted/ingested |
| hub_evidence | Campaign hub section/chunk | broader context with route/role metadata |

Suggested authority values:

| authority | Meaning |
|---|---|
| pre_canonical_evidence | Evidence that must pass recap-write before normal use |
| canon_play | Happened in play / committed recap memory |
| derived_memory | Derived retrieval representation of canon/prep source |
| planning_scaffold | GM intent, prep possibility, or planned beats |
| planning_input | Active planning-session input not yet promoted to canon |
| live_observation | Human/agent observation appended during live-control use |
| audit | Write evidence or system event |
| reference_tool | Roll table / utility / reusable table aid |

## Allowed and Forbidden Use

Every activated entry should make use explicit.

Example play recap entry:

```json
{
  "entry_id": "c2-s22-play-recap",
  "source_role": "play_recap",
  "authority": "canon_play",
  "allowed_uses": ["answer_play_facts", "derive_open_loops", "planning_context"],
  "forbidden_uses": []
}
```

Example prep scaffold entry:

```json
{
  "entry_id": "c2-s22-planning-anchor",
  "source_role": "prep_scaffold",
  "authority": "planning_scaffold",
  "allowed_uses": ["planning_context", "unused_prep_reuse"],
  "forbidden_uses": ["answer_play_facts"]
}
```

Example raw notes entry after recap exists:

```json
{
  "entry_id": "c2-s22-raw-notes",
  "source_role": "raw_table_notes",
  "authority": "pre_canonical_evidence",
  "allowed_uses": ["provenance"],
  "forbidden_uses": ["normal_retrieval", "answer_play_facts"]
}
```

## Reconciliation Model

Do not merge recap and prep into one narrative.

Reconcile them by linking sources and preserving authority.

Useful reconciliation questions:

- What prep material was realized in play?
- What prep material was contradicted or superseded?
- What prep material remains unused but viable for Session 23?
- What prep material should be retired?
- What new play facts change Session 23 planning?

This may eventually produce a derivative artifact:

```text
session_22_reconciliation.json
session_22_reconciliation.md
```

But that reconciliation artifact is not required before PR91. PR91 can benchmark the need for it.

## Revised Roadmap

### Step 0 — Ingest Session 22

This is a content operation using existing skills, not a code PR.

Run recap-write on staged Session 22 raw notes, then normalize, breadcrumb, and generate session memory.

If Session 22 notes are not final, document that PR91 uses a projected post-ingest state.

### PR91 — C2S23 Dogfood Planning Benchmark + Manual Baseline

Author 15–25 Session 23 planning questions from GM intent.

Do not author questions by surveying the recap contents. That risks oracle leakage.

Capture a manual baseline using the current workflow: current Cursor / DungeonBuddy planning surface, bootstrapped live-control session, and human notes.

No automated score is required yet.

Outputs:

```text
benchmark question set
manual baseline answers
friction log
runbook update
```

### PR92 — C2S23 Activated Planning Corpus Manifest

Build the session-scoped activation manifest.

This is a composition layer, not a new ingestion layer.

It should include:

- Session 21 recap/session memory.
- Session 22 recap/session memory after content ingest.
- Session 22 prep scaffold that may carry into Session 23.
- Session 23 live workspace files from PR90.
- Roll tables allowed by planning policy.
- Relevant hub/campaign corpus records if policy allows.
- Route-equivalence records where available.

It should emit:

```text
canonical JSON manifest
generated markdown mirror
```

No retrieval yet.

### PR93 — Query / Admission over Activated Planning Corpus

Wire retrieval/admission to consume the activation manifest.

The query layer should know both what is in bounds and how each source may be used.

The primary correctness risk is authority misuse, not just missing recall.

### PR94 — Instrumented Dogfood Re-run

Re-run the PR91 questions against manifest-backed query/admission.

Compare against manual baseline.

Measure evidence recall, authority discipline, planning usefulness, and friction reduction.

## Benchmark Focus

The benchmark should include authority traps intentionally.

Examples:

```text
What actually happened by the end of Session 22?
```

Expected behavior: use play recap/session memory, not planning scaffold.

```text
Which Session 22 prep elements are still available for Session 23?
```

Expected behavior: use prep scaffold and label it as unused/reusable planning material, not canon.

```text
What should I prepare for the start of Session 23?
```

Expected behavior: synthesize play recap, unresolved loops, live workspace planning beats, and reusable prep scaffold while preserving authority labels.

```text
What facts are confirmed, and what is only GM intent?
```

Expected behavior: explicitly separate canon_play from planning_scaffold/planning_input.

## Metrics That Matter

- Evidence recall: did the system find the right S21/S22/S23/prep sources?
- Role correctness: did the system know play recap vs prep scaffold vs live event vs roll table?
- Temporal correctness: did it distinguish S21, S22, and S23 planning state?
- Canon discipline: did it separate happened-in-play from prep idea from projected beat?
- Planning usefulness: did it produce actionable prep decisions?
- Route grounding: did entries carry normalized routes/source roles rather than raw paths alone?
- Friction reduction: did manifest-backed retrieval reduce manual repo archaeology?

## Invariants

- Do not flatten prep into canon.
- Do not treat raw notes as normal retrieval once the recap exists.
- Do not treat roll tables as evidence that something happened.
- Do not build a second corpus ingestion system.
- Do not add retrieval to PR92.
- Do not let question gold be reverse-engineered from source files.
- Do preserve source_role, authority, session scope, lifecycle state, routes, and allowed/forbidden uses.

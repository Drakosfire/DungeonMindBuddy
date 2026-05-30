---
document_id: dmb-benchmark-c2s23-dogfood-planning
title: C2S23 Dogfood Planning Benchmark Charter
document_class: benchmark_charter
status: active
version: 0.1
created_at: "2026-05-30T20:00:00Z"
campaign_id: longmont-c2
planning_session: 23
source_sessions: [21, 22]
---

# C2S23 Dogfood Planning Benchmark Charter

## Purpose

Define what the first **real** Campaign 2 Session 23 planning pass is trying to prove in DungeonMindBuddy **before** manifest-backed retrieval or automated scoring exist.

This benchmark is a **decision-capture and friction instrument**, not a retrieval harness. It records:

- whether operators can plan Session 23 with the current live-control + corpus toolchain,
- whether authority boundaries stay visible under pressure,
- and which artifact actions are supported vs missing.

The seed questions live in `evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json`. Manual answers use `evals/c2_live_prep/benchmarks/c2s23_manual_baseline.template.md`.

## Scope

**In scope**

- Planning **Session 23** using **Session 22 play outcome** plus **Session 21** continuity where relevant.
- Raw Session 22 recap ingestion (CLI L5M or ingestion pane L5N), derivative promotion (normalize, breadcrumb, session memory), and Session 23 live workspace bootstrap.
- Manual answers through Timeline, Inspector reads, Chat classifier routing, append observation, and roll-table patch where artifacts exist.
- Explicit logging of source roles, authority mistakes, and desired-but-unsupported artifact actions.

**Out of scope for this charter (non-goals)**

- Implementing retrieval or admission over an activated planning corpus.
- Building or emitting a C2S23 activated planning corpus manifest.
- Performing corpus mutation as part of benchmark automation (operator-driven writes via existing tools are allowed when the runbook says so).
- New live-control feature work, LLM recap rewrite, or breadcrumb auto-generation.
- Gold answers reverse-engineered from corpus files (questions are GM-intent seeds only).

## What counts as “actively planning in DungeonBuddy”

A dogfood round **counts** when the operator:

1. Has promoted Session 22 table notes through recap ingestion far enough that play recap and (when breadcrumb exists) session memory are usable.
2. Boots or activates a **Session 23** live workspace (`live_packet.json`, `event_log.jsonl`, plan-view projection).
3. Uses the **live-control surface** (not only CLI or IDE agents) for at least:
   - Timeline / plan-view orientation,
   - one Inspector artifact or capability read,
   - one planning question attempted via Chat or manual corpus navigation,
   - one write attempt that the capability inventory marks as supported (e.g. append observation) **or** explicit logging of a blocked desired action.
4. Records answers and friction in the manual baseline template.

**Does not count:** answering the same questions only in Cursor chat without the live workspace; grep-only prep without authority notes; treating staged table notes as play facts after a canonical recap exists.

## Benchmark dimensions

| Dimension | What we measure | Pass signal (manual, v0) |
|-----------|-----------------|---------------------------|
| **Evidence recall** | Operator can find the right sources for play facts, continuity, and prep hooks | Sources listed match question intent; missing sources named explicitly |
| **Authority discipline** | Play facts come from canon play / derived memory; prep and tools are not mistaken for happened facts | `forbidden_source_roles_for_play_facts` not violated; authority traps answered with correct tier |
| **Context enrichment quality** | When context is assembled (manual or future packet), it is complete enough to plan the next beat | Answer cites multiple relevant roles without collapsing scaffold into recap |
| **Artifact actionability** | Desired planning actions map to real entrypoints | Supported actions succeed; missing actions logged with PR follow-up |
| **Mutation safety** | Writes stay on allowlisted surfaces; no silent canon corruption | Preview/two-phase where required; live observations not treated as retroactive play canon |
| **Planning usefulness** | Output helps run Session 23 at the table | Actionable next beats, open loops, and prep gaps—not encyclopedic summary |

## Source authority roles

Use these roles when recording `sources consulted` and `source roles` in the manual baseline. They align with L5M/L5N ingest status and the C2 live-control authority model.

| Role | Meaning | Typical paths / surfaces |
|------|---------|---------------------------|
| `pre_canonical_evidence` | Raw table notes before recap-write / canonical recap | `_ingest_staging/session_<N>_raw_notes.md` |
| `canon_play` | Played recap of what happened | `Session Recaps/Session <N> - <slug>.md` |
| `derived_memory` | Retrieval records derived from recap | `Session Recaps/_session_memory/*.records_meta.{jsonl,json}` |
| `planning_scaffold` | GM planning anchor, prep brief, runbook—not play proof | `Session Prep/`, planning beats in live packet |
| `reference_tool` | Roll tables and reusable prep tables | `known_roll_tables`, corpus roll-table markdown |
| `live_observation` | Observations appended during live-control | `event_log.jsonl` via append_observation |
| `audit` | Write evidence, command results, ingest status JSON | command bus events, recap ingest status |

**Forbidden for play-fact answers** (unless question explicitly asks about intent or tools): `planning_scaffold`, `reference_tool`, `pre_canonical_evidence` (after canonical recap exists), `live_observation` (for past-session play facts).

## Question categories (seed benchmark)

| Category | Intent |
|----------|--------|
| `raw_recap_ingestion_session_22_understanding` | Confirm operator understands S22 outcome after ingest pipeline |
| `cross_session_continuity` | S21 → S22 → S23 threads without conflating sessions |
| `roll_table_creation_mutation` | Prep tables: read, patch, create expectations |
| `location_creation_mutation` | Location hubs and scene grounding |
| `npc_creation_mutation` | NPC hubs, timelines, dossier boundaries |
| `town_economy_planning_model` | Next settlement, travel, economy hooks for S23 |
| `authority_trap_questions` | Deliberate checks that prep/tools/observations are not play canon |

## Success and failure (charter level)

**Success (round complete)**

- Session 22 ingest path executed through at least apply+normalize; breadcrumb boundary acknowledged if present.
- Session 23 workspace bootstrapped and used in live-control UI.
- ≥15 seed questions attempted in manual baseline with sources and roles filled.
- Capability inventory gaps updated with anything newly discovered.
- Follow-up PRs identified for blocking missing capabilities (manifest, retrieval, artifact creates).

**Failure (stop and fix process)**

- Play facts routinely sourced from prep scaffold or roll tables without correction.
- Operator cannot complete ingest or bootstrap due to tooling breakage (regression).
- Questions answered only from memory/chat with no source trace (oracle leakage in baseline).
- Unscoped corpus writes outside allowlist during dogfood.

**Stop and open follow-up PR when**

- Same missing capability blocks ≥3 questions (e.g. no manifest-backed query, no roll-table create).
- Authority traps fail repeatedly → PR for activation manifest + admission role enforcement (see roadmap).
- Ingest or bootstrap tests fail → fix L5M/L5N/L5L before continuing dogfood.

## Related artifacts

| Artifact | Path |
|----------|------|
| Seed questions | `evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json` |
| Manual baseline template | `evals/c2_live_prep/benchmarks/c2s23_manual_baseline.template.md` |
| Capability inventory | `Docs/Plans/CAPABILITY-INVENTORY-c2s23-planning-artifact-actions.md` |
| Operator runbook | `Docs/Plans/RUNBOOK-c2-first-dogfood-planning-round.md` |
| Roadmap | `Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md` |

## Verification (this PR)

- Charter defines dimensions, roles, scope, and non-goals.
- Seed file has 15–25 questions with `expected_source_roles` / forbidden roles where relevant.
- No retrieval implementation, manifest builder, or automated corpus mutation added in this PR.

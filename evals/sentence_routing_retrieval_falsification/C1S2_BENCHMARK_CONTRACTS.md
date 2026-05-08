# C1S2 Breadcrumb Retrieval — Benchmark Contracts

This document freezes taxonomy, artifact shapes, and anti-oracle rules for the Campaign 1 Session 2 (`C1S2`) natural-query slice. Source recap: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md`. The historical manual breadcrumb index is `manual_labels/Session 2 - Finishing the Job.breadcrumbed.md`; the current promoted control baseline is the routing-only refresh in §Current routing-only control baseline.

## Goals (non-goals)

- **Goal:** Prove lexical + route-grounded retrieval from the C1S2 breadcrumb artifact supports accurate answers in recall, prep, and planning-shaped questions.
- **Goal (wings):** A small subset of scenarios exercises “enough context for downstream tool prep” without grading any generated statblock or mechanical output.
- **Non-goal:** Scoring or gold-matching a produced monster/NPC statblock.

## Scenario categories (`category`)

Core retrieval (majority of gold, ~15 scenarios):

| `category` | Intent |
|------------|--------|
| `core_recall` | Direct factual recall from the recap index |
| `entity_context` | Entity-specific beats (NPC, party, creature mentions) |
| `event_context` | What happened in a beat (combat, discovery, negotiation) |
| `location_context` | Places and spatial references |
| `relationship_or_faction_context` | Social / negotiation / “who with whom” |
| `consequence_or_hook_context` | Outcomes, open threads, “what next” |

Future-use wings (optional, smaller):

| `category` | Intent |
|------------|--------|
| `planning_context` | Question phrased like prep for next session; still graded only on retrieval + must-hit tokens |
| `mechanical_prep_context` | Question about threats/loot/resources relevant to later statblock instructions; **no** mechanical gold |

## Gold schema

- Same as C1S1: `dmb_breadcrumb_query_natural_gold_v1` in `gold/breadcrumb_query_natural_c1s2_v1.json`.
- `default_query_spec.session_min` / `session_max` = **2** for C1S2.
- Each scenario includes: `expect_route_substrings`, `must_hit_tokens`, optional `notes` with corpus rationale (not model-output justification).

## Candidate artifact schema (`dmb_breadcrumb_query_candidates_v1`)

Emitted by `c1s2_query_candidate_build.py` (gold-agnostic).

| Field | Description |
|-------|-------------|
| `schema` | `dmb_breadcrumb_query_candidates_v1` |
| `source_breadcrumb_path` | Repo-relative path to the C1S2 `.breadcrumbed.md` |
| `campaign_id` | e.g. `longmont-c1` |
| `session_number` | `2` |
| `candidates[]` | List of candidate records |

Each `candidates[]` element:

| Field | Description |
|-------|-------------|
| `candidate_id` | Stable slug, e.g. `c1s2_cand_u-C1S2-01` |
| `category` | One of the taxonomy values above |
| `question` | Natural-language query |
| `expected_answer_draft` | Authoring hint; promoted to gold `expected_answer` after review |
| `must_hit_tokens_draft` | Token hints for gold |
| `supporting_unit_ids` | Normalized unit ids |
| `supporting_route_substrings` | Substrings matching grader normalization (corpus-relative routes) |
| `supporting_evidence_snippets` | Short embedded source text for human review (no extra file hops) |
| `notes` | Rationale / review hints |
| `review_status` | `pending` in generated output; human sets `accept` / `revise` / `reject` when promoting |

## Anti-oracle (leakage) guardrails

- **Candidate generation** must not read `gold/breadcrumb_query_natural_c1s2_v1.json` or any grader internals.
- **Tagging / repair prompts** must not include expected benchmark answers or gold-only tokens beyond what exists in the public recap + breadcrumb artifact.
- **Gold edits** after review must be justified from corpus/design intent in `notes`, not from “the model said X.”

## Canvas rules

- Generated regions in `.canvas.tsx` files are **emitter-owned** only; do not hand-edit between `BEGIN GENERATED` / `END GENERATED` markers.
- Candidate review canvas is a **projection** of candidate JSON; canonical state lives in JSON on disk.

## Breadcrumb alignment note (Session 2)

Sentence-unit joints concatenate without whitespace across `?` / `!` / `.` boundaries in some cases; the tag-stripped breadcrumb body must normalize to the same joint as the source recap. When several hook questions appear in one recap paragraph, **boundary tags** (e.g. a minimal `[Party][…]` immediately after `?`) may be required so inline-tag fragments do not span two units and duplicate routes onto the wrong sentence.

As of the 2026-05-08 refresh, the full manual `Session 2 - Finishing the Job.breadcrumbed.md`
artifact is not the promoted baseline until it is realigned with current normalization.
Use the routing-only report below for regression checks.

## Acceptance

- Three identical `breadcrumb_query_run.py` invocations against C1S2 gold; report pass counts, failing `scenario_id`s, violation families, and cost stats per `cost-as-signal` and suite README.

## Current routing-only control baseline (2026-05-08)

C1S2 is now the clean control lane for the routing-only cross-session refresh:

- Source recap: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md`
- Seed: `manual_labels/Session 2 - Finishing the Job.breadcrumbed.frontmatter_seed.md`
- Report: `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s2_routing_refresh_retrieval_only.json`
- Result: `all_ok: true`, 15/15 retrieval-only scenarios
- Cost: `$0.012705`

Use this lane as the first broad-regression check when changing routing-only prompt
behavior or deterministic rendering. A change that fixes C1S1 roster expansion,
C1S3 location hierarchy behavior, or C1S13 alias bridging should not break C1S2.

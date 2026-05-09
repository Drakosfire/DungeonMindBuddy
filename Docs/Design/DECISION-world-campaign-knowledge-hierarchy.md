# Decision: World and Campaign Knowledge Hierarchy

**Date:** 2026-05-08
**Status:** Accepted; implementation in progress

## Decision

DungeonMindBuddy separates durable setting knowledge from table-specific continuity with a two-layer subject model:

1. **World layer** (`canon_layer: world`, `campaign_id: null`) holds setting-side facts: world bible, location primers, pre-contact seeds, and setting-export statblocks.
2. **Campaign layer** (`canon_layer: campaign`, `campaign_id: longmont-cN`) holds table continuity: played-session recaps, campaign-specific dossiers, timelines, aliases, state changes, and campaign-specific mechanical overrides.

When the same subject exists in both layers, it gets **two sibling hubs**, not one merged folder:

- A setting/world hub under `Elderwyld/...`.
- A campaign/table hub under `Longmont Campaign/Campaign N/...`.

The sibling hubs cross-link by full corpus-relative path. Each hub defines what is authoritative **from that hub's perspective**.

This is not a new abstraction imposed on the corpus. It formalizes the shape already present in the best current corpus examples, especially Captain Lysandra Ironveil:

- `Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/README.md`
- `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md`

## Why

The old flat-folder shape mixed several kinds of truth:

- world-bible facts about who a person/place is in Elderwyld,
- campaign continuity about what happened at a specific table,
- mechanical statblocks at different tiers,
- session recaps and timelines with different freshness properties.

That confused both humans and planner agents. A model could read one file and accidentally treat table-state prose as timeless setting truth, or treat a setting statblock as the campaign-current sheet after sessions had changed the character.

The separation gives the planner a stable question to answer:

- "Am I answering about the setting as authored?"
- "Am I answering about what happened in Longmont Campaign 1 or Campaign 2?"
- "Which hub owns the current mechanical sheet for this perspective?"
- "Which recaps or timeline rows prove the table-side change?"

## Existing Evidence

### Corpus layout learnings

`Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md` records the core failure and fix:

- Flat Lysandra folders mixed world-bible and campaign-specific facts.
- Two cross-linked hubs worked better.
- README-first navigation and mechanical priority tables were necessary for reliable planner behavior.

### Conventions already encode the rule

`Docs/CONVENTION-Corpus-Subject-Schemas.md` defines the fields that make this decision machine-checkable:

- `document_class`
- `subject_class`
- `subject_doc_kind`
- `canon_layer`
- `campaign_id`
- `temporal_scope`
- `origin_session`
- `last_updated_session`

It also defines **sibling hub** as another hub for the same subject in a different canonical layer.

`Docs/CONVENTION-NPC-Hub-Package.md` makes the NPC-specific rule explicit:

- setting hub: seed and setting mechanical exports,
- campaign hub: dossier, timeline, campaign continuity, and table-specific overrides,
- README cross-links in both directions,
- no pinned default recap path.

`Docs/CONVENTION-PC-Hub.md` intentionally differs:

- PCs are campaign-only by default.
- A setting-side PC hub is rare and only appears if a PC becomes a recurring world/NPC subject.

`Docs/CONVENTION-Location-Hub.md` covers the location side:

- top-level setting hubs under `Elderwyld/...`,
- sub-location dossiers and nested region hubs,
- campaign-side play records remain under `Longmont Campaign/...`.

### Vertical slice already proved the invariant

`Docs/Design/DESIGN-layered-canon-vertical-slice.md` captures the broader Canon -> Planning -> Play model:

- lower layers are not rewritten by higher layers,
- campaign facts do not mutate world canon,
- play updates are additive overlays,
- projections are agent context, not GM-facing final output.

This decision narrows that broad model into the corpus layout and retrieval rule for subject hubs.

### Code already feels the pressure

`src/agent/corpus_writer.py` now has campaign-aware timeline resolution (`preferred_campaign_scope` / `campaign_id`) because same slugs can exist in multiple campaign trees. Backlog notes show the concrete failure: Campaign 1 and Campaign 2 PCs can share slugs, and slug-only timeline writes become ambiguous without campaign disambiguation.

`src/prompts/corpus_session_planner.py` already tells the planner to:

- open hub READMEs first,
- treat statblock priority tables as authoritative for mechanical questions,
- ask when table vs setting canon is ambiguous,
- derive most-recent recaps from the tree rather than from pinned README paths.

## Rules

### 1. World hubs are evergreen setting references

World-layer documents use:

```yaml
canon_layer: world
campaign_id: null
temporal_scope: evergreen
```

They answer "what is true about the setting independent of a particular campaign?"

They should not carry campaign-specific timeline rows, session-state changes, or table-earned level-up overrides.

### 2. Campaign hubs are table-state references

Campaign-layer documents use:

```yaml
canon_layer: campaign
campaign_id: longmont-c1 # or longmont-c2
temporal_scope: campaign_stateful # for living hubs
```

They answer "what is true for this table's continuity right now?"

They may point to world hubs for baseline context, but they do not rewrite the world hub.

### 3. Recaps remain the canonical chronology

Session recaps are `document_class: play`, `canon_layer: campaign`, and `temporal_scope: session_specific`.

Timelines, dossiers, and hub READMEs are projections or indexes. If they conflict with a cited recap, fix the projection; do not edit the recap to match the projection.

### 4. Sibling hubs cross-link explicitly

If a subject has both a world hub and a campaign hub, both READMEs must include:

- full corpus-relative path to the sibling hub,
- a short explanation of what lives in this hub vs the sibling,
- a mechanical priority table when any statblock exists,
- exact paths only; no shell globs in copyable path strings.

### 5. Mechanical priority is perspective-specific

A world hub may treat a setting statblock as current for the setting.

A campaign hub may prefer a campaign-specific override when present, falling back to the world statblock only when no table override exists.

The planner must read the actual statblock file before quoting CR, HP, AC, attacks, saves, or other numbered mechanics.

### 6. Writers must target campaign state unless explicitly world-authoring

Session-driven writes should create recaps or append campaign timelines. They must not update seeds, dossiers, or statblocks as a side effect.

World-layer authoring is a separate editorial act. It should not be inferred from play-session ingest.

## Current Implementation State

Implemented / largely present:

- Frontmatter fields for `canon_layer`, `campaign_id`, and temporal metadata.
- NPC, PC, and Location hub conventions.
- Lysandra sibling hubs as the worked example.
- README-first planner instructions.
- Campaign-aware timeline resolver work in `corpus_writer.py`.
- Normalized recap convention for prepared recap sources.

Partial / in progress:

- Not every subject has both hubs when it should.
- Some registries still use a setting hub as the campaign authority when no campaign hub exists.
- C1 PC hubs are explicitly absent in the PC convention.
- Location hierarchy is not yet fully represented in query behavior; recent breadcrumb retrieval showed that sublocation facts do not automatically imply parent-location membership.
- Some older files predate the subject-schema convention and still need frontmatter/hub migration when touched.

## Fresh-Agent Rework Scope

Start by auditing, not rewriting:

1. List subjects that already have both world and campaign hubs.
2. List subjects that have only a world hub but appear in a campaign registry or campaign recap.
3. List subjects that have only campaign hubs but should stay campaign-only (PCs by default).
4. Check whether each sibling pair has bidirectional README cross-links and perspective-specific mechanical priority.
5. Check whether registries distinguish `hub_path` (campaign authority) from `setting_hub_path` (world fallback) cleanly.
6. Check whether tools that accept only slugs also accept or derive `campaign_id`.

Do not create or move corpus hubs during the audit unless the user explicitly asks for migration. The first deliverable should be a gap report and migration plan.

## Roadmap: from here to dynamic lexical retrieval (reanchor plan)

This section is the execution map for "ingest all sessions and retrieve with the existing lexical retriever using matches generated from ingestion."

### Current state snapshot (2026-05-08)

- **Corpus session coverage:** Campaign 1 and Campaign 2 recaps are present, including normalized recap files.
- **Ingestion slices:** recap ingest + events-first Stage A/B/C/D surfaces exist and have run artifacts.
- **Contracts recently hardened:** registry authority split and campaign-id normalization checks are now deterministic and audited.
- **Still open before full fail-closed:** location-hierarchy equivalence contract is not yet fully encoded in all relevant benchmark gold.

### Target state

For every new recap:

1. ingest emits/update records with canonical routes and campaign scope,
2. lexical match handles are generated from those records (not hand-seeded per session),
3. existing lexical retriever uses the generated handles,
4. holdout sessions retrieve new facts without scenario-specific prompt provisioning.

### Phase plan

#### Phase A — Lock deterministic guardrails (current phase)

Goal: make structural drift fail before LLM-level tuning.

- Keep registry authority split strict (`hub_path` campaign authority vs `setting_hub_path` world fallback).
- Keep remote manifest campaign-id normalization strict (`longmont-cN` for campaign rows).
- Complete location-hierarchy contract encoding in breadcrumb natural-gold scenarios where parent labels rely on sublocation hits.

Exit criteria:

- alignment audit command is green for registry + manifest + hierarchy checks.
- no ambiguous "policy by convention" gaps remain in these three lanes.

#### Phase B — Dynamic lexical artifact generation

Goal: build lexical match inventory from ingestion outputs, not static hand curation.

- Define one generated artifact schema for lexical handles per campaign/session cohort (routes, aliases, key noun phrases, provenance pointers).
- Populate from ingestion surfaces already produced (normalized breadcrumb/session records and route-bearing units).
- Keep generation deterministic: same inputs produce byte-stable artifact output.

Exit criteria:

- lexical artifact is produced automatically from ingestion runs.
- artifact diffs are explainable by corpus/input changes only.

#### Phase C — Retriever wiring (reuse existing lexical retriever)

Goal: keep retrieval engine, swap lexical source-of-truth to generated artifact.

- Wire query expansion/lookup to load generated lexical handles first.
- Retain static fallback only as migration safety switch, not primary path.
- Add deterministic assertions that retrieval runs without session-specific hardcoded seed requirements.

Exit criteria:

- retrieval operates correctly with generated artifact enabled and static seeds removed for tested scenarios.
- failures clearly point to missing generated handles vs retriever behavior.

#### Phase D — Holdout proof on unseen recap sessions

Goal: prove this generalizes beyond Session 20-style familiarity.

- Choose holdout recap(s) not used to design the lexical seeds.
- Run ingest -> generate lexical artifact -> retrieval benchmark chain.
- Verify new facts/handles are discovered via generated artifact only.

Exit criteria:

- holdout retrieval passes required route/context gates without prompt retuning for that session.
- report includes one success sample and one failure sample per active failure type during iteration.

#### Phase E — "All sessions" operationalization

Goal: move from proof slice to campaign-wide ingest cadence.

- Run phased backfill across Campaign 1 + Campaign 2 recap sets.
- Emit per-run and cohort summaries with cost + gate telemetry.
- Add CI/manual gate target that fails on structural drift and retrieval-regression deltas.

Exit criteria:

- repeatable command path exists for full-session ingest + retrieval validation.
- on-ramp docs point to current command(s), artifacts, and known caveats.

### Resume protocol (how to pick this up later)

When resuming, always answer these first:

1. Which phase is currently active (A-E)?
2. What was the last green artifact path for that phase?
3. What is the single blocking red gate?
4. Is the blocker structural (contract/data) or prompt behavior?

If unclear, run deterministic checks first and re-anchor with their outputs before touching prompt text.

## Open Questions

These need explicit product/design decisions before broad migration:

- Should campaign registries require both `hub_path` and `setting_hub_path` for cross-layer subjects, or allow a world hub as a temporary `hub_path` fallback?
- Should location hierarchy be represented by redundant parent-location routes in breadcrumb artifacts, by deterministic hierarchy expansion at query time, or by explicit location-hub metadata?
- Should campaign-specific statblock overrides live only in campaign hubs, or may a world hub contain "published current" mechanical exports that are also used by one campaign?
- What is the exact migration trigger for older files: next substantive edit, lint-enforced deadline, or targeted campaign-by-campaign sweep?

## Related Documents

- `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — canonical execution super-plan (frontmatter, changelog) for split-corpus retrieval through autonomous C1S1–C1S3 demo; pairs with `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`.
- `Docs/Design/DESIGN-layered-canon-vertical-slice.md`
- `Docs/Design/DESIGN-lysandra-statblock-vertical-slice-benchmark.md`
- `Docs/Design/SCHEMA-document-temporal-metadata-v0.2.md`
- `Docs/CONVENTION-Corpus-Subject-Schemas.md`
- `Docs/CONVENTION-NPC-Hub-Package.md`
- `Docs/CONVENTION-PC-Hub.md`
- `Docs/CONVENTION-Location-Hub.md`
- `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md`
- `.cursor/rules/corpus-layout-conventions.mdc`

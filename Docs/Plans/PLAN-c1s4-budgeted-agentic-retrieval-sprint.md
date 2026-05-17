# C1S4 Budgeted and Agentic Retrieval Sprint Plan

## Purpose

This plan captures the retrieval design direction that emerged from PR40 and PR41’s Step 2C expected-context benchmark work.

The central finding is that DungeonBuddy should stop treating retrieval as a flat `top_k` list and start treating retrieval as the auditable construction of a planner working-memory packet.

A planning packet is not just “the first N retrieved records.” It is a bounded context object that should intentionally balance prior campaign memory, player/PC continuity, worldbuilding, support/adaptation knowledge, known gaps, and safety constraints.

PR40 showed why this matters. Q5’s Hempholm support card is not absent. It appears at diagnostic depth, but it is not admitted into the graded top-k planner-visible context. That is not a support-loading failure. It is an admission/ranking failure.

PR41 deepened the point. A flat 8k character-budget simulation can admit the Hempholm support card, but it may still appear late in the admitted context. This means we need to distinguish admission from presentation. The eventual consumer is an LLM, not a human reviewer, so context must be structured for model ingestion, not merely dumped as a flat list.

This sprint moves from deterministic diagnostics to deterministic budgeted retrieval, then to LLM-facing context rendering, then toward shadow-mode LLM retrieval planning.

---

## Current baseline after PR40/PR41

PR40 should be treated as the end of the first diagnostic loop.

PR40 provides:

- `retrieved_context_preview` for each Step 2C result row.
- `retrieval_depth_diagnostics` for required context groups.
- Improved normalization and matching for expected-context predicates.
- Configurable diagnostic retrieval depth via `max_hits`.
- PR-scoped benchmark artifacts under `evals/c1s4_preplanning_vertical_slice/artifacts/pr40/`.

PR41 provides:

- `budget_admission_diagnostics` for Step 2C rows.
- Deterministic character/token estimates.
- Simulated flat budget profiles.
- Simulated support-reserved budget profiles.
- Evidence that Q5 support can be admitted under an 8k character budget, while still failing official top-k grading.

Current benchmark interpretation:

- Q1 now passes in all modes.
- Q3 known-gap behavior still passes.
- Q5 prior-only still passes, with no support leakage.
- Q5 support modes still fail at graded top-k.
- The Q5 Hempholm support card is found at diagnostic depth.
- The Q5 Hempholm support card is admitted by flat 8k budget simulations.
- The Q5 Hempholm support card may still be late in admitted order, so final LLM packet rendering remains an unsolved problem.

Important distinctions:

```text
candidate recall at diagnostic depth: yes
admitted recall under flat 8k budget: yes
admitted recall at top_k=9: no
LLM-facing presentation quality: not yet measured
```

Those distinctions should drive the next sprint.

---

## Guiding architecture

The old model is too linear:

```text
question
  -> retrieve/rank
  -> take top_k
  -> planner packet
```

The target model is lane-aware, budget-aware, and LLM-renderer-aware:

```text
question
  -> query analysis / routing
  -> lane-specific retrieval
      - session memory
      - PC / party timeline
      - worldbuilding / location graph
      - support knowledge
      - known gaps / constraints
  -> candidate pools
  -> budgeted admission
  -> structured LLM-facing packet rendering
  -> planner / generator
```

Key distinction:

```text
Retrieval asks:
  What might be relevant?

Admission asks:
  What actually enters the planner packet?

Rendering asks:
  How should admitted context be structured so an LLM can use it correctly?

Benchmarking asks:
  Did the admitted/rendered packet contain the needed context, avoid forbidden material, and surface gaps honestly?
```

PR40 proved retrieval and admission should not be collapsed into a single flat top-k cutoff.

PR41 proved admission and presentation should not be collapsed either. Inclusion somewhere in an 8k context budget is not the same as useful model-facing organization.

---

## LLM-facing packet design principle

The packet consumer is an LLM, not a human reviewing a debug report.

Therefore, packet rendering should not be a flat list of admitted snippets. It should help the model separate:

- prior campaign events,
- player and PC behavior,
- NPC relationship history,
- location and worldbuilding context,
- support/adaptation material,
- known gaps,
- safety constraints,
- chronological facts,
- non-chronological world structure.

Different lanes need different ordering rules:

```text
session_memory:
  chronological or session-local order often matters

pc_timeline:
  summary first, then chronological examples

location/worldbuilding:
  hierarchy and locality often matter more than chronology

support_knowledge:
  relevance and authority matter more than prior-session chronology

known_gaps/safety_constraints:
  should appear early, before generative context
```

The renderer should use chronological order inside chronological sections, but it should not globally sort everything by time.

Bad:

```text
Sort every admitted item globally by time.
```

Better:

```text
Render sections by packet role.
Sort items inside each section according to that section’s logic.
```

This avoids burying support/adaptation context behind session-memory snippets while still preserving chronological order where chronology matters.

---

## Non-negotiable safety rules

These rules apply to every PR in this sprint.

- Do not use C1S4 oracle material in Steps 0-5.
- Do not retrieve by `question_id`.
- Do not retrieve by expected-context gold.
- Do not use `usable_for_questions` as a retrieval key.
- Do not let `prior_only` retrieve support cards.
- Do not make Q35 planner-facing.
- Do not loosen gold until anything passes.
- Do not hide failed rows from reports or canvas payloads.
- Preserve raw candidate rank even when admission changes.
- Preserve enough metadata for later LLM-facing rendering.
- Any LLM retrieval planner must propose plans only; deterministic code must validate, execute, filter, and admit context.

---

## Sprint overview

```text
PR40  Merge diagnostics + Q1 matcher repair
PR41  Add budget/admission diagnostics without changing behavior
PR42  Implement deterministic budgeted admission v1 and preserve presentation metadata
PR43  Add structured LLM-facing planner packet renderer
PR44  Add deterministic query-feature routing and lane planning
PR45  Expand expected-context gold from 3 questions to 8-10
PR46  Add shadow LLM retrieval planner
PR47  Evaluate shadow planner and define promotion gates
```

Visual roadmap:

```text
PR40
 Diagnostics + matcher repair
        ↓
PR41
 Measure budget behavior
        ↓
PR42
 Deterministic budgeted admission + presentation metadata
        ↓
PR43
 LLM-facing context renderer
        ↓
PR44
 Deterministic query router / lane plans
        ↓
PR45
 Gold expansion / generalization check
        ↓
PR46
 Shadow LLM retrieval planner
        ↓
PR47
 Compare, gate, maybe promote
```

---

# PR40 — Merge diagnostic foundation

## Purpose

PR40 should end as a clean diagnostic and matcher-repair PR.

It should not absorb budgeted retrieval or agentic retrieval work.

## Contributions

- Adds `retrieved_context_preview`.
- Adds `retrieval_depth_diagnostics`.
- Repairs Q1 matcher brittleness.
- Adds configurable diagnostic `max_hits`.
- Adds PR-scoped benchmark artifact evidence.
- Shows that Q5 support exists but ranks too low.

## Acceptance criteria

- Q1 passes in all modes.
- Q3 known-gap behavior passes.
- Q5 still fails in support modes, but diagnosis is clear.
- Forbidden violations remain 0.
- Focused tests pass.
- PR-scoped artifact exists.

---

# PR41 — Budget and admission diagnostics

## Proposed title

`Add budget-aware context admission diagnostics for Step 2C`

## Purpose

Do not change production packet behavior yet.

Add instrumentation that compares flat top-k behavior against character/token-budgeted packet construction.

PR41 should answer:

- Would Q5 pass if admitted context were budgeted by characters rather than top-k?
- Would Q5 pass only when support has a reserved lane?
- How many characters/tokens are packed per source kind?
- Which required groups are found at candidate depth but lost during admission?

## Core diagnostic distinction

Track both:

```text
candidate_rank
admitted_rank
```

Candidate rank preserves raw retrieval order.

Admitted rank describes where the item enters the planner-visible packet under a simulated budget policy.

## Suggested diagnostic shape

```json
{
  "budget_admission_diagnostics": {
    "candidate_depth": 50,
    "legacy_top_k": 9,
    "budget_profiles_checked": [
      "flat_ranked_4000",
      "flat_ranked_8000",
      "flat_ranked_12000",
      "support_reserved_25_8000",
      "support_reserved_35_8000"
    ],
    "required_groups": {
      "hempholm_tree_visible_threat": {
        "first_matching_candidate_rank": 27,
        "legacy_top_k_admitted": false,
        "flat_ranked_8000_admitted": true,
        "support_reserved_25_8000_admitted": true
      }
    }
  }
}
```

Add per-item diagnostic fields where useful:

```json
{
  "ref": "support:hempholm_road_hook_merchant_role",
  "candidate_rank": 27,
  "estimated_chars": 900,
  "estimated_tokens": 225,
  "source_kind": "support_knowledge_card"
}
```

Use a deterministic rough token estimate:

```text
estimated_tokens = ceil(chars / 4)
```

## Budget profiles to simulate

- `legacy_top_k_9`
- `flat_ranked_4000_chars`
- `flat_ranked_8000_chars`
- `flat_ranked_12000_chars`
- `support_reserved_25pct_8000_chars`
- `support_reserved_35pct_8000_chars`

## Expected finding

Likely:

```text
flat top_k=9:
  Q5 fails

flat 8000 chars:
  Q5 passes admission but may admit the relevant support late

8000 chars + support reservation:
  Q5 passes admission and admits more support, but may still need renderer structure
```

## Acceptance criteria

- No production packet behavior changes.
- Existing Step 2C pass/fail remains comparable to PR40.
- Reports show candidate rank versus simulated admitted rank.
- Q5 support admission can be analyzed under multiple budget profiles.
- Focused tests pass.
- No oracle boundary changes.

---

# PR42 — Deterministic budgeted admission v1

## Proposed title

`Implement deterministic budgeted admission with presentation metadata`

## Purpose

Turn the best budget policy from PR41 into actual packet construction.

This is the first PR that should make Q5 pass in support modes.

PR42 should admit the right context, but it should not try to solve final LLM prompt formatting. Instead, it must preserve enough metadata for the next PR to render admitted context well.

## Core behavior

Replace “take top-k” as the only admission mechanism with:

```text
retrieve candidates deeply
partition candidates into lanes
admit into planner packet by budget
preserve raw candidate rank
report admitted rank
preserve presentation metadata
```

Initial lanes:

- `session_memory`
- `support_knowledge_card`
- `known_gaps_or_constraints`

Do not add PC timeline or world graph lanes yet unless those data products are already reliable.

## Presentation metadata to preserve

Each admitted item should carry at least:

```json
{
  "ref": "support:hempholm_road_hook_merchant_role",
  "source_kind": "support_knowledge_card",
  "source_layer": "adaptation_planning",
  "candidate_rank": 37,
  "admitted_rank": 12,
  "admission_reason": "support_required_budget_admission",
  "presentation_lane": "support_knowledge",
  "estimated_chars": 420,
  "estimated_tokens": 105
}
```

Suggested initial `presentation_lane` values:

- `prior_campaign_memory`
- `support_knowledge`
- `known_gap`
- `safety_constraint`
- `unknown`

Later PRs can add:

- `pc_timeline`
- `party_timeline`
- `location_context`
- `worldbuilding`
- `npc_relationship_context`

## Suggested default budget profiles

For `support_knowledge_required`:

```text
total packet budget: 8000 chars

session_memory:
  floor: 2000
  target: 3200
  max: 4200

support_knowledge:
  floor: 2000
  target: 3200
  max: 4500

known_gaps/constraints:
  floor: 600
  target: 1200
  max: 1800
```

For `prior_recap_supported`:

```text
session_memory:
  dominant lane, 70-85%

support_knowledge:
  0 unless support mode and clear relevance

known_gaps/constraints:
  small but preserved
```

For `worldbuilding_required`:

```text
session_memory:
  medium

world/support:
  medium

known gaps:
  large enough to prevent hallucinated canon
```

## Rules

- `prior_only` makes support cards ineligible.
- Support modes make support cards eligible, but still relevance-gated.
- Preserve raw candidate rank.
- Assign admitted rank separately.
- Budget overflow must be deterministic.
- Unused lane budget may spill over to other lanes in a deterministic priority order.
- Preserve enough presentation metadata for PR43 to render sections without re-inferring source roles.

## Q5 target

Before:

```text
support card candidate rank: 37 / 27
admitted top-k: no
row passes: no
```

After:

```text
support card candidate rank: preserved
admitted into budgeted packet: yes
presentation_lane: support_knowledge
row passes: yes
```

## Acceptance criteria

- Q5 passes in both support modes.
- Q5 prior-only still passes with no support leakage.
- Q1 still passes in all modes.
- Q3 still passes known-gap expectations.
- Forbidden violations remain 0.
- The support card is admitted by general policy, not Q5-specific logic.
- Admitted items preserve `candidate_rank`, `admitted_rank`, `admission_reason`, and `presentation_lane`.
- Focused tests pass.

---

# PR43 — Structured LLM-facing planner packet renderer

## Proposed title

`Add structured LLM-facing planner packet renderer`

## Purpose

Build the first deterministic renderer for admitted context packets.

The consumer is an LLM, not a human reading debug output. The renderer should organize context so the model can distinguish prior play, worldbuilding, support/adaptation material, known gaps, and safety constraints.

This PR should not change retrieval or admission. It should transform already-admitted context into a structured LLM-ingestion format.

## Core principle

Do not render admitted context as one flat list.

Render by packet role and authority:

```text
1. Planning question
2. Retrieval/authority summary
3. Known gaps and safety constraints
4. Support / adaptation context
5. Prior campaign memory
6. Player / PC / party behavior context, when available
7. Location / worldbuilding context, when available
8. Provenance appendix or compact citation map
```

The first implementation can omit unavailable sections, but the renderer contract should make room for them.

## Suggested rendered structure

```markdown
# Planning Question

<user/planning question>

# Retrieval and Authority Summary

- Retrieval mode: <mode>
- Source sessions allowed: C1S1-C1S3
- Support knowledge allowed: yes/no
- Oracle material allowed: no
- Context budget: <chars/tokens>

# Known Gaps and Safety Constraints

- <gap or constraint items>

# Support / Adaptation Context

## <entity/location grouping if available>

- [ref] <support context>

# Prior Campaign Memory

## Chronological session memory

- [session/ref] <prior event/context>

# Character / Party Behavior Context

- [ref] <PC or party behavior context>

# Location / Worldbuilding Context

- [ref] <location/worldbuilding context>

# Provenance Map

- [ref] source_kind=<...> source_layer=<...> candidate_rank=<...> admitted_rank=<...>
```

## Sorting rules

Use section-specific sorting, not one global sort.

```text
known gaps / safety constraints:
  high-priority first, near the top

support knowledge:
  relevance/admission priority first, grouped by entity/location if possible

prior campaign memory:
  chronological or session-local order

PC / party behavior:
  summary first when available, then chronological examples

location / worldbuilding:
  hierarchy/locality first, then relevance
```

Do not globally sort all context by chronology. That would bury future-facing support/adaptation context.

## Renderer outputs

At minimum:

```json
{
  "schema": "dmb_planner_context_render_v1",
  "question_id": "...",
  "retrieval_mode": "...",
  "rendered_text": "...",
  "sections": [
    {
      "section_id": "support_knowledge",
      "title": "Support / Adaptation Context",
      "refs": ["support:hempholm_road_hook_merchant_role"],
      "chars": 1200,
      "estimated_tokens": 300
    }
  ],
  "provenance_map": {
    "support:hempholm_road_hook_merchant_role": {
      "source_kind": "support_knowledge_card",
      "source_layer": "adaptation_planning",
      "candidate_rank": 37,
      "admitted_rank": 12,
      "presentation_lane": "support_knowledge"
    }
  }
}
```

## Tests to add

- Q5 support mode renders Hempholm support in `Support / Adaptation Context`.
- Q5 prior-only does not render support context.
- Q1 renders Stone Bridge/Pippa/Bubbles/Grishna context under prior campaign memory.
- Q3 renders known route gaps near the top.
- Provenance map preserves candidate/admitted ranks.
- Renderer output excludes eval-only gold fields and oracle material.

## Acceptance criteria

- Renderer consumes admitted context only.
- Renderer does not change retrieval/admission behavior.
- Renderer groups context by LLM-ingestion role.
- Known gaps/safety constraints are placed before generative/support detail.
- Support context is clearly labeled as support/adaptation, not prior play.
- Prior memory preserves chronological/session ordering where available.
- Tests prove prior-only support exclusion is preserved.

---

# PR44 — Deterministic query-feature router and lane planning

## Proposed title

`Add deterministic query feature routing for lane-aware retrieval`

## Purpose

Move from static budget profiles toward query-sensitive retrieval depth and lane weighting.

Core principle:

```text
Use query features to modulate lane depth, lane budget, and admission floors/caps.
Do not use features to hard-route exclusively.
```

## Query features to extract

```json
{
  "detected_entities": {
    "pcs": [],
    "npcs": [],
    "locations": [],
    "objects": [],
    "sessions": [],
    "factions": []
  },
  "intent_signals": {
    "asks_for_prior_events": false,
    "asks_for_character_behavior": false,
    "asks_for_world_context": false,
    "asks_for_support_material": false,
    "asks_for_route_or_travel": false,
    "asks_for_generation": false
  },
  "authority_need": {
    "prior_memory": "low|medium|high",
    "support_knowledge": "low|medium|high",
    "worldbuilding": "low|medium|high",
    "known_gap_awareness": "low|medium|high"
  }
}
```

## Lane-plan output

```json
{
  "lane_plan": {
    "session_memory": {
      "candidate_depth": 50,
      "budget_weight": 0.45
    },
    "support_knowledge": {
      "candidate_depth": 30,
      "budget_weight": 0.35
    },
    "known_gaps": {
      "candidate_depth": 10,
      "budget_weight": 0.20
    }
  }
}
```

## Early deterministic heuristics

- PC name detected:
  - increase PC/player-history lane when available
  - increase session-memory depth
- Location detected:
  - increase world/location/support lane
- Session number detected:
  - boost exact session and adjacent-session context
- Route/travel language:
  - increase worldbuilding/route lane
  - increase known-gap lane
- Support-required authority label:
  - increase support lane floor and depth
- Creative-generation authority:
  - preserve constraints/gaps
  - avoid overstuffing facts

## Skeptical guardrails

Avoid these false assumptions:

- Capitalized word = definitely entity.
- Support mode = always include support.
- PC name = only retrieve PC lane.
- Keyword overlap = truth.

Use floors and caps so no plausible lane gets starved.

## Acceptance criteria

- Router emits deterministic lane plans.
- Lane plans are stored in report artifacts.
- Q1, Q3, and Q5 remain stable or improve.
- No oracle leakage.
- Tests cover PC/location/session/support feature cases.

---

# PR45 — Expand expected-context gold

## Proposed title

`Expand C1S4 expected-context gold coverage`

## Purpose

Stop overfitting Q1/Q3/Q5.

Once deterministic budgeted admission is working, expand the benchmark.

Do not jump to all 38 target questions. Add a curated batch.

## Suggested expansion batch

- Q4 — merchant hook / support knowledge
- Q6 — rumors / mixed support + prior context
- Q10 — first view of Hempholm / support knowledge
- Q13 — observable clues tree danger / support knowledge
- Q20 — tree battlefield / support knowledge
- Q22 — remains and loot / support knowledge
- Q25 — celebration / support knowledge
- Q17 — Stafl social behavior / prior + mixed character behavior
- Q27 — PC likely reactions / prior behavior

Aim for 8-10 total gold questions after expansion, not all 38.

## Each new gold entry needs

- Mode-specific expectations.
- Required context groups.
- Forbidden context groups.
- Known gaps.
- Authority label.
- Oracle risk.
- Clear reasons for each required group.

## Q35 stays excluded

Q35 remains evaluator-only and must not become planner-facing.

## Acceptance criteria

- Gold expands beyond seed coverage.
- No expected group depends on oracle material.
- Q35 remains excluded from planner-facing runs.
- Benchmark includes at least one support, prior, mixed, and known-gap case.
- PR42/PR43 behavior generalizes beyond Q5.

---

# PR46 — Shadow LLM retrieval planner

## Proposed title

`Add shadow LLM retrieval planner for corpus-aware retrieval plans`

## Purpose

Introduce the LLM only as a retrieval-plan proposer.

It should not execute retrieval, decide truth, mutate context, or directly admit planner-visible context.

This runs in shadow mode first and does not affect production packets.

## Architecture

```text
question
  + corpus schema
  + lane descriptions
  + graph/index summary
  + allowed operators
  + oracle boundary rules
  -> LLM retrieval planner
  -> strict JSON retrieval plan
  -> deterministic validator
  -> deterministic executor in shadow
  -> comparison report
```

## Prompt input should include

- Available lanes.
- Source-kind meanings.
- Authority labels.
- Known corpus structures.
- Allowed query operators.
- Session boundary policy.
- Support-mode policy.
- Examples of safe plans.
- Forbidden behaviors.

Do not include:

- Expected-context gold.
- Question IDs as retrieval handles.
- `usable_for_questions`.
- C1S4 oracle.
- Answer hints.

## Strict schema

```json
{
  "schema": "dmb_retrieval_plan_v1",
  "question_summary": "string",
  "detected_entities": {
    "pcs": [],
    "npcs": [],
    "locations": [],
    "objects": [],
    "sessions": [],
    "factions": []
  },
  "intent_signals": {
    "asks_for_prior_events": true,
    "asks_for_character_behavior": false,
    "asks_for_world_context": true,
    "asks_for_support_material": true,
    "asks_for_generation": true
  },
  "lane_queries": [
    {
      "lane": "support_knowledge",
      "query_text": "Hempholm tree metallic magical merchant road hook",
      "required_terms": ["Hempholm"],
      "optional_terms": ["tree", "metallic", "merchant"],
      "candidate_depth": 40,
      "rationale": "Question asks for support-specific Hempholm tree description."
    }
  ],
  "admission_profile": {
    "profile": "support_knowledge_required",
    "budget_chars": 8000,
    "lane_weights": {
      "session_memory": 0.35,
      "support_knowledge": 0.40,
      "known_gaps": 0.25
    }
  },
  "safety": {
    "requires_oracle": false,
    "must_not_use_oracle": true
  }
}
```

## Validation

Reject plans that:

- Reference unknown lanes.
- Include held-out session ranges.
- Use support lane in `prior_only`.
- Contain oracle leakage tokens.
- Reference expected gold.
- Reference question IDs as retrieval keys.
- Request excessive candidate depth.
- Lack rationales.

## Caching

Cache retrieval plans by:

- Normalized question.
- Retrieval mode.
- Corpus schema hash.
- Policy hash.
- Prompt hash.
- Model ID.

This keeps benchmark runs replayable.

## Acceptance criteria

- Shadow plans are generated and stored.
- Plans do not affect production packet construction.
- Validator catches unsafe plans.
- Reports compare deterministic baseline versus shadow plan.
- Q1/Q3/Q5 shadow behavior is inspectable.
- No oracle leakage.

---

# PR47 — Shadow planner evaluation and promotion gates

## Proposed title

`Evaluate shadow retrieval planner against deterministic baseline`

## Purpose

Decide whether the LLM planner earns any production responsibility.

## Metrics

Compare deterministic baseline versus shadow planner on:

- Candidate recall at depth.
- Admitted recall under budget.
- Rendered-section recall.
- Known-gap recall.
- Forbidden violation rate.
- Support-card admission rate.
- Plan validation failure rate.
- Query drift rate.
- Cost and latency.
- Cache hit rate.

## Critical cases

- Q1:
  - LLM should preserve prior/session focus.
  - Rendered packet should put Stone Bridge/Pippa/Bubbles/Grishna in prior campaign memory.
- Q3:
  - LLM should preserve known-gap awareness.
  - Rendered packet should put route gaps near the top.
- Q5:
  - LLM should activate support lane and admit Hempholm support.
  - Rendered packet should put Hempholm support in Support / Adaptation Context.
- Expanded gold:
  - LLM should improve support/mixed queries without degrading prior-only or known-gap cases.

## Promotion gate

The LLM planner may influence deterministic lane plans only if:

- Forbidden violation rate remains 0.
- Known-gap recall does not regress.
- Prior-only support leakage remains 0.
- Required-context admitted recall improves meaningfully.
- Rendered-section placement does not regress.
- Plan validation failure rate is low.
- Query drift is inspectable and bounded.
- Results are replayable from cache.

## If promoted

Promote only one capability at a time:

```text
Phase 1:
  LLM may propose lane depth changes.

Phase 2:
  LLM may propose query expansions per lane.

Phase 3:
  LLM may propose graph hints.

Never:
  LLM directly admits context without deterministic validation.
```

---

## Key artifacts to preserve across PRs

Each PR should leave behind artifacts that future agents can inspect.

Suggested artifacts:

- `retrieval_plan.json`
- `lane_plan.json`
- `candidate_pool_diagnostics.json`
- `budget_admission_diagnostics.json`
- `rendered_context_packet.json`
- `rendered_context_packet.md`
- `expected_context_report.json`
- `canvas_payload.json`

Each artifact should help answer:

- What was retrieved?
- From which lane?
- At what raw rank?
- At what admitted rank?
- Why was it admitted?
- What budget did it consume?
- Which required groups did it satisfy?
- What gaps/constraints were surfaced?
- Where was the context rendered for the LLM?
- Did rendered structure match the context’s authority and role?

---

## Sprint risks and mitigations

## Risk 1 — Budgeted admission becomes hidden top-k

If we simply take the first N characters from a global ranked list, we have not solved the problem.

Mitigation:

- Use lane-aware floors and caps.
- Report source-kind budget consumption.
- Track `candidate_rank` and `admitted_rank` separately.

## Risk 2 — Support cards invade everything

Support mode should make support eligible, not mandatory.

Mitigation:

- Require relevance gates.
- Keep `prior_only` strict.
- Use spillover if support is irrelevant.

## Risk 3 — Admitted context becomes an LLM-hostile blob

A flat list can include the right facts while still making it hard for the LLM to distinguish prior play, support, worldbuilding, known gaps, and constraints.

Mitigation:

- Preserve presentation metadata in PR42.
- Add structured LLM-facing renderer in PR43.
- Test rendered section placement for Q1, Q3, and Q5.

## Risk 4 — Query-router overconfidence

Entity detection and keyword signals are noisy.

Mitigation:

- Use floors and caps, not hard routing.
- Keep baseline retrieval available.
- Report router decisions.

## Risk 5 — LLM query drift

LLM expansion can regress retrieval by introducing attractive but wrong vocabulary.

Mitigation:

- Shadow mode first.
- Strict schema.
- Plan validation.
- Plan caching.
- Compare against deterministic baseline.
- Keep the original query protected.

## Risk 6 — Benchmark overfits Q5

Q5 is useful but only one support case.

Mitigation:

- Expand gold after deterministic budgeted admission and renderer contract.
- Add multiple support, prior, mixed, and known-gap cases.

---

## Practical sprint sequence

```text
Sprint A — Close diagnostic foundation
  Merge PR40.

Sprint B — Budget visibility
  PR41: budget/admission diagnostics and sweeps.

Sprint C — Deterministic packet construction
  PR42: budgeted lane admission with presentation metadata.
  Goal: Q5 support modes pass without prior-only leakage.

Sprint D — LLM-facing packet presentation
  PR43: structured planner packet renderer.
  Goal: admitted context is organized for model ingestion, not human debug reading.

Sprint E — Query-sensitive routing
  PR44: deterministic query feature router.
  Goal: lane depth/budget responds to PC/location/session/support signals.

Sprint F — Benchmark expansion
  PR45: expand gold to 8-10 questions.
  Goal: prove PR42/PR43/PR44 generalize.

Sprint G — Agentic retrieval shadow
  PR46: LLM retrieval planner in shadow.
  PR47: evaluate and define promotion gates.
```

---

## One-sentence thesis

DungeonBuddy should stop treating retrieval as “top-k results” and start treating it as auditable construction of an LLM-ingestible planner working-memory packet, where deterministic lane retrieval, budgeted admission, structured context rendering, known-gap preservation, and eventually shadow LLM retrieval planning cooperate without compromising oracle safety.

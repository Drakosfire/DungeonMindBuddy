# C1S4 Budgeted and Agentic Retrieval Sprint Plan

## Purpose

This plan captures the retrieval design direction that emerged from PR40’s Step 2C expected-context benchmark work.

The central finding is that DungeonBuddy should stop treating retrieval as a flat `top_k` list and start treating retrieval as the auditable construction of a planner working-memory packet.

A planning packet is not just “the first N retrieved records.” It is a bounded context object that should intentionally balance prior campaign memory, player/PC continuity, worldbuilding, support/adaptation knowledge, known gaps, and safety constraints.

PR40 showed why this matters. Q5’s Hempholm support card is not absent. It appears at diagnostic depth, but it is not admitted into the graded top-k planner-visible context. That is not a support-loading failure. It is an admission/ranking failure.

This sprint moves from deterministic diagnostics to deterministic budgeted retrieval, then toward shadow-mode LLM retrieval planning.

---

## Current baseline after PR40

PR40 should be treated as the end of the first diagnostic loop.

PR40 provides:

- `retrieved_context_preview` for each Step 2C result row.
- `retrieval_depth_diagnostics` for required context groups.
- Improved normalization and matching for expected-context predicates.
- Configurable diagnostic retrieval depth via `max_hits`.
- PR-scoped benchmark artifacts under `evals/c1s4_preplanning_vertical_slice/artifacts/pr40/`.

Current benchmark interpretation:

- Q1 now passes in all modes.
- Q3 known-gap behavior still passes.
- Q5 prior-only still passes, with no support leakage.
- Q5 support modes still fail at graded top-k.
- The Q5 Hempholm support card is found at diagnostic depth, but too late for the current planner packet.

The important distinction:

```text
candidate recall at diagnostic depth: yes
admitted recall at top_k=9: no
```

That distinction should drive the next sprint.

---

## Guiding architecture

The old model is too linear:

```text
question
  -> retrieve/rank
  -> take top_k
  -> planner packet
```

The target model is lane-aware and budget-aware:

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
  -> planner packet
```

Key distinction:

```text
Retrieval asks:
  What might be relevant?

Admission asks:
  What actually enters the planner packet?

Benchmarking asks:
  Did the admitted packet contain the needed context, avoid forbidden material, and surface gaps honestly?
```

PR40 proved these should not be collapsed into a single flat top-k cutoff.

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
- Any LLM retrieval planner must propose plans only; deterministic code must validate, execute, filter, and admit context.

---

## Sprint overview

```text
PR40  Merge diagnostics + Q1 matcher repair
PR41  Add budget/admission diagnostics without changing behavior
PR42  Implement deterministic budgeted admission v1
PR43  Add deterministic query-feature routing and lane planning
PR44  Expand expected-context gold from 3 questions to 8-10
PR45  Add shadow LLM retrieval planner
PR46  Evaluate shadow planner and define promotion gates
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
 Deterministic budgeted admission
        ↓
PR43
 Deterministic query router / lane plans
        ↓
PR44
 Gold expansion / generalization check
        ↓
PR45
 Shadow LLM retrieval planner
        ↓
PR46
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
        "flat_ranked_8000_admitted": false,
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
  Q5 may still fail or be inconsistent

8000 chars + support reservation:
  Q5 likely passes
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

`Implement deterministic budgeted admission for support retrieval modes`

## Purpose

Turn the best budget policy from PR41 into actual packet construction.

This is the first PR that should make Q5 pass in support modes.

## Core behavior

Replace “take top-k” as the only admission mechanism with:

```text
retrieve candidates deeply
partition candidates into lanes
admit into planner packet by budget
preserve raw candidate rank
report admitted rank
```

Initial lanes:

- `session_memory`
- `support_knowledge_card`
- `known_gaps_or_constraints`

Do not add PC timeline or world graph lanes yet unless those data products are already reliable.

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
admitted rank: inside planner packet
row passes: yes
```

## Acceptance criteria

- Q5 passes in both support modes.
- Q5 prior-only still passes with no support leakage.
- Q1 still passes in all modes.
- Q3 still passes known-gap expectations.
- Forbidden violations remain 0.
- The support card is admitted by general policy, not Q5-specific logic.
- Focused tests pass.

---

# PR43 — Deterministic query-feature router and lane planning

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

# PR44 — Expand expected-context gold

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
- PR42 behavior generalizes beyond Q5.

---

# PR45 — Shadow LLM retrieval planner

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

# PR46 — Shadow planner evaluation and promotion gates

## Proposed title

`Evaluate shadow retrieval planner against deterministic baseline`

## Purpose

Decide whether the LLM planner earns any production responsibility.

## Metrics

Compare deterministic baseline versus shadow planner on:

- Candidate recall at depth.
- Admitted recall under budget.
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
- Q3:
  - LLM should preserve known-gap awareness.
- Q5:
  - LLM should activate support lane and admit Hempholm support.
- Expanded gold:
  - LLM should improve support/mixed queries without degrading prior-only or known-gap cases.

## Promotion gate

The LLM planner may influence deterministic lane plans only if:

- Forbidden violation rate remains 0.
- Known-gap recall does not regress.
- Prior-only support leakage remains 0.
- Required-context admitted recall improves meaningfully.
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

## Risk 3 — Query-router overconfidence

Entity detection and keyword signals are noisy.

Mitigation:

- Use floors and caps, not hard routing.
- Keep baseline retrieval available.
- Report router decisions.

## Risk 4 — LLM query drift

LLM expansion can regress retrieval by introducing attractive but wrong vocabulary.

Mitigation:

- Shadow mode first.
- Strict schema.
- Plan validation.
- Plan caching.
- Compare against deterministic baseline.
- Keep the original query protected.

## Risk 5 — Benchmark overfits Q5

Q5 is useful but only one support case.

Mitigation:

- Expand gold after deterministic budgeted admission.
- Add multiple support, prior, mixed, and known-gap cases.

---

## Practical sprint sequence

```text
Sprint A — Close diagnostic foundation
  Merge PR40.

Sprint B — Budget visibility
  PR41: budget/admission diagnostics and sweeps.

Sprint C — Deterministic packet construction
  PR42: budgeted lane admission.
  Goal: Q5 support modes pass without prior-only leakage.

Sprint D — Query-sensitive routing
  PR43: deterministic query feature router.
  Goal: lane depth/budget responds to PC/location/session/support signals.

Sprint E — Benchmark expansion
  PR44: expand gold to 8-10 questions.
  Goal: prove PR42/43 generalize.

Sprint F — Agentic retrieval shadow
  PR45: LLM retrieval planner in shadow.
  PR46: evaluate and define promotion gates.
```

---

## One-sentence thesis

DungeonBuddy should stop treating retrieval as “top-k results” and start treating it as auditable construction of a planner working-memory packet, where deterministic lane retrieval, budgeted admission, known-gap preservation, and eventually shadow LLM retrieval planning cooperate without compromising oracle safety.

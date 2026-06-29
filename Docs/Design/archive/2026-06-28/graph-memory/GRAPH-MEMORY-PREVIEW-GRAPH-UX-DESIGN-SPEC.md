# Graph Memory Preview Graph UX Design Spec v0

## Purpose

This PR defines the GM-facing preview experience for candidate graph memory. It does not implement runtime UI, execute extraction, write graph memory, approve writes, execute queries, connect `/plan`, connect Agent Interaction, or promote facts/canon.

The preview graph is not campaign truth. It is an evidence-backed proposal for GM inspection.

The purpose of the Preview Graph UX is to help a GM inspect candidate memory before anything becomes durable campaign memory. The experience should make candidate graph output legible as a review workflow rather than a raw JSON report.

## Current Foundation

The graph-memory workstream already has design and eval artifacts for evidence-backed preview output:

- Source Span Evidence Resolver Contract v0
- Candidate Graph Preview IR v0
- Rich Recap Dogfood Fixture v0
- Session 23 Raw Recap Ingest Fixture v0
- Session 23 Hand-Authored Candidate Graph Gold Fixture v0
- Multi-Pass Extraction Contract v0
- Eval-Only Extractor Harness Fixture v0
- Static Extractor Output Comparison Report v0

Those artifacts prove that static candidate graph output can be contract-shaped, preview-only, evidence-backed, high-risk audited, compared against gold, classified as safe / unsafe / incomplete, and summarized for reviewers.

## Product Problem

A static comparison report can say `safe_but_incomplete`, `hard failures: 0`, `evidence health: pass`, `high-risk audit: pass`, and `GM preview readiness: not_ready_for_gm_preview`. That is useful for a reviewer but not yet a GM product surface.

The GM needs to answer:

- What did DungeonBuddy think happened?
- What evidence supports it?
- What is missing?
- What is risky?
- What would be written if approved in a future workflow?
- What should be approved, rejected, or deferred once approval mechanics exist?

## GM Trust Goal

DungeonBuddy should not silently remember everything. DungeonBuddy should propose useful memory, show why it believes it, and let the GM decide what becomes durable.

No item should become durable memory without explicit future approval mechanics.

## Preview Graph UX Principles

### 1. Evidence first

Every candidate memory item must expose source evidence. The GM should never have to trust the model blindly.

### 2. Preview, not truth

Candidate graph output is proposed memory, not canon. The UI must label preview objects as proposals and avoid language that implies promotion.

### 3. Safety before completeness

Hard failures block trust even if coverage is high. The UX must separate safety failures from quality/coverage misses.

### 4. Completeness before convenience

Bulk approval should be unavailable or restricted when coverage is weak. A candidate output can be safe to inspect while still not ready for GM preview.

### 5. High-risk claims require friction

Identity binding, alias binding, cliffhanger outcomes, uncertain counts, and inferred relationships require special visibility and review friction.

### 6. Missing coverage is part of the product

The UI should show what DungeonBuddy failed to capture, not only what it captured.

### 7. Deferred is a first-class outcome

Not every item is approved or rejected. Some items should remain deferred because the session source does not resolve them.

## Source Data Inputs

A future UI should consume data shaped by existing artifacts, not invent product behavior ahead of the contracts:

- Candidate Graph Preview IR
- Static Extractor Output Comparison Report
- Resolved Evidence refs
- High-Risk Audit summary
- Proposed Write summary
- GM Preview Readiness state

Expected future payload groups include:

- `verdict`
- `score_summary`
- `coverage_summary`
- `hard_failure_summary`
- `soft_miss_summary`
- `missing_gold_coverage`
- `extra_candidate_coverage`
- `evidence_health`
- `high_risk_audit_summary`
- `proposed_write_summary`
- `gm_preview_readiness`
- candidate graph nodes
- candidate graph edges
- candidate graph beats
- ignored items
- deferred items
- proposed writes
- resolved evidence refs

No new runtime schema is required in this PR. Future payloads should preserve stable candidate IDs, source anchor IDs, evidence resolution state, risk flags, proposed write linkage, review eligibility, and disabled-action reasons.

## User Journey

1. GM opens a session memory preview summary.
2. GM checks safety, evidence health, high-risk audit state, and GM preview readiness.
3. GM reviews missing coverage and soft misses before considering individual candidates.
4. GM inspects candidate nodes, edges, beats, ignored items, and deferred items in a structured explorer.
5. GM opens a candidate detail view to inspect source evidence and proposed write implications.
6. GM reviews the proposed writes queue to understand what would eventually become durable memory.
7. Future controls allow approve / reject / defer intent, but this design rung only describes those controls.

## Information Architecture

The first useful version should be structured-review-first rather than graph-visualization-first:

- Preview Summary
- Candidate Graph Explorer
- Evidence-Backed Candidate Detail
- Proposed Writes Queue
- Missing Coverage and Soft Misses
- Hard Failures and Safety Blocks

Graph visualizations may be added later as supplemental context, but table/card inspection is the primary v0 review model.

## Screen 1: Session Memory Preview Summary

This is the GM landing screen. It should answer:

- Is this preview safe?
- Is it complete enough?
- What did DungeonBuddy find?
- What is missing?
- Should I inspect, reject, or defer?

Suggested content:

- Session title / session ID
- Preview status
- Safety gate
- GM preview readiness
- Candidate counts
- Coverage score bands
- Evidence health
- High-risk audit status
- Proposed write count
- Hard failure count
- Soft miss count
- Recommended next action

Example for the current static sample:

```text
Session 23 Memory Preview

Status: Safe but incomplete
GM preview readiness: Not ready for GM preview
Safety: Pass
Evidence: 206 / 206 refs resolve and highlight
High-risk audit: Pass
Candidate nodes: 33 / 42 gold
Candidate edges: 8 / 23 gold
Candidate beats: 6 / 14 gold
Proposed writes: 6 pending
Hard failures: 0
Soft misses: 45

Recommendation: Safe to inspect, not safe to approve in bulk.
```

## Screen 2: Candidate Graph Explorer

This view lets the GM inspect graph structure through tabs or sections:

- Nodes
- Edges
- Beats
- Threads
- NPCs
- Locations
- Groups
- Threats
- Ignored
- Deferred

Each item card should show:

- label
- type
- confidence / readiness
- evidence count
- risk flags
- proposed write status
- linked beats
- linked edges
- review state

The design should avoid graph-visualization-first UX. Graph visualizations are optional later. The first useful version is likely a structured review table/card list.

## Screen 3: Evidence-Backed Candidate Detail

This is the trust-building screen. For a selected candidate, show:

- candidate label
- candidate type
- description
- why it was proposed
- source evidence snippets
- source anchor IDs
- open source action
- highlight source action
- related nodes / edges / beats
- high-risk warnings
- proposed write preview
- review action controls

Evidence interaction states:

- resolved
- openable
- highlightable
- warning
- unresolved
- unknown anchor
- heading-only
- source leakage blocked

The UI should make unresolved evidence visually obvious and should not hide evidence problems behind a generic warning.

## Screen 4: Proposed Writes Queue

This screen shows what would eventually become durable memory if future approval mechanics allowed it. It should group proposed writes by type:

- create node
- create edge
- create beat
- create thread
- update node
- defer item
- ignore item

For each proposed write:

- write ID
- target ID
- write type
- status
- candidate source
- evidence count
- risk flags
- approval eligibility
- reason approval is disabled, if disabled

For v0 design, all write actions should be conceptual or disabled.

This PR does not implement approval mechanics.

## Screen 5: Missing Coverage and Soft Misses

This view turns eval misses into user-legible gaps. It should show:

- missing nodes
- missing edges
- missing beats
- missing proposed writes
- missing ignored items
- missing deferred items

Group misses by priority:

- critical
- important
- nice to have

For the current static sample, the design should make clear:

- Edges and beats are weak.
- The candidate is safe to inspect but not good enough for GM preview.

## Screen 6: Hard Failures and Safety Blocks

This view should only matter when something unsafe happens. Hard failures should block approval-like actions.

Potential hard failure categories:

- dangerous diagnostic flag
- promoted lifecycle forbidden
- approved write forbidden
- unknown evidence anchor
- unresolved evidence ref
- source leakage
- runtime leakage
- corpus mutation
- LLM execution required

The UI should show:

- failure category
- affected object
- why it blocks trust
- suggested next action

Suggested next actions are inspect / reject / defer, not auto-fix.

## Evidence Interaction Model

Evidence is a first-class review object. Each candidate detail view should include evidence snippets, anchor IDs, resolution status, and actions to open or highlight the source.

Evidence states should be displayed as:

- `resolved`: source reference resolves.
- `openable`: source can be opened.
- `highlightable`: exact span can be highlighted.
- `warning`: evidence exists but has degraded fidelity.
- `unresolved`: source reference cannot be resolved.
- `unknown anchor`: anchor ID is not known to the resolver.
- `heading-only`: evidence resolves only to a broader heading or paragraph.
- `source leakage blocked`: source points outside allowed preview input.

Unresolved or blocked evidence should affect approval eligibility in future designs.

## High-Risk Claim Display

High-risk claims need explicit warning treatment. Examples include:

- Lysandro name + father relationship
- Lysandra recognizes Lysandro edge
- Heroes / party vs canonical party-name binding
- remaining approaching horde vs unsupported second-wave wording
- cliffhanger outcome
- exact uncertain counts
- alias binding
- identity merge
- relationship inference

The UI should distinguish:

- high-risk audit passed
- high-risk audit missing evidence
- high-risk audit failed
- high-risk claim deferred

When high-risk audit passes, still show the warning as “review carefully,” not “trust blindly.”

## Proposed Write Display

Proposed writes should be shown as preview consequences, not active mutations. Each proposed write should link back to its candidate source and evidence. Disabled approval reasons should be visible beside the write rather than hidden in a tooltip-only affordance.

## Approve / Reject / Defer Intent Model

This PR defines future intent states, but does not implement them.

Suggested future states:

- unreviewed
- approved
- rejected
- deferred
- needs_more_evidence
- needs_split
- needs_merge
- campaign_context_required

Suggested future actions:

- approve candidate
- reject candidate
- defer candidate
- open evidence
- highlight source
- mark needs more evidence
- mark requires campaign context
- split candidate
- merge with existing memory

For this design PR:

- All write-changing actions are illustrative only.
- No approval state is persisted.
- No memory is written.

## Bulk Action Rules

Bulk approval should be restricted. Product rules for future implementation:

- No bulk approval when hard failures exist.
- No bulk approval when evidence health is below 1.0.
- No bulk approval when high-risk audit fails.
- No bulk approval for high-risk claims.
- No bulk approval when GM preview readiness is `not_ready_for_gm_preview`.
- Bulk defer may be allowed in a future design.
- Bulk reject may be allowed in a future design.

These are product rules only and are not implemented in this PR.

## Empty / Incomplete / Unsafe States

- Empty candidate: show that nothing was proposed and provide no approval affordance.
- Incomplete candidate: allow inspection, emphasize coverage gaps, and disable bulk approval.
- Unsafe candidate: show hard failures first and block approval-like actions.
- Invalid report: show validation failure and avoid candidate review claims.

## GM Preview Readiness States

Visible readiness states:

```text
ready_for_gm_preview
not_ready_for_gm_preview
unsafe_for_preview
invalid
```

Suggested display:

```text
ready_for_gm_preview:
  Safe to inspect. Candidate may be reviewable by GM.

not_ready_for_gm_preview:
  Safe to inspect, but coverage is too weak for useful review.

unsafe_for_preview:
  Hard failures exist. Do not use for memory approval.

invalid:
  Report or candidate graph failed validation.
```

## Agent Interaction Readiness

The Preview Graph UX is not an Agent Interaction integration. The design can describe future review intent and source evidence display, but Agent Interaction should not consume candidate graph memory until approved durable graph memory exists in a future rung.

## Accessibility and Legibility Notes

- Do not encode safety, coverage, or risk with color alone.
- Use explicit labels for `safe_but_incomplete`, `not_ready_for_gm_preview`, unresolved evidence, and high-risk claims.
- Keep source evidence snippets readable and expandable.
- Provide keyboard-reachable review controls in future UI work.
- Ensure disabled controls expose visible disabled reasons.

## Out of Scope

This PR does not:

- implement runtime UI
- add React components
- add routes
- add API endpoints
- call an LLM
- execute live extraction
- generate output from recap text
- write graph memory
- approve graph writes
- implement approve / reject / defer behavior
- execute graph queries
- scan or mutate `corpus/**`
- connect `/plan`
- connect Agent Interaction
- promote facts
- promote canon
- change production behavior

## Future Implementation Rungs

1. Static preview graph UI prototype using checked-in fixture/report data only.
2. Static accessibility and review-state prototype.
3. Preview approval / write intent contract.
4. Persistence design for approval state after explicit gate.
5. Runtime UI integration after fixture-only prototype review.
6. Agent Interaction use only after approved durable graph memory exists.

Recommended next PR: `graph-memory: add static preview graph UI prototype v0`.

## Acceptance Criteria

- UX spec clearly defines the GM review flow.
- UX spec separates safety failures from quality/coverage misses.
- UX spec treats preview graph as proposal, not truth.
- UX spec includes evidence interaction model.
- UX spec includes high-risk claim display.
- UX spec includes missing coverage view.
- UX spec includes proposed writes queue.
- UX spec includes future approve / reject / defer intent controls.
- UX spec explicitly states approval/write behavior is out of scope.
- No runtime/app/corpus files are modified.

# Hermes × World Graph interaction design reset — executive handback

**Prepared:** 2026-07-14  
**Repository observed:** `Drakosfire/DungeonMindBuddy`  
**Current main/base SHA observed:** `4e9b489351ac2aa3eee3e62584b7fe0dd2cffac7`  
**PR356 head reviewed:** `2f10dd579fc14b2ea6cbc455de2b12ac2db2f4b9`

## Decision summary

```text
PR356 recommendation:
SUPERSEDE WITH REPLACEMENT PR. Preserve bounded prose replay concepts/tests for a later
referent-continuity slice; do not merge PR356 as the foundation of the next ladder.

First confirmed failure boundary:
The preflight-to-Hermes handoff. The panel has resolved candidate nodes/edges/attributes,
but the Hermes request discards them and retains only scope/revision. The immediate runtime
cause of the canned abstention still requires the operator's instrumented Tripod run.

Selected authority model:
Authority varies by claim class. Accepted explicit graph claims are canonical graph authority.
Successful source reads add source verification, quotation, and deeper detail. Derived summaries
are not factual authority by default. Inferences are disclosed and noncanonical.

Selected retrieval architecture:
One server-owned GraphRetrievalSession and claim ledger shared by the panel and Hermes,
with deterministic candidate resolution, agent-requested bounded expansions, and admitted
source reads.

Selected panel role:
Shared human/agent exploration and answer-support inspector: current referents, candidates,
claims used, inferences, opened/available/unreadable sources, connected objects, gaps,
conflicts, revision, and admissibility.

Selected grounding/reference model:
Claim-level graph grounding; graph references for accepted claims; source citations only after
successful source reads; explicit partial coverage, inference, conflict, abstention, and
execution-error states.

Bounded prose replay disposition:
Retain as a low-priority lexical aid after explicit/selected/pinned/resolved durable referents.
Reimplement/consolidate after the shared retrieval protocol, not as the current critical path.

Durable Hermes session disposition:
Deferred until the new read architecture passes cumulative dogfood. It remains optional and
may never be necessary if persisted referents plus bounded visible prose are sufficient.

Tripod source-data repair required:
Yes. Audit/rebuild the active Eldyrwild head so graph-native contribution source-payload digests
are revision-bound and Tripod JSON-pointer anchors are readable. This is necessary but not a
complete product fix.

Immediate implementation slices:
0 forensic capture + Tripod digest migration;
1 claim authority/ledger;
2 shared retrieval session;
3 retrieval-plan executor;
4 source-read ledger/citations;
5 structured answer validator;
6 panel/trace convergence;
7 selected referents + bounded prose;
8 cumulative dogfood/demolition;
9 optional durable sessions.

Code/contracts to delete:
Independent query-dependent panel semantics; current model-facing five-tool vocabulary;
anchor-presence grounding classifier; opaque anchor-only citation contract; candidate-only
WorldGraphQueryContextPanel; generic graph trace shell; duplicated history policy; synthetic
anchor tests that claim product grounding.

PR011 status:
BLOCKED until the authority ADR, shared retrieval/claim ledger, source/reference model,
selected referents, full scenario suite, Tripod real-agent dogfood, and demolition gate pass.

Unresolved operator decisions:
1. Accept or reject graph claims as first-class factual authority by claim class.
2. Approve superseding PR356 rather than merging it.
3. Approve the shared retrieval-session rebuild and destructive demolition scope.
4. Decide whether old persisted turns need a migration UI or a legacy read-only badge.
```

## Experiments run

- current PR metadata/head/path inventory;
- base/head comparison;
- full relevant PR patch/source review;
- canonical architecture/roadmap/tracker/Hermes story review;
- preflight → host field mapping;
- raw Kernel result → tool-event summary → classifier mapping;
- Tripod contribution/source-anchor/digest/source-read trace;
- pinned Hermes 0.18.2 callback source review;
- current product/UI trace and fake-host test review;
- GitHub combined status check.

## Real-agent environment

```text
Model/provider: not run in this environment
Activated world graph: not available
Browser runtime: not available
Local repository checkout/tests: not available
```

This package does not claim the mandatory Tripod browser reproduction was completed. It narrows the remaining runtime forensic to no-tool, no-completion, no-anchor, or malformed-result branches and supplies Slice 0 to capture it before implementation redesign proceeds.

## Documents

```text
Docs/Reports/REVIEW-pr356-in-context-of-hermes-graph-design-reset.md
Docs/Reports/HERMES-GRAPH-INTERACTION-AS-BUILT-AUDIT.md
Docs/Reports/HERMES-GRAPH-TRIPOD-DOGFOOD-FORENSIC.md
Docs/Design/ADR-hermes-graph-authority-grounding-and-citations.md
Docs/Design/UX-STORIES-hermes-world-graph-interaction-v2.md
Docs/Design/DESIGN-hermes-graph-agent-story.md
Docs/Design/ARCHITECTURE-hermes-world-graph-interaction.md
Docs/Research/RESEARCH-agent-interaction-with-canonical-knowledge-graphs.md
Docs/Design/EVAL-hermes-world-graph-interaction.md
Docs/Plans/PLAN-hermes-world-graph-interaction-rebuild.md
Docs/Plans/PROPOSED-REANCHOR-hermes-world-graph-active-docs.md
```

## Explicit deviations from the jumpstart

1. The runtime forensic packet could not be captured because the operator’s live browser, activated graph root, and real model environment were not available.
2. Tests were not run because no repository checkout/runtime was available; no test-pass claim is made.
3. Documents were prepared as a sandbox package rather than written to GitHub.
4. No PR was opened, merged, closed, or modified.

```text
STOP. PRESENT DESIGN FOR OPERATOR REVIEW.
DO NOT OPEN AN IMPLEMENTATION PR.
DO NOT BEGIN DURABLE SESSION CONTINUITY.
DO NOT UNBLOCK PR011.
```

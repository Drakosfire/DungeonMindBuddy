# Re-anchor — Hermes Campaign Authoring Foundation

**Date:** 2026-07-15
**Scope:** Hermes workstream and current implementation branch
**Status:** PRODUCT DIRECTION ACCEPTED; UI baseline green; S1 gate rejected; Phase 0 code/UI gate remains open
**Related plan:** [`PLAN-hermes-campaign-authoring-foundation-reset.md`](PLAN-hermes-campaign-authoring-foundation-reset.md)
**Active design index:** [`../Design/INDEX-hermes-campaign-authoring-foundation.md`](../Design/INDEX-hermes-campaign-authoring-foundation.md)

This is the explicit Phase 1 re-anchor record. It reconciles the active Hermes
design set with the implementation branch and the Campaign Supergraph
infrastructure roadmap. It does not claim that backend demolition, UI cleanup,
creative workflow primitives, or statblock promotion are complete.

## Evidence used

- Buddy branch `agent/pr010b5-plan-hermes-thread-continuity`:
  `1d0b52398cfc9161d50b01d31340c8e9c33c7bce`
- `origin/agent/pr010b5-plan-hermes-thread-continuity` was fetch-verified at
  the same commit.
- Buddy `origin/main` remains at `4e9b4893`, whose documented critical path is
  PR010B Rung 5 same-thread continuity.
- The 2026-07-15 archive batch and its link/boundary verification are recorded
  in the parent repository's `Docs/Archive/2026-07-15/`.
- The current branch contains bounded Hermes graph retrieval and visible-prose
  continuity work. It does not yet contain a generic
  `CreativeOperationSession`, `GenerationPacket`, `DraftArtifact`,
  `PromotionPlan`, or `CommitReceipt` implementation.
- The deterministic S1 latest-recap artifact is green, while the three-trial real
  Plan/Hermes dogfood is recorded as rejected in
  [`../Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md`](../Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md).

## Re-anchor decisions

These decisions are accepted as the product direction for the reset:

1. **Hermes is a campaign sensemaking and authoring partner**, not a retrieval
   report generator.
2. **Free-form text is the primary interaction contract.** Workflow buttons may
   provide context or a suggested question, but they do not replace agent
   judgment with hidden forms.
3. **Retrieval is a governed evidence boundary.** The World Supergraph and
   graph-admitted source anchors remain factual authority; Hermes owns
   interpretation, clarification, and tool choice within server-owned bounds.
4. **Graph incompleteness becomes useful disclosed context.** An empty first
   result is not automatically the final answer when bounded admitted context
   can support investigation. A true graph/source gap remains visible.
5. **Generated output is always a draft until explicit promotion.** No Hermes
   turn, background worker, or conversation state can silently create campaign
   canon.
6. **Statblocks are the first full authoring proving domain.** Locations, NPCs,
   and encounters are later schema and promotion mappings over the same workflow
   kernel.
7. **Conversation continuity is contextual, never factual authority.** The
   current bounded visible-prose replay is retained as a continuity primitive;
   fresh graph retrieval remains authoritative for each factual turn.
8. **The primary UI is conversation and draft review.** Evidence, revision,
   trace, and diagnostics remain available as secondary inspection surfaces.

## Proving sequence

The active documents used “first proving slice” for two different purposes. The
sequence is now explicit:

### S0 — retained read-only foundation

Retain the revision-pinned graph retrieval boundary and bounded same-thread
continuity work already present on the branch. This is infrastructure evidence,
not proof that the authoring reset is complete.

### S1 — first conversational acceptance

> “What changed after the latest ingested recap?”

This is the first sensemaking acceptance. It must identify the latest admitted
recap and comparison boundary, select meaningful movement, disclose uncertainty
and memory lag, and keep support inspectable without turning the answer into a
ledger.

### S2 — first full authoring proof

> “Collect everything we know about this threat. What is missing? Help me create
> a statblock for it.”

This is the first end-to-end authoring gate: retrieval, clarification, typed
packet, draft review, promotion preview, explicit confirmation, commit receipt,
and post-commit retrieval verification.

S2 must not begin by adding more domains or by extending the legacy planner
path. S1 and S2 share the same retrieval/evidence boundary.

## Retained systems and boundaries

Retain:

- revision-pinned World Supergraph projection and graph retrieval;
- graph-admitted source-anchor reads;
- server-owned scope, admissibility, bounds, revision, and authority checks;
- bounded conversation continuity as noncanonical context;
- the existing v2 statblock workbench/lifecycle as the first domain adapter;
- explicit preview/confirmation semantics from the agent-authored-prep contract;
- answer-first Plan interaction with evidence and diagnostics behind inspection.

Do not promote yet:

- the existing Hermes interaction package to the generic creative workflow
  kernel without the S1/S2 contract;
- old graph-only rung documents to active product authority;
- the current Plan thread/session persistence to campaign memory;
- existing graph-review authoring fixtures to canonical promotion.

## Demolition and cleanup decisions

The document archive pass is complete. The initial runtime/UI cleanup slice is now
complete and its evidence is recorded in the Phase 0 reports:

- The dead Hermes CLI/context path, superseded five-tool adapter, dead Plan toolbar,
  and primary Plan backend picker were removed after reference scans.
- Legacy Live/Hermes switching outside the graph path, duplicate retrieval surfaces,
  grounding-first answer framing, and remaining debugger-like chrome are deferred
  quarantine candidates with owners and gates in the cleanup maps.
- The current graph retrieval and continuity path is retained as the S0
  foundation, even where later authoring work will simplify its boundaries.
- The Graph Review workbench remains a secondary inspection/authoring surface;
  it is not replaced by conversational generation until the statblock loop has
  a reviewable draft and governed promotion path.

## Phase 0 exit work still open

Before new creative primitives are built, the reset now has the required maps,
reference scan, retained-adapter list, stale-test list, and explicit approval record
for the initial removal set. The UI failure families have been triaged and the
broader gate still needs:

- repair and rerun of the rejected S1 latest-recap read-only dogfood;
- replacement-owner decisions for deferred Live, planner, and Graph Review paths.

The current branch is therefore **re-anchored for direction and the initial cleanup
slice, but not released from the broader Phase 0 implementation gate**.

## Next gate

Repair the S1 route so an empty focused graph does not terminate the turn before
Hermes can use the server-provided latest-recap context. Rerun the S1 read-only
dogfood acceptance before constructing `CreativeOperationSession`.
The next implementation slice must be independently falsifiable and must not
add another graph tool or domain-specific generation path without satisfying
that gate.

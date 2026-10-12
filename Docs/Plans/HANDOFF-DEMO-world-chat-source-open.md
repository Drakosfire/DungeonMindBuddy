# HANDOFF — DEMO: open sources from durable World conversation

**Status:** BLOCKED design, 2026-10-12. This document grants no implementation path or runtime lease.
**Owner:** DEMO; PRIME controls activation, review and merge.
**Design base:** Buddy `main@1710af3cb4d167346c0ce0388ffc9bf0868338e8`.
**Topology if activated:** one serial Buddy UI consumer PR after the exact SERVER projection and SOURCE reader contracts are merged and pinned. Re-anchor main, open PRs and path leases before activation.

## User action and invariant

In ordinary saved World Plan conversation, the GM asks a question, sees a useful Graph-backed answer, opens the relevant supporting passage from that same saved turn, and can do so again after history reload without another provider call. A passage that only supplies related recap context is labelled as context; it does not prove the claim. Missing or unreadable source is shown as source access failure, distinct from missing World knowledge. The operator's Stacey continuity challenge remains a separate acceptance fixture awaiting an identity/species decision; this consumer does not authorize a Graph or corpus write.

The current durable `WorldPlanAgentConversation` displays Graph claim text, revision, `source_opened`, evidence IDs and V2 read IDs, but offers no citation-linked open action. The existing `PlanAgentInteractionBar` “Open evidence” test covers a different Hermes interaction. `source_read_id` is a receipt identity, not an opener. Neither evidence IDs, legacy span labels nor model text may be transformed into an anchor or context ID by naming convention.

At answer production, SERVER is expected to project a versioned, persisted `source_open_targets` binding for a genuine admitted evidence anchor. It binds the Graph claim, evidence ID, opaque anchor and exact authority tuple; only this target may use the existing `/world-graph/retrieval/source-anchor/read` route and the label **Open evidence**. A separately projected `related_source_context` target may identify Core-authorized recap context for the same artifact/revision. It uses SOURCE's distinct descriptor/read route and the label **Open source context**; it is never counted as claim support. The UI consumes the exact settled response/history types and verifies the returned identity before displaying content. It does not choose an arbitrary source from a global catalog or claim that `source_opened` means the GM clicked a passage.

## Gates before ACTIVE

1. ARCHITECTURE and PRIME settle the exact persisted target schema, claim/evidence/anchor or context tuple, historical replay behavior, and response validation. APP-STATE requires no new schema under the current ruling; recheck if the final producer contract changes.
2. SERVER's versioned `source_open_targets` and `related_source_context` projection is merged at an exact head after its producer-side evidence-ID/edge-ID repair. It must supply exact native World, scope, campaign, focus, admissibility and Graph revision pins, with a trustworthy target-to-citation association.
3. SOURCE's distinct Core-authorized recap-context read route is merged and pinned. Core's World-scope campaign-recap corrective must be settled; the UI must not narrow ordinary chat to a campaign picker to work around it. Genuine evidence-anchor reads retain their existing route.
4. Confirm no collision with active UI consumer, shared API type, history or reader leases. Activate only the exact paths needed by the merged producer contracts.

## Proposed UI write set after activation

- `apps/live-control-ui/src/api/types.ts` — consume strict additive target types if not already supplied by SERVER.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx` — citation actions, bounded read state and current World/conversation fencing.
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx` — mounted fresh and restored history witnesses.
- A colocated source-reader component/style and `apps/live-control-ui/src/api/liveApi.ts` with its focused test only if the accepted SOURCE route requires transport not already present.
- This handoff, when activated and settled.

No SERVER, APP-STATE, Core, Graph source, corpus, provider, database or runtime path is reserved by this BLOCKED design. Reuse an installed UI dependency lane for verification; a missing `vitest` binary in one scratch clone does not establish a repository test failure.

## Owning-boundary proof when activated

- Fresh V2 answer: one claim opens its exact evidence anchor; a related recap context opens only through the separate context route with an honest label. Request bytes carry the saved native World/scope/campaign/focus/admissibility/revision and target ID, never current selection or a guessed ID.
- Saved history reopen: the same persisted target opens without resubmitting the question or invoking the provider. V1/metadata-only history remains readable and does not acquire fabricated source-opened status.
- Wrong World, graph revision, evidence/anchor/context tuple, read response snapshot or source digest does not display content. Unsupported and legacy opaque sources show a clear unavailable state; no current-HEAD or whole-document fallback.
- Switching World, conversation or turn clears visible passage content and ignores a late read from the prior scope. Source read failures remain distinct from Graph evidence absence and answer failure.
- Preserve the producer's `source_opened` meaning as an Agent read receipt; a separate UI state records the GM's on-demand opening. Run focused mounted/API tests, inspect the cumulative diff and return exact head to PRIME. A synthetic UI pass does not certify useful answers, a real source opening or the later operator acceptance witness.

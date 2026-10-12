# HANDOFF — DEMO: open sources from durable World conversation

**Status:** ACTIVE UI consumer, 2026-10-12, authorized by PRIME against SERVER PR #1090 merged at `5614fb1c9156a6a42aed94e2f2422f52df412667` (DTO code `98bc9eb18cda45daffc50d94d32947051c92368b`). SOURCE #1089 merged at `8fce46de7e33bc352300abdf3ece0369a3ac1e68`; no runtime or operator acceptance is claimed.
**Owner:** DEMO; PRIME controls activation, review and merge.
**Branch/base:** `codex/demo-world-chat-source-open-design`, re-anchored to Buddy `main@36a44d5e67133ae5a2d5061c6c2ac759d14d467b` after checking open PRs. One draft UI consumer PR is under review against the merged producer contract.

## User action and invariant

In ordinary saved World Plan conversation, the GM asks a question, sees a useful Graph-backed answer, opens the relevant supporting passage from that same saved turn, and can do so again after history reload without another provider call. A passage that only supplies related recap context is labelled as context; it does not prove the claim. Missing or unreadable source is shown as source access failure, distinct from missing World knowledge. The operator's Stacey continuity challenge remains a separate acceptance fixture awaiting an identity/species decision; this consumer does not authorize a Graph or corpus write.

The current durable `WorldPlanAgentConversation` displays Graph claim text, revision, `source_opened`, evidence IDs and V2 read IDs, but offers no citation-linked open action. The existing `PlanAgentInteractionBar` “Open evidence” test covers a different Hermes interaction. `source_read_id` is a receipt identity, not an opener. Neither evidence IDs, legacy span labels nor model text may be transformed into an anchor or context ID by naming convention.

At answer production, SERVER is expected to project a versioned `source_open_targets` list from the stored turn, keyed by citation `claim_id`. A genuine evidence target binds the admitted opaque anchor, evidence ID, source artifact/revision and exact frozen authority tuple; only this target may use the existing `/world-graph/retrieval/source-anchor/read` route and the label **Open evidence**. A `related_recap_context` target may be attached only when a Core-authorized descriptor's artifact/revision pair matches admitted citation provenance at that pinned projection. It carries an opaque context ID and exact descriptor tuple, uses SOURCE's distinct reader route, and bears the label **Open related recap context**. It is never counted as claim support. The UI consumes the exact settled response/history types and verifies returned identity before displaying content. It does not choose an arbitrary source from a global catalog or claim that `source_opened` means the GM clicked a passage.

## Contract pins and remaining gates

1. ARCHITECTURE's portable source-open ruling is pinned at SHA-256 `d1502b6cea6172e170a6008000bf0f60f99ce84635c37adc872bcd4a03f0dea4a`. SERVER must publish the exact target DTO and historical replay shape. APP-STATE requires no new schema under this UI projection ruling; recheck if the final producer contract changes.
2. SERVER's versioned `source_open_targets` projection, including the separate `related_recap_context` target kind and additive evidence/recap availability statuses, merged in PR #1090 at `5614fb1c9156a6a42aed94e2f2422f52df412667`. The UI includes `source_campaign_id` and verifies it against the read descriptor. It accepts bounded partial/overflow status while retaining valid links. Targets carry exact native World, scope, campaign, focus, admissibility and Graph revision pins with a trustworthy target-to-citation association.
3. SOURCE's distinct Core-authorized recap-context read route merged via #1089 at `8fce46de7e33bc352300abdf3ece0369a3ac1e68`; Core's World-scope campaign-recap corrective is included. The UI does not narrow ordinary chat to a campaign picker. Genuine evidence-anchor reads retain their existing route.
4. Open PRs checked 2026-10-12: SOURCE #1089 owns only backend/Core pin paths; remaining draft UI PRs do not touch this consumer or its API types/history test. Recheck before PR. No shared runtime, port, database or external state lease.

## Proposed UI write set after activation

- `apps/live-control-ui/src/api/types.ts` — consume strict additive target types if not already supplied by SERVER.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx` — citation actions, bounded read state and current World/conversation fencing.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css` — readable source actions and bounded passage layout in the ordinary answer.
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx` — mounted fresh and restored history witnesses.
- A colocated source-reader component/style and `apps/live-control-ui/src/api/liveApi.ts` with its focused test only if the accepted SOURCE route requires transport not already present.
- This handoff, when activated and settled.

No SERVER, APP-STATE, Core, Graph source, corpus, provider, database or runtime path is reserved by this UI lease. Reuse an installed UI dependency lane for verification; a missing `vitest` binary in one scratch clone does not establish a repository test failure.

## Owning-boundary proof when activated

- Fresh V2 answer: one claim opens its exact evidence anchor; a related recap context opens only through the separate context route with an honest label. Request bytes carry the saved native World/scope/campaign/focus/admissibility/revision and target ID, never current selection or a guessed ID.
- Saved history reopen: the same persisted target opens without resubmitting the question or invoking the provider. V1/metadata-only history remains readable and does not acquire fabricated source-opened status.
- Wrong World, graph revision, evidence/anchor/context tuple, read response snapshot or source digest does not display content. Unsupported and legacy opaque sources show a clear unavailable state; no current-HEAD or whole-document fallback.
- Switching World, conversation or turn clears visible passage content and ignores a late read from the prior scope. Source read failures remain distinct from Graph evidence absence and answer failure.
- Preserve the producer's `source_opened` meaning as an Agent read receipt; a separate UI state records the GM's on-demand opening. Run focused mounted/API tests, inspect the cumulative diff and return exact head to PRIME. A synthetic UI pass does not certify useful answers, a real source opening or the later operator acceptance witness.

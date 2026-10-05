# HANDOFF — DEMO: recover successful Plan Ask across SPA remount

**Status:** SETTLED — PR #919 merged; implementation write lease released.

**Owner:** DEMO

**Repository/base:** `Drakosfire/DungeonMindBuddy`, PR base `main@498353516a1ed49c48d4039e0edc218e63419424` (PR #918); merged to current `main@4731245e5ccce8eb1179449903c40c824dc64a48`.

**Branch/checkout:** `codex/demo-plan-ask-spa-recovery-v1`, isolated checkout `/tmp/dmb-demo-plan-ask-spa-recovery`.

**Topology:** implementation ran parallel-independent from #914 at codex/demo-plan-card-projection-fidelity@41e81264802b4235ef1e81ccace6aab76b10ab1e and #917 at codex/dogfood-focused-plan-adapter@05fa6365b710c70ab0aea56849fb63d30177d669. The #914 diff was path-disjoint. PR #917 historically included the two UI paths below; PRIME transferred exclusive production ownership of those paths to DEMO until this lane settled. That transfer ended when #919 merged. No prototype code was imported. The #914 visual witness remains a separate pending gate for its own slice.

## Mission and observed failure

A canonical saved-World Plan Ask can finish successfully after its original `WorldPlanAgentConversation` component unmounts during SPA navigation. The accepted server turn must then be visible from canonical World history, while its exact local recovery envelope is retired only if that same stored record is still present.

At the pinned base, `sendPendingAsk` returns before validating or settling the response when its original component is no longer mounted. The local pending envelope remains, and an already-remounted subscriber has no same-document signal to reread local recovery and refresh server history when the response arrives. The existing #915 fence handles a late response within the mounted component and is settled; this is a separate remount-recovery capability.

## Accepted behavior

1. Validate a successful response against the immutable captured request envelope and captured committed Plan origin even after the dispatching component unmounts. Require the existing response identity, canonical conversation UUID, and committed-basis checks. The canonical `conversation_id` is distinct from the client `turn_id`.
2. Compare the current localStorage bytes at the captured key with the exact bytes persisted for that request. Remove only an exact match. If the key is missing, replaced, malformed, or unreadable, preserve the current record and its idempotent recovery path.
3. For a validated successful response, dispatch one same-document settlement event with only a version, the storage key, and safe origin metadata (World, document and committed-basis identity). Use the cleared event only after exact removal; if the captured record is missing, replaced, malformed, or unreadable, send the separate accepted-result event so history can still refresh while the current recovery record remains. Never include request text, response text, credentials, or the full envelope.
4. A mounted subscriber for that same World/document rereads pending local recovery and refreshes canonical server history on either settlement event. It ignores unrelated or malformed event details. On ordinary remount it also reads current localStorage and fetches canonical history as it does today.
5. Keep React state updates behind the original component's mounted/scope/request-token fence. A successful unmounted response may settle its captured storage record and notify the correct subscriber, but it must not write into stale component state or a newly selected World/document.
6. Network errors, malformed or unknown responses, and response/basis mismatches do not clear the captured record or emit a cleared event. Explicit retry continues to use the exact request and client turn ID. Remounting does not automatically POST a second time.
7. Do not change schemas, correlation APIs, provider behavior, server ownership, Graph behavior, or canonical history authority. The server transcript remains the source of truth for completed turns.

## Implementation write lease — released

These were the only implementation paths changed in this lane:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-plan-ask-spa-recovery-v1.md`

The handoff was committed before either source/test path was edited. The exclusive lease on these three paths ended when PR #919 merged. No implementation edits remain active under this handoff. Do not infer runtime, server, APP-STATE, or #914 authority from this completed UI slice.

## Runtime, data and fixture ownership

This is a browser UI recovery slice verified with mounted tests, deferred mocked API responses, synthetic IDs/content, and test localStorage. It uses no live provider, service, database, port, credential, operator World, corpus, or external state. Do not use production data to prove it.

## Owning-boundary acceptance

- Mounted regression: send one synthetic Ask and hold the successful response; unmount and remount before resolving it; verify the remount initially sees the exact pending envelope and no completed answer; then return a valid response with a canonical conversation UUID distinct from the client `turn_id`. Assert one POST, exact-key/byte retirement, a same-document event containing only the approved metadata, no automatic retry, one canonical-history refresh, and the server turn appearing in the remounted transcript.
- Replacement regression: while the request is pending, replace the stored bytes at the captured key. A later valid success must not remove those replacement bytes or report that envelope as cleared. Recovery remains available.
- Replacement-success history regression: even when replacement bytes remain, the same-document subscriber refreshes canonical history and displays the accepted server turn; it does not auto-POST the retained recovery envelope.
- Error/unknown regression: after remount, reject or return a malformed/unknown response. The original bytes remain and no cleared event is emitted. An explicit retry sends the exact captured request/client turn ID.
- Preserve current-context fences: a response for another World/document or malformed origin cannot refresh or mutate the selected subscriber.
- Run the focused mounted Plan conversation/history suite, `git diff --check`, and inspect the exact cumulative base-to-head diff. Record any inherited failures without broadening this lease.

## Implementation verification and review

- Focused mounted history suite: 21/21 passed, including late success after unmount/remount, exact canonical-history refresh, canonical conversation UUID distinct from client `turn_id`, replacement-byte preservation, malformed/network failure preservation and exact explicit retry.
- `git diff --check` against the pinned base passes.
- UI typecheck is blocked by the inherited main error `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`; that file is unchanged from the pinned base.
- PR #919's final reviewed head was `9e2fbdd418d61301fc88f99b9bd4baea6a32150e`; PRIME reported an independent exact-head PASS. GitHub's review API contains no submitted PR review, and the commit-status API returned no status entries.
- PR #919 merged into main at `4731245e5ccce8eb1179449903c40c824dc64a48`. This settles the recovery implementation only; it does not establish runtime or visual acceptance for #914 or operator acceptance of the full DEMO mission.
- The byte comparison is synchronous in this document, but localStorage has no transactional compare-delete operation across browsing contexts. This protects a replacement already present when settlement starts; cross-tab concurrent writes to the same key are outside this slice. Pending keys are per submitted turn and explicit retry reuses the same envelope. Do not describe this as a cross-tab atomic CAS guarantee.

## Publication and settlement

- Published as [PR #919](https://github.com/Drakosfire/DungeonMindBuddy/pull/919), based on the pinned main SHA above. The PR opened at `70c312988880579b4aae415095f7f740e608043a`; follow-up commits added the replacement-success history refresh and its regression before final review.
- PRIME reviewed final head `9e2fbdd418d61301fc88f99b9bd4baea6a32150e` and merged PR #919 at `4731245e5ccce8eb1179449903c40c824dc64a48`. The implementation lease is closed and its three paths are released.
- No live runtime, provider, database, credentials, operator World, or corpus was touched. #914's synthetic visual witness remains separate; its shared API timing question is unresolved and did not gate this PR.

## Slice disposition

This implementation slice is settled after exact-head review and merge. The complete DEMO mission remains open until its separate journey and operator-acceptance gates pass.

# HANDOFF — DEMO: recover successful Plan Ask across SPA remount

**Status:** ACTIVE — PRIME authorized this bounded production slice and its exact paths.

**Owner:** DEMO

**Repository/base:** `Drakosfire/DungeonMindBuddy`, fetched remote `main@498353516a1ed49c48d4039e0edc218e63419424` (PR #918).

**Branch/checkout:** `codex/demo-plan-ask-spa-recovery-v1`, isolated checkout `/tmp/dmb-demo-plan-ask-spa-recovery`.

**Topology:** parallel-independent from #914 at codex/demo-plan-card-projection-fidelity@41e81264802b4235ef1e81ccace6aab76b10ab1e and #917 at codex/dogfood-focused-plan-adapter@05fa6365b710c70ab0aea56849fb63d30177d669. The #914 diff is path-disjoint. The current #917 diff historically includes the two UI paths below, but PRIME explicitly transferred exclusive production ownership of those paths to DEMO and instructed DOGFOOD to hold new edits until this lease settles. Its pushed diff remains prototype-reconciliation material, not an active competing writer or implementation dependency. Do not import prototype changes. PRIME owns independent review and merge coordination.

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

## Exclusive expected write lease

Only these paths may change in this lane:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-plan-ask-spa-recovery-v1.md`

The handoff is committed before either source/test path is edited. If implementation or owning-boundary evidence requires another path or contract, stop and ask PRIME for a bounded lease change. Do not edit the roadmap, API types, server, APP-STATE, migrations, package manifests, lockfiles, prototype, or #914 files.

## Runtime, data and fixture ownership

This is a browser UI recovery slice verified with mounted tests, deferred mocked API responses, synthetic IDs/content, and test localStorage. It uses no live provider, service, database, port, credential, operator World, corpus, or external state. Do not use production data to prove it.

## Owning-boundary acceptance

- Mounted regression: send one synthetic Ask and hold the successful response; unmount and remount before resolving it; verify the remount initially sees the exact pending envelope and no completed answer; then return a valid response with a canonical conversation UUID distinct from the client `turn_id`. Assert one POST, exact-key/byte retirement, a same-document event containing only the approved metadata, no automatic retry, one canonical-history refresh, and the server turn appearing in the remounted transcript.
- Replacement regression: while the request is pending, replace the stored bytes at the captured key. A later valid success must not remove those replacement bytes or report that envelope as cleared. Recovery remains available.
- Replacement-success history regression: even when replacement bytes remain, the same-document subscriber refreshes canonical history and displays the accepted server turn; it does not auto-POST the retained recovery envelope.
- Error/unknown regression: after remount, reject or return a malformed/unknown response. The original bytes remain and no cleared event is emitted. An explicit retry sends the exact captured request/client turn ID.
- Preserve current-context fences: a response for another World/document or malformed origin cannot refresh or mutate the selected subscriber.
- Run the focused mounted Plan conversation/history suite, `git diff --check`, and inspect the exact cumulative base-to-head diff. Record any inherited failures without broadening this lease.

## Candidate verification

- Focused mounted history suite: 21/21 passed, including late success after unmount/remount, exact canonical-history refresh, canonical conversation UUID distinct from client `turn_id`, replacement-byte preservation, malformed/network failure preservation and exact explicit retry.
- `git diff --check` against the pinned base passes.
- UI typecheck is blocked by the inherited main error `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`; that file is unchanged from the pinned base.
- The current candidate head is published through PR #919 and has not yet received PRIME review. Do not claim runtime or visual acceptance for this slice.
- The byte comparison is synchronous in this document, but localStorage has no transactional compare-delete operation across browsing contexts. This protects a replacement already present when settlement starts; cross-tab concurrent writes to the same key are outside this slice. Pending keys are per submitted turn and explicit retry reuses the same envelope. Do not describe this as a cross-tab atomic CAS guarantee.

## Publication checkpoint

- Published as [PR #919](https://github.com/Drakosfire/DungeonMindBuddy/pull/919), based on the pinned main SHA above. The PR opened at `70c312988880579b4aae415095f7f740e608043a`; that head contains the source, mounted regressions, and this verification record across only the three leased paths.
- PRIME's exact-head review and merge coordination remain pending. Do not merge from this handoff.

## PR and settlement

One implementation PR for this capability, from this pinned base. DEMO implements, verifies, inspects the cumulative diff, commits and pushes the branch, and opens/updates that PR. PRIME independently reviews the exact head and owns merge coordination. Do not claim this slice complete until that review and its required gates settle; record actual head, evidence and lease release here after merge.

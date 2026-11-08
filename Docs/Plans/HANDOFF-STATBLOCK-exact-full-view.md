# STATBLOCK — exact saved full view

ACTIVE. PRIME owns one serial slice after delivered2229. Base
cec51360c7b84d9bf4d43c2e17173daf936eb9d5; codex/statblock-exact-full-view;
reuse buddy-context-loop checkout/dependencies. Live API57cf/UIafac6db0 immutable;
no implementation runtime lease. No overlap with held2172/2223/2225 or backend
ADVERSARY work.

## Outcome and invariant

A popup's currently opened saved revision links to /statblock with explicit managed
World, owning draft and revision. Full view uses existing openSavedMechanicsVersion
and StatblockRenderer, directly reading the exact target; no history/default/local
selection lookup, new store, generation/Save/adoption or alternate authority.
The full view is read-only. Popup remains the sole edit/recovery instance. Local
edits are never presented as saved mechanics or copied into this full view.

Missing/ambiguous targets, World mismatch, failed reads and mismatching response
identities show an honest failure without newer/default substitution. Late replies
for previous targets cannot show. Retry uses the same explicit target. Same-World
statblock navigation must honor draft/revision query changes; other existing
primary-navigation semantics remain unchanged.

The new route is shared entry-point plumbing, not a Build-specific viewer. It has
normal selected-World AppChrome, no new nav tab and no invented agent work context.

## Exclusive writes and review map

1. Saved projection/link: src/statblocks/savedStatblockLocation.ts and test,
   StatblockPage.tsx/CSS/test; src/statblocks/revision/SavedMechanicsRevisionEditor.tsx
   and test (link only). All paths relative to apps/live-control-ui/.
2. Shared read boundary: src/api/liveApi.ts and liveApi.savedMechanicsVersion.test.ts
   centralize response scope/identity checks formerly embedded in the editor.
   The editor retains its separate history-original check.
3. App integration: src/App.tsx, src/chrome/appNavigation.ts,
   src/chrome/appChromeConfig.ts, src/test/appNavigation.test.tsx.
4. Existing hosted UI cohort registers affected tests; this handoff and truthful
   predecessor HANDOFF-CONVERSATION-native-qualifications.md settlement.

Review burden belongs together: exact link, route admission, native read and render
are one usable capability; splitting would leave a dead link or unreachable reader.
No backend/schema/dependency/generated-contract paths.

## Verification and remaining scope

Owning tests cover exact read/no history/no writes, incorrect identities, failure/
retry, stale reads, ambiguous links, World admission, primary route/pin navigation,
and existing editor source-version links. TypeScript/build and controlled browser
prove popup→exact full route→reload and narrow layout using retained saved mechanics,
without providers/content writes. Inspect cumulative diff, independent Bugbot
review, push/open one PR, CI, merge and protected UI-only delivery.

The legacy artifact-backed StatblockViewModule is not a fallback for native saved
mechanics and is not adopted here. Its separate caller/storage audit remains in
the final adoption/demolition inventory. Shared editing across node/conversation
hosts, media generation/selection/native asset binding, native threat association
and real Corrupted Edge ooze creation remain subsequent slices. Held Play2172 is
not resumed. Dogfooding/operator acceptance remain excluded.

## Candidate evidence

Private runtime-evidence/q01-published-graph-authority: statblock-full-view-tests-v3
proves49 owner/client/renderer/editor/dialog cases; navigation-tests proves the
focused exact-pin navigation case; build-v3 TypeScript/Vite passes with existing
chunk-size warning. Shared API reader owns envelope checks; editor retains its
separate original-history relationship check. Earlier mocked component identity
case failed after moving that check; the transport suite now exercises actual
wrong-response admission and component rejection tests mock that typed failure.

Browser-v4 uses candidate assets and actual retained Sheep saved mechanics. Popup
link reads exactly one explicit native revision in full view, no history/default
lookup or editing copy; reload keeps revision,390px layout fits, and back/reopen
recovers the dirty popup draft. No providers/content writes, errors or blocked
requests; auth revoked. Browser-v1/v2 incorrectly expected a ProseMirror editor on
the source-less Build landing page after Back; that harness assumption is fixed,
not a product change. Original failed observations remain retained.

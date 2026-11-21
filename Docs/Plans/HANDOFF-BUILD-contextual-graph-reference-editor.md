# Mount the typed Graph reference Review in the Build editor

Status: ACTIVE under the contextual-layout lane. Serial base
`74b0072f6fcc2decf84f789ce6654fb419d774f1` after #4360, in the isolated
`codex/build-contextual-graph-reference-editor` checkout.

The receiver presents the exact Graph label and classification. It prepares a
single typed atom at the frozen paragraph boundary, waits for an explicit
author action, invokes the existing Build Content Save, and acknowledges only
the committed postimage. Retry uses the recorded apply identity or refuses on a
changed page. Existing local history, plain and identity-only sidecar behavior
remain under their respective owners.

The allowlist comprises this handoff, `apps/live-control-ui/src/api/buildGraphReferenceReviewApi.ts`,
`apps/live-control-ui/src/buildSurface/BuildGraphReferenceReview.tsx` and its
test, and the typed atom branch and its coverage in `buildComposeBridge.ts`
and `buildComposeBridge.test.ts`. #3867 at
`a2c5d9115bf1347f2cd84a2808d3dec29ddc3242` retains its distinct prose concerns.
Reuse existing Save forwarding and page ownership. Ordinary Build Send is a
serial dispatch successor after the receiver is verified. Its route remains
off until then. No profile, migration, provider or deployment change belongs
to this editor slice.

The mounted editor emits `#dmb-ref:graph-node:` for a typed reference. The
integration admits that canonical href in
`src/application_state/build_proposal/graph_reference.py` and its tests in
`tests/application_state/test_build_proposal_postgres.py`. The original HTTP
receiver can still replay and confirm the exact legacy `dmb-node:` postimage
through its existing API. A receipt may never change href, digests or Apply
ID within that replay. The mounted card can confirm already saved legacy
receipts. The earlier slice had no mounted authoring client for uncommitted
legacy preparations.

Verify real mounted editor geometry, typed atom round trip, inert Review,
stale and foreign refusal, explicit Save, lost acknowledgement, Undo/Redo,
untouched siblings, and cold 390px reopen. Use the authenticated #4360 route
and actual disposable Content owner. Exact frontend hosted, default-discovered
comparison, and independent exact-head review gate merge.

## Completed predecessor

#4360 merged at `74b0072f6fcc2decf84f789ce6654fb419d774f1`, exact reviewed
head `b4b45dffea6543dc96bf0671fe4e4378a3cebae4`. It passed 39 focused checks
and 1,465 hosted frontend checks with build. Exact query and saved-page
failures matched their baselines. A disposable database proved the reader
fence, old APP read refusal and refused downgrade. The HTTP receiver verified
plain and identity-only Content against scripted Graph identity rows. Graph
preflight and Content Save use distinct storage owners.

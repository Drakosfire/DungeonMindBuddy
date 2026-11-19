# CLEANUP: consistent authored-Page rejection from Plan

Status: SETTLED by #4096, merge6fee61800b98f6cc7ac49e00021a18f9a8db5cbc.
Exact reviewed headb42201ee12c3b0d2a62c5e7efc09a6c470a75bea approved independently.
Focused30pass, all26descriptor cases pass; hosted1411/build/validator pass.
Full8045pass132fail2pending: only intended failure resolves, no omissions/new
failures/changed remaining leading messages. Full qualification remains red.

Historical assignment: Standing cleanup goal authorizes implementation, independent
review and merge. Base a0765314d86827a553924c2b933c5b16938dd1eb.
Serial after #4095, no unmerged dependency. Existing isolated cleanup checkout;
no ports, databases, providers or operator data.

## Invariant and scope

Exact Plan document selection must reject authored Pages before any campaign
fallback or list read. #1993 added an early generic error while the existing
descriptor conversion already rejects the same kind with
UnsupportedPlanningDocumentKindError. Preserve early rejection and use that
existing typed error consistently, not a weaker test or expanded admission.
Exercise same- and cross-campaign Page records; preserve exact retrieval and no
list fallback. Plan/Runbook and cross-campaign admission behavior stays unchanged. These legacy
registry fixtures do not prove managed-World ownership or authorization.

Lease: planSurface/config/planSessionDescriptor.ts and its existing test under
apps/live-control-ui/src; this brief; prior session-evidence-viewer-fixture brief
for truthful #4095 settlement. No API, content owner, schema, registry or other
Plan component edits. All 61 open PR heads were inspected: no changes to these
source/test paths. Historical gateway #660 is merged (a3fd6219062d1cd978c394d07e2f80aaa6d203eb),
not a current lease. Re-anchor if scope or owners change.

## Verification

Compare focused descriptor admission baseline/current under the global frontend
lock using external task-owned source. Prove authored Page rejection is typed for
both campaign scopes before fallback; all existing Plan/Runbook cases must pass. Run the
exact-head repo hosted verifier/build/validator and full discovered diagnostic.
Compare exact test IDs with 3f718fab4efd40da82d713309fb3d2b25f37f35d: only the
intended failure may resolve, no omissions/new failures/changed remaining leading
messages. Keep inherited failures, conditional inventory differences and earlier
unresolved quote variant red under #4074. Independent exact-head cumulative
source and raw-evidence review precedes merge; no backend/release acceptance.

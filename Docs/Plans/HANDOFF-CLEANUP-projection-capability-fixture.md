# CLEANUP: explicit projection-capability regression fixture

Status: SETTLED by #4098, mergeca3101a35dbb54d7edc5b58f764365ee7729c691.
Exacthead190971af136d9a1e003388e570cfc6186e0f065d independently approved.
Focused76pass; hosted1411/build/validator pass; full8046pass131fail2pending.
One explicit old/new case pair, only intended failure resolved; no other
omissions/new failures/changed leading messages. Full qualification remains red.

Historical assignment: ACTIVE under the cleanup goal, with independent review and merge authority.
Base 6fee61800b98f6cc7ac49e00021a18f9a8db5cbc; serial after #4096,
no unmerged dependency. Reuse isolated checkout; no ports/providers/databases.

## Scope and invariant

projectionContext.test.tsx still expects implicit Plan graph-reference authority.
Current provider requires an effective publication declaring graph-reference
content plus a registered live binding. Existing projectionBindings tests already
use that native declaration; do not restore retired inference or weaken gates.
Replace the old case with explicit declaration/binding/open/revocation coverage,
using the real provider and useProjection hook. Assert no content before either
gate, exact resolution on authorized open, and clearing on binding retirement.
Pair the old/new test ID explicitly; preserve all unrelated cases.

Write lease: apps/live-control-ui/src/planSurface/projection/projectionContext.test.tsx;
this brief; HANDOFF-CLEANUP-plan-page-admission-error.md for truthful predecessor
settlement. No provider, shared host, runtime, manifest or schema changes. All61
open head diffs checked: no target test, test host or provider overlap. Current
provider/source contract and retirement history govern, not obsolete Plan fixture.

## Verification

Run focused baseline/current projection context, binding and publication gates
under the global frontend lock in external task-owned source. Preserve strict
negative assertions and revocation; no mock provider. Exact-head hosted verifier,
build, validator and full discovered diagnostic required. Compare with final
b42201ee12c3b0d2a62c5e7efc09a6c470a75bea baseline (verify parent byte identity):
explicit one old/new test-ID pair, only intended failure resolves, no other
omissions/new failures/changed remaining leading messages. Keep132 inherited
failures, conditional inventory differences and earlier quote variant visible;
this does not establish backend/Graph delivery or release qualification.
Independent exact-head source/raw-evidence review before merge.

Historical Combat prototype product navigation also differs from current chrome,
but its frozen assets are referenced by local delivery evidence and lab callers.
They are outside this lease; do not rewrite/delete them to pass a parity test.

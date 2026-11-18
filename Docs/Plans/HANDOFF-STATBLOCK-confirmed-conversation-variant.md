# Confirmed conversation statblock variants

ACTIVE under the Meat Mind workflow goal. Base e5e139501 on codex/aw-confirmed-variant.
Serial slice for Buddy application state, the agent route and statblock validation
and create integration, the conversation draft control and their owner tests.
Use the existing isolated AW database. Keep primary data unchanged.

Bind explicitly reviewed mechanics to the exact conversation draft revision.
Store the request before dispatch. Exact replay must recover the same variant.
A different request or a stale unclaimed revision must fail without creating.
Verify principal scope, edit/save races, interrupted creation, replay and exact
readback. Edge linking and Combat admission consume the resulting receipt.

## Review binding

The chat editor currently persists Markdown only. A client-supplied definition
and matching digest prove self-consistency, not that the definition was shown
with this draft. Keep the create operation internal until Buddy owns a review
record that captures the exact draft revision, structured mechanics and base
source locator. The operator confirms that review record. Resolve its definition
server-side and reject stale unclaimed revisions under the existing draft lock.
Do not accept arbitrary mechanics alongside a confirmation.

## Ordinary writer contract

The shared Build path dispatches through PlanWriterCall and completes through
the Rules runtime's native output proof, which verifies exact provider bytes.
The write set also includes the selected Build response view, its native output
schema and normalization, PlanWriterCall, the Rules completion adapter and
their contract tests. Only the selected conversation draft with an admitted
exact statblock base may offer a variant; standard discussion and ordinary
Markdown drafts retain their existing schema. The provider sees local source
aliases. The host resolves them against the admitted read and retains full
mechanics and source identity in the review. Carry the typed result through
exact output verification and save the review in the fenced draft transaction.

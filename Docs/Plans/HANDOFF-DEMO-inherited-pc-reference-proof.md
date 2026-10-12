# HANDOFF — DEMO: inherited PC reference review proof

**Status:** SETTLED — Buddy [PR #1086](https://github.com/Drakosfire/DungeonMindBuddy/pull/1086) merged at `e9243dadf33d0a3c34a6c0ad11c4759cdb37940b` from reviewed head `e397a2a877f47169461076e5dc111ddbbdb707db` on 2026-10-12. The exclusive write lease below is closed.
**Owner:** DEMO
**Authority base:** `Drakosfire/DungeonMindBuddy` `origin/main@736098ac6e1ed0133a57540669d7719d23447808` (merged V9 PR #1084)
**Branch:** `codex/demo-inherited-pc-reference-review`
**PR topology:** parallel-independent from RAKE's legacy source-read eligibility/mapping and the currently open UI, rollout, and Rules PRs; no shared runtime state. The open PR path sets were checked at activation. If RAKE claims an exact function below, coordinate before editing it.
**Assigned PR:** `DEMO: review inherited PC reference proof`

## Invariant and authority

A later V7/V8 recap correction may preserve a PC `corpus_ref` introduced by a V9 child. Each surviving reference must remain visibly tied to its introducing V9 run and manifest, exact attachment tuple, frozen source quote/span/index, origin World and native `pc:<slug>` target. Walk only that immutable lineage segment. Verify parent and manifest digests, source/index identity, continuous unchanged attachment tuples, and absence of cycles or forged introductions. An omitted reference has no surviving overlay. A changed or unproved inherited reference remains held before publication.

The final review package returns typed inherited-reference rows, their canonical digest, final candidate SHA, run revision and computed semantic basis SHA together. An authenticated reviewer uses that exact API package and the existing candidate-SHA/revision semantic decision. A conditional `inherited_pc_proof_sha256` joins the existing V7/V8 basis only when inherited resolved PC references survive; legacy no-reference basis serialization and hashes stay byte-identical. The server and APP-STATE independently rederive/check the proof against immutable lineage. Missing proof on a legacy held descendant with inherited refs fails closed. The accepted basis/effect binding is rechecked at decision, prepare and confirm.

This is an API-level review workflow. The Buddy UI has no semantic-disposition consumer/action for this package and is not certified by this slice. `review_decision_ref` records an authenticated decision; it does not prove that a human opened the JSON. Do not add a decision request field, route or new review engine. If proof fields can change without changing candidate/revision/basis, return to ARCHITECTURE before widening the contract.

Current unique active native PC targets are rechecked at prepare/confirm in the publication World. Do not require intermediate parents' unrelated semantic assertions to be accepted, and do not reapprove mutable historical registry or head state. No live child, semantic acceptance, APP/native/corpus data, provider or runtime mutation belongs to this lease.

## Exclusive expected paths

- `Docs/Plans/HANDOFF-DEMO-inherited-pc-reference-proof.md`
- `apps/live_control_server/models/extract_promote.py`
- `apps/live_control_server/services/extract_promote.py`
- `apps/live_control_server/services/recap_semantic_candidate_correction.py`
- `apps/live_control_server/services/recap_semantic_disposition.py`
- `src/application_state/ingest/service.py`
- `tests/test_recap_semantic_candidate_correction.py`
- `tests/test_recap_semantic_disposition.py`

No port, service, database, external state or artifact output directory is leased. The exact-run package route keeps its existing path and decision route; its Python response projection/model may gain additive fields. RAKE owns source-read eligibility and mapping, so a collision there is a stop-and-coordinate signal.

## Verification and exit

Use invented synthetic fixtures. Prove a V9→V7→V8 chain with held intermediates, final review rows/digest/basis correspondence and accepted final decision. Refuse changed ref/tuple/quote/manifest, missing or forged introduction, wrong source/index/World, cycle and stale/current native target before publication. Prove old V7/V8 no-reference basis bytes/digests unchanged and a legacy held descendant with inherited refs cannot pass absent proof. Review the cumulative diff, run owning tests, commit, push and open the assigned PR. Return its exact head and limits to PRIME for independent review and merge control.

## Settlement

ARCHITECTURE's exact-head Cycle 2 review passed on `e397a2a8` (formal review `5487118787`). The focused correction/disposition suites passed 158 tests; the test-only final commit exercised the accepted V8 descendant through the real decision service and APP-STATE CAS function over synthetic rows while V9/V7 parents stayed held. A synthetic prepare carried the accepted effect binding, and the confirm-time semantic gate rejected current native-target drift and representative frozen-lineage attacks. No real World writer, live source, provider, runtime, database migration, Session 28 publication, UI semantic-decision action, or proof that a human opened the JSON was claimed. PRIME merged the exact reviewed head; this handoff grants no remaining implementation lease.

# Deliver a duplicated inline clarification

Status: ACTIVE. The user authorized this chat to restore clarifying questions
and establish its own app lane. Serial, independently reviewable runtime slice
based on `814ace002a59b4d6417906b5a0bdb1aa8c2cb855`, branch
`codex/clarification-app-lane`, checkout at
`/home/drakosfire/Projects/.codex/clarification-app-lane/DungeonMindBuddy`.
No merge or deployment authority is implied. There is no start prerequisite.

## Outcome and boundary

An ordinary synthetic Build turn produced a valid typed question and repeated
it verbatim as a discussion segment. Completion rejected the whole reply with
`Question duplicated outside its inline object`. Preserve the question and
remove only exact duplicate plain discussion segments during native completion
normalization. Keep other prose, evidence-bearing claims, malformed responses,
capability and output checks, and exact provider-output provenance intact.
Normalization must replay deterministically from the captured response. No
question alone authorizes a proposal or page mutation.

Failure cases include duplicate text in evidence-bearing segments, nonexact
text, missing or wrong-kind collaboration, altered captured output, and empty
responses. Do not use model-output repair to admit invalid collaboration or
change any source claim. The existing typed object remains the sole question
owner. UI reopen behavior and source routing are separate work.

## Expected write lease and verification

`src/application_state/agent_conversation/native_completion.py`, focused native
collaboration/ordinary-turn tests, this handoff, and the clarification entry in
`evals/plan-authoring-benchmark.md` for evidence status. Add a bounded
conversation-first benchmark regression only if its fixture can express this
completion behavior without changing another lane's evaluator contract.
No shared routing, schema, migration, frontend, model, deployment, or provider
configuration edits. Open PRs #4642 (routing), #4584 (benchmark), and #3867
(placement) were checked for these implementation paths.

Prove exact captured output and replay at the native completion boundary,
including the controls above, then exercise ordinary synthetic Build delivery
and answer continuation with the existing inline component. Retain the live
result and its limitations. Run affected locked backend contracts and required
exact-source local verification before review; report missing evidence rather
than equating component tests with workflow or deployed proof. Update the
action catalog with only evidence actually obtained.

The isolated app uses ports 38951/38952 and disposable App and Core databases
on 33393/33394. Its runtime ledger is in the lane's `runtime/LANE.md`; it does
not share operator World data. Vite owns the global frontend verification lock
while running and must stop before the frontend verifier.

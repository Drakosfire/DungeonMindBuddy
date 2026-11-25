# Deliver a duplicated inline clarification

Status: SOURCE MERGED. Source03d803fd6819edfbc52d0c062db95ae35f187a99 was
independently reviewed and merged as aad8c32b6ac3f64dab0b085106e6ba086c979419
(PR4652). Exact-source52focused native-collaboration checks passed3.68s under
Alan's current minimum-focused-verification policy; historical broad diagnostics
below are retained, not green. Serving adoption and actual app acceptance remain
in HANDOFF-DOGFOOD-inline-question-serving.md. Historical assignment follows.

Original status: ACTIVE. The user authorized this chat to restore clarifying questions
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

The routing owner explicitly split the overlapping native-completion lease at
`be54f7b2471f18bf19d7dd2dba68f6424ba562f3`: this slice owns the existing
duplicate-question normalization and question-only helpers; routing retains
only its new pending/source-free dispatch and codec helpers. The split requires
independent retained-reader and replay verification and does not grant merge or
deployment authority.

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

## Local working-tree evidence

The synthetic native completion test reproduced the captured provider answer's
`ValueError: Question duplicated outside its inline object`. With this change,
78 focused native-collaboration and related-page tests pass, including exact
replay, preservation of nonidentical discussion and a related-source claim,
and rejection of an identical evidence-bearing claim. These are working-tree
diagnostics, not exact-commit qualification.

Subsequent review found the first implementation could accept 129 duplicated
raw discussion rows after reducing them to zero, bypassing the completion's
128-segment bound. The repair now checks that limit before filtering. The
expanded focused diagnostic passed 79 tests and scoped Ruff; evidence recorded
against the earlier commit does not qualify the revised head.

In the task-owned app, retrying the original fabricated lamp request produced
an editable inline question. Its answer was added to a message and submitted;
the next turn generated a visible incomplete page suggestion, then failed at
writer dispatch. The saved page was unchanged after a browser reload. On that
reload, the successful clarification displayed only `Open Details to inspect
this reply`, while the submitted answer remained in the transcript. Thus the
continuation and cold-reopen goals are **not** established by this slice.

A broader working-tree diagnostic (native collaboration, intentional response,
and mixed Rules) reported 141 passing, two `SimpleNamespace` fixture failures
and seven missing owned App database fixture errors. It did not use the required
retained CI App owner and is not qualifying evidence; those failures have not
been established as inherited. No deployed or full benchmark claim is made.

# RETRIEVAL: preserve pinned history in negative capture

Status: ACTIVE under the user's negative-retrieval goal. Serial, evaluator-only
fix on `codex/negative-pinned-history-compat`, based on main
`3714dd269124be1d7e82776451700292b445039d`. The existing serving reader and
Plan producer are separate lanes; no open negative-evaluator PR was found.

Write lease: this brief, `evals/negative_retrieval/capture.py`, its README and
focused cases in `tests/evals/test_negative_retrieval_assessment.py`. No model,
database, migration or production state changes.

The negative adapter must validate its frozen fixture before and at the ordinary
runner's history read. When the ordinary runner receives its own pinned history,
the adapter must not also supply `expected_conversation_id`; both mechanisms
must agree on the active conversation and independently reject stale or changed
history before dispatch. Preserve legacy seeded captures without a history pin.
Verify the adapter and real ordinary capture boundary with synthetic responses,
including mismatch and mutation between the reads. Review the cumulative diff
against the pinned base before merge.

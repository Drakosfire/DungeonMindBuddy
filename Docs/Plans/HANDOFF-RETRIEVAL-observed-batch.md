# RETRIEVAL: observe nonempty Core batch reads

Status: ACTIVE. The user owns and authorized the over-retrieval goal and this
lane. Serial successor to merged #4864 (`622082a391beeb2c2cbb093a5dee4d2736349fa4`),
based on fetched main `670389d29ba170936cc59bd4a984dc86ea8017c9`. Branch
`codex/retrieval-batch-observation`, isolated checkout
`/home/drakosfire/Projects/.codex/retrieval-batch-observation/DungeonMindBuddy`.

Outcome: recognize a scoped execution of the pinned Core batch owner's
nonempty read path as one provisional unmapped read attempt in a bound,
successful POST window. Empty, malformed, unknown-owner, unscoped, late,
failed-dispatch and incomplete captures must not create that attribution. The
attempt cannot count as a returned body or satisfy required evidence. Older
artifacts remain readable and diagnostic, and missing observations cannot prove
absence. Do not inspect or retain arguments, source identifiers or body text.

The pinned owner's nonempty path has a stable transaction-entry line. Bind the
actual registered code, source and locked interpreter to a versioned host-only
provenance record; unknown changes stay unscored. Keep callbacks observational,
clean up all monitor hooks even on failure, and poison the process if cleanup
cannot be proven. This is partial observation, not journal completeness.

Write lease: `evals/negative_retrieval/source_window.py`, `capture.py`,
`report.py`, `README.md`, `tests/evals/test_negative_retrieval_assessment.py`,
this handoff and `Docs/Plans/HANDOFF-RETRIEVAL-observed-read.md` for predecessor
settlement. No runtime, provider, schema, database owner, shared runner or CI
changes. Existing Plan lanes #4580 and #4550 and Build serving #4823 own other
paths. The existing App clone stays owned by its supervisor; no allocation.

Verify the actual Core owner at the capture/report boundary: empty and
nonempty inputs, a read that raises, same-window correlation, unknown or changed
code, old artifacts, late/unscoped work, monitor cleanup, and a source-required
control. Use only focused local cases, exact cumulative diff and independent
exact-head review. This does not qualify the wider goal: ordinary-turn native
positive control, complete acquisition coverage, held-out cases and deployed
product qualification remain open.

# RETRIEVAL: observe admitted PDF loader attempts

Status: ACTIVE. The user authorized continuing the negative-retrieval goal.
Serial eval-only slice based on main `e4b6f68a362a2c5ccba49a783f28edb42f8ca812`,
branch `codex/negative-pdf-observation`, in the attached managed checkout.
The prior development regression #4924 is merged. Open retrieval and PDF PRs
were checked; no overlapping negative-evaluator lease was found.

The current probe misses PDF regions opened through a pre-bound Graph alias.
Observe entry to the supplied PDF loader from the Graph alias and module opener,
without recording inputs or bodies. A locator rejected before the loader is not
an acquisition attempt. Entered, returned and raised loader calls are unmapped
attempts, never completed source proof; old artifacts, unknown aliases, workers
and late calls remain unknown. Zero observations cannot prove a complete journal.

Write scope: this brief, `evals/negative_retrieval/native_graph_probe.py`,
`report.py`, `README.md`, and focused cases in
`tests/evals/test_negative_retrieval_assessment.py`. Verify the real admitted
opener boundary with a synthetic loader, pre-load rejection, success, failure,
alias restoration, payload exclusion, and report handling. No database, model
provider, production state, or additional clone is used for these checks.
Independent exact-head review and applicable merge checks are required.

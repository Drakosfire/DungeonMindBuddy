# Common ingestion assessment records

Run `python scripts/evaluate_ingestion.py assessment-report --manifest /path/assessment.json`.
This is offline and does not initialize providers or databases. It verifies bytes,
run/candidate binding, Gold criterion IDs, review references and declared coverage.
It reports counts by dimension and phase, without blending phases or imputing cost.

The `dmb_ingestion_assessment_v1` record contains:

- `subject`: `result` is an artifact/JSON Pointer reference to the actual run
  object; `candidate` is its exact candidate component path/SHA256 pin.
- `gold`: path/SHA256 pins for the effective source-reviewed Gold artifacts.
- `criteria`: one entry per criterion: `criterion_id`, `dimension`, `gold` reference
  to its identified Gold object. Do not copy or rewrite the expected claim.
- `phases`: all three of `raw_extraction`, `reviewed_output`, `publication`.
  An unassessed phase is `{"status":"unknown","reason":"Specific missing evidence"}`.
  An assessed phase has `phase_evidence` (artifact pins) and `judgments`.
- Each judgment has `criterion_id`, `outcome` (`pass`, `fail`, `partial`, `unknown`),
  `review` (reference to the original criterion judgment), `evidence` (references
  to inspectable values), and `reason`. All declared criteria must appear exactly
  once; uncertainty is an explicit judgment, not omission. The review document
  must identify the actual `run_id` or `assessment_run_id`.
  It must also pin the exact `candidate_sha256` (or `pins.candidate_graph`)
  and `revision`/`run_revision` (or `pins.result` for the exact result bytes).
  Explicit conflicting bindings are refused. A legacy review without these needs
  an independently reviewed, exactly bound adoption retaining its original refs.
- `measurements`: `elapsed_ms`, `billed_cost_usd`, `review_effort_minutes`, each
  either a reference to a retained numeric measurement or an explicit unknown.
  Zero is accepted only when actually present in the referenced measurement.

A reference is `{"artifact":{"path":"/absolute/evidence.json","sha256":"..."},"pointer":"/checks/0"}`.
Use an empty pointer to reference the whole document. Selectors are strict JSON
Pointers; legacy selectors must be resolved explicitly, never evaluated as code.
Legacy scalar Gold constraints may use stable assessment-local IDs and their
unchanged literal Gold pointer; independent review validates that mapping. Duplicate
references to the same Gold object are refused to prevent denominator inflation.

Normalize completed legacy reviews once into this format. Preserve their original
bytes and judgment pointer; there are no runtime adapters or per-session scoring
scripts. A normalized outcome is an explicit reviewer judgment, never inferred
from a substring such as "supported", or from preparation/feasibility. Independent
review must verify the mapping, full effective Gold criterion inventory and phase
evidence. The tool cannot certify semantic completeness from a declared subset.

Gold recall and unsupported-claim precision have different denominators. A recall
pass does not erase unsupported extras; retain those findings in the source review
and report them separately. This slice does not manufacture a precision score from
Gold recall. Candidate source-excerpt copies do not earn model-authored recall.
Publication requires actual confirmation/readback evidence and independent review,
not a dry run, source-support receipt, or an assessed `publication` label alone.

Use the existing capture audit/accounting owner for token/cost/retry evidence. Do
not introduce another usage calculation here. Model/configuration comparisons and
cohort aggregate/variation reports remain separate from criterion normalization.

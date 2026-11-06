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
  An assessed phase has `phase_evidence` (artifact pins), `judgments` and explicit
  `limitations` (text list, empty only when no limitation is known). Reports retain
  those links and limits beside counts so coverage cannot hide precision holds.
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
Legacy Gold constraints without intrinsic IDs may use stable assessment-local IDs and their
unchanged literal Gold pointer; independent review validates that mapping. Duplicate
references to the same Gold object are refused to prevent denominator inflation.
Identified objects (including `id` on interpretive items) must match the declared
criterion ID. Unidentified structured constraints are retained unchanged, like
scalar constraints; no new Gold representation is created to add synthetic IDs.

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
## Assemble a sealed review offline

Use the same CLI rather than a per-session assembly script:

```bash
python scripts/evaluate_ingestion.py assessment-assemble \
  --manifest trusted-assessment.json \
  --result records/session.result.json --review review-document.json \
  --audit records/audit.json --timing records/session.timing.json \
  --assessment-output assembled-assessment
```

`--manifest` supplies only the existing common format's pinned Gold and criterion
inventory. Previous outcomes, subjects, reviewed-output and publication scores
are not copied. `--review` uses the current `judgments` shape with explicit
criterion IDs, outcomes, reasons, evidence and run/revision/candidate binding.
Extra annotations remain in that sealed review; canonical rows contain only the
standard five fields. There is no legacy field-name remapper or semantic grader.

The command verifies the result's candidate pin, binds supplied audit billing to
the same run/candidate and timing to the exact result bytes, then reuses
`assessment-report` validation before retaining `assessment.json` and
`assessment-report.json`. Audit and timing are optional; missing or unreported
measurements remain unknown. Automated reviewer time is never human minutes.
Reviewed output and publication remain explicitly unknown.

This command initializes no provider or database backend and can assess retained
results from a pinned earlier evaluator without executing its manifest. Existing
outputs are never overwritten: an identical invocation is safe to repeat after
an interrupted report write; a conflicting artifact fails before output writes.
It does not authorize publication or establish whole-output semantic quality.

## Blinded semantic inputs

Prepare future reviewer inputs with the existing offline evaluator:

```bash
PYTHONPATH=src python scripts/evaluate_ingestion.py review-packet \
  --result /absolute/retained/result.json \
  --packet-output /absolute/neutral-public-directory \
  --private-receipt /absolute/private/projection-receipt.json \
  --review-id opaque01
```

Give the reviewer only the public packet, separately pinned source/Gold/criteria
and neutral owner contracts. The candidate bytes and every recorded response text
are preserved; repeated or malformed response texts are not dropped. Operational
request/telemetry envelopes are excluded. Unexpected candidate telemetry or shape
fails preparation rather than silently redacting authored content. Exact response
text identity does not imply identity of the newly serialized JSON wrapper.

Use `binding.json` for the existing sealed-review run/revision/candidate fields.
Cite public artifacts with ordinary pinned JSON Pointers. After sealing, the
existing `assessment-assemble` command consumes the original result and unchanged
sealed review. Preserve the private receipt linking public pointers to original
records. Never give it, the original operational envelopes or the experiment
schedule to the semantic reviewer. Source/Gold references are not rewritten here.

Response count, length and authored self-disclosure remain visible. A file
projection is not a security sandbox or proof of perfect blinding. Host source
wrappers/excerpts and normalized fields require neutral provenance contracts and
earn no model-knowledge credit. Allocation experiments still require independent
qualification and calibration before calls; this command grants no execution
or semantic-assessment authority. Historical review records remain unchanged.

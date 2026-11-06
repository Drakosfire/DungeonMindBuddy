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

Each response wrapper carries an origin tag derived from the owning receipt,
not its text shape: `provider_response`, `host_materialization`, or `unclassified`.
Host-normalized wrappers are retained for provenance but are not additional
provider attempts or model claims. Unclassified records require investigation;
never infer authorship merely from a `parsed` or `source_units` key in the text.

When the original private capture contains its compact source dictionary,
`review-packet` also emits `evidence-context.json`. This is the exact captured
context object: request-local `E` handles, canonical source-span IDs, paragraph
text, text hashes and line bounds. Cite its entries through ordinary JSON
pointers. It is host-supplied input evidence, not model-authored knowledge or
independent proof that a claim follows from its cited paragraph.

The projection validates the captured envelope hash and run/source binding,
source-index identity, entry text hashes, unique sequential handles and source
span line bounds before writing any packet. Only the closed context object is
public; model/provider settings, execution binding and other telemetry stay in
the private receipt/source records. The receipt maps the public dictionary to
its original captured JSON pointer and envelope hash. It never rebuilds aliases
from a candidate or falls back to diagnostics.

Historical captures without that envelope report the dictionary as unavailable
in `scope.json`; no dictionary is invented. Use a new output directory when
qualifying the expanded packet. Existing packets and sealed reviews remain
unchanged, and supplying this additional evidence does not automatically regrade
their findings or turn an unknown outcome into a pass.

## Paired comparison diagnostics

Use `assessment-compare --manifest /absolute/comparison.json` to consume pinned
canonical assessments through the existing validator. Declare cases and exact
replication from the experiment design before selecting outputs:

```json
{
  "schema": "dmb_ingestion_paired_comparison_v1",
  "expected_cases": ["case-A"],
  "pairs_per_case": 1,
  "pairs": [{
    "case_id": "case-A", "pair_id": "replicate-1",
    "control": {"path": "/absolute/control.assessment.json", "sha256": "..."},
    "variant": {"path": "/absolute/variant.assessment.json", "sha256": "..."}
  }]
}
```

The command reports every pair, per-case count deltas, conservative intervals
for unknown criterion outcomes, and measurement-ratio variation. It refuses
missing cases/pairs, reused runs, mixed Gold/criterion contracts and invalid pins.
A missing measurement or zero control denominator makes that case's corresponding
median unknown; it never computes a favorable available-case median. Cases are
never pooled. The example has one pair; use the design's actual replicate count.

Count non-regression is a diagnostic (median pass delta >= 0 and fail delta <= 0),
not an adoption decision. Matching Gold/criteria does not prove identical review
semantics. Separately pin and verify the common review protocol, precision,
severe-claim veto, uncertainty, reliability and experiment acceptance rules.
Original reviews, phase limitations and measurement evidence remain linked.
The command has no provider/database backend and does not change study captures.

## Retained normalization comparison

Use `normalization-compare --manifest /absolute/normalization.json` when a
normalizer changes but actual model responses should remain fixed. This command
extends the same evaluator; it does not create another ingestion producer.

The manifest uses schema `dmb_retained_normalization_v1` and contains:

- `tooling_sha256`: the existing evaluator's `tooling_identity()`.
- `interpreter`: an absolute Python executable path and its SHA-256.
- `environment`: a pinned JSON receipt containing `files` (absolute content
  pins), `import_roots` (absolute real dependency directories), and `scope`
  describing what dependency reproducibility is and is not attested.
- `runtimes`: exactly `control` and `treatment`, each pinning a JSON manifest
  with an absolute `root` and `files` entries containing relative `path` and
  `sha256`. Pin the complete composed runtime, including any required donor
  changes; a Git head alone cannot attest a composed runtime.
- `cases`: unique generic `id` values and pins named `result`, `source`,
  `request`, and `assessment`. Use the original canonical assessment, not a
  newly rescored version. Each actual run can occur only once.
- `output`: a new absolute evidence directory outside runtime, dependency and
  input locations.
- `worker_timeout_seconds`: 1–60 seconds for each offline worker, independent
  of provider accounting or attempt policy.

Workers follow explicit accepted response-component links and verify binding,
outcome, model, request hashes and response bytes. They execute the pinned
owner's parser, schema validation and source-packet materialization using the
retained character context. The adapter currently supports the ordinary
source-only category profile, without encounter or advisory passes. It refuses
missing configured passes rather than accepting fixture defaults.

The control must reconstruct the entire original decoded candidate exactly
before the treatment worker starts. No fields are excluded or repaired. Reports
retain both candidates, request hashes, worker diagnostics and changed root
fields. Actual raw scores and costs remain linked to their original records;
synthetic fixture metrics are omitted. Changed normalized fields still need
independent semantic review and publication proof. This is a counterfactual
comparison, not a new inference run or replacement database candidate.

Workers disable Python site startup hooks, use a fresh bytecode-cache location,
and trap network, common database and child-process calls. These are accidental
effect guards for trusted pinned product code, not an operating-system security
sandbox for hostile code. Explicit dependency pins do not automatically attest
every transitive import; declare that limitation in the environment receipt.

Successful output reuse verifies the completion/report/artifact hashes and the
same manifest. Failed or incomplete directories are preserved and refused on
reuse. Investigate a failure before creating a separately identified attempt;
do not overwrite evidence or repeat unchanged runs until one passes.

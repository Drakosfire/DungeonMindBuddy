# Ordinary benchmark workflow

Use the existing Buddy benchmark package for every ordinary question. Questions
are manifest data; no question-specific executable is required.

```sh
PYTHONPATH=src:. python -m evals.buddy_benchmark.workflow report \
  --manifest retained-manifest.json --output new-report-directory
```

`report` is offline. It never imports the app, opens a database connection or
dispatches a provider. It validates retained request/history/trace correlation,
prepared prompt hashes and byte lengths, and accounting by provider attempt ID.
Repeated lifecycle observations do not become additional calls or tokens.
Missing usage or billing stays unknown. This trace format does not supply actual
invoice costs; token-price estimates are not substituted for billed cost.

## Retained manifest

The manifest has schema `dmb_ordinary_benchmark_v1`, optional shared `pins`, and
a nonempty `cases` list. Each case supplies:

- `id`: unique safe artifact-directory identifier.
- `question`: exact ordinary question, with no expected answer appended.
- `capture_dir`: existing directory containing `request.json`, `answer-http.json`,
  `history-after.json` and `context-trace.json`.
- `prompt_dir`: retained `agent_request_evidence` directory.
- `assessment`: optional `{path, sha256}` pin to an adopted independent review.

Paths are relative to the manifest unless absolute. Shared pins are also
`{path, sha256}`. Original six-question captures and corrected Q09 use this same
contract without QID-specific branches. Old HTTP409/503 results remain failures;
the corrected turn remains a different capture. A missing artifact produces an
explicit incomplete/not-started result with unknown outcomes, never a pass.
Present but contradictory or tampered evidence is rejected.

## Independent assessments

HTTP200 is delivery evidence, not semantic correctness. Missing reviews produce
unknown semantic dispositions. Do not put grades in the case manifest.

An adopted review has schema `dmb_ordinary_benchmark_assessment_v1`, a nonempty
`reviewer` identifier, and a `capture` binding containing `world_id`,
`conversation_id`, `turn_id`, plus exact hashes named `request_sha256`,
`answer-http_sha256`, `history-after_sha256` and `context-trace_sha256`.

Its `boundaries` independently names `ingestion_publication`, `retrieval`,
`composition` and `citations`. Each judgment has `status` (`pass`, `partial`,
`fail`, `not_reached` or `unknown`) and nonempty `evidence`. Each evidence entry
contains an `artifact` pin, JSON `pointer` and exact `expected` reviewed value.
Review adoption is an explicit semantic judgment, independently checked against
the original findings; the runner verifies its binding rather than deciding that
a prose finding means pass. Reusing a review for another capture is rejected.
Preserve original reviews when adopting historical formats. There is no keyword
grader, answer completion repair, or inferred full-corpus precision score.

## Ordinary capture

```sh
PYTHONPATH=src:. python -m evals.buddy_benchmark.workflow capture \
  --manifest capture-manifest.json --output new-capture-directory
```

Capture is an explicit live operation. This consolidation was validated without
new paid calls. Future execution uses the existing product attempt/retry policy;
the runner adds neither a call cap nor a retry-until-pass loop.

In addition to cases, capture requires:

- `world` and a closed ordinary `request_template`: schema, Plan surface,
  matching World owner, primary Plan revision/hash, client work state,
  `graph_request: {"mode": "none"}`, optional null `graph_selection` and ordinary
  `plan_context_policy`. Client IDs are regenerated. No authored references,
  operation override, edit capture, supporting-work additions or Gold fields.
- Nonempty shared runtime/source `pins`.
- `runtime.source_tree`: a pin to a JSON map of every tracked source path to its
  SHA256. This must match the executing checkout, including this runner.
- `runtime.dependencies`: module-name to inventory pins, including at least
  `generationengine`, `openai`, `dungeonmind` and `worldkeeper`. Each inventory maps package-relative files to
  SHA256, excluding bytecode caches. Inventories bind actual imported packages.
- `provider_policy`: the exact existing `plan_jev_dispatch.request_budget()`
  value, checked after startup. The runner does not select models or allocations.
- `isolation.app` and `isolation.native`: expected local `host`, `port`,
  `database`, `oid` (string) and PostgreSQL `system_identifier` (string).
  `isolation.native.inventory` pins the shared row-inventory JSON for the fixed
  corpus. The full native inventory must match before capture and after every
  question; a drift stops subsequent dispatch.

Provision and qualify isolated state once through the existing owning tools;
reuse its pins for the cohort. The runner deliberately does not clone databases,
migrate schemas, publish knowledge or switch runtime checkouts. Supply the two
explicit database URL environment variables and existing provider credentials.
Never put credentials in manifests. Use the product's local-operator environment
configuration. The runner creates only its own session/artifact paths and token.
Hidden local profiles are rejected. Database, auth, session and artifact settings
are rechecked after startup and before each question.
Its APP database is mutable; native authority is only read by the ordinary path.

The capture command uses the existing in-process app and ordinary routes. It
checks readiness and unchanged database configuration before creating a fresh
conversation through CAS. The question goes through the ordinary turn endpoint.
History resolves the actual durable turn ID; the client request ID is not used
as a context-trace URL. No semantic review or Gold is copied into requests.

Every output directory is new. Exact HTTP response bytes survive non-JSON
failures. A transport exception is outcome-unknown, not evidence that a provider
was never called. History/trace readback and terminal records are attempted in
cleanup; no dispatch is repeated. The capture manifest and partial report remain
available even after a failed turn. Investigate uncertain outcomes before any
new execution. Fresh captures never inherit earlier semantic assessments.

## Historical tools and retirement

`run_current_corpus_question_gauntlet.py` is an oracle/Hermes evaluation, not the
ordinary producer. The Q01 native fixture/selected-subject answer and S8 proposal
proofs also test different historical contracts. Their evidence and unique
capabilities remain distinct. Shared checkpoint and row-inventory code now has
one owner in `evals/buddy_benchmark/artifacts.py`; historical routing-key shapes
are explicit parameters.

The ad hoc ordinary Q09 launcher is superseded by this workflow after retained
parity verification. Preserve its hash and nonexecuting provenance text rather
than another executable runtime path. New questions add case data and reviewed
assessment bindings, not another launcher.

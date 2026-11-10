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

## Writer judge calibration

The same `context-tasting` transport accepts an explicit `assessment` object with
file pins `candidates`, `reference` and `schema`, only with a compiled prompt
manifest whose contract is `buddy_writer_judge_v1`. Ordinary writer roles reject
assessment input. Candidates have blind local `candidate_id` and semantic `answer`
fields, validated against the captured native answer owner’s full nested schema.
The host reattaches its fixed schema discriminator for validation only. Model/cost
identity fields and invented candidate envelopes are rejected. Reference data contains only `required_concepts` with id/description;
hidden expected candidate grades stay in the offline calibration file.

The pinned native schema must equal `writer_assessment.quality_schema` for those
candidate/concept IDs. Original capture verification, route controls, raw attempt
retention and usage/cost/time accounting are shared with writer experiments.
Judge results are provider-only diagnostics, not QA acceptance or citation proof.
`writer_assessment.calibration_report` compares explicit reviewed seven-axis
judgments, excluding unknown human axes and reporting false passes, false failures,
abstentions and internal coverage inconsistencies. It does not infer human taste
or automatically authorize score-based grading. Freeze reference labels and
stopping rules before calls, retain rejected judges and test order variation.

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
# Frozen-context model tasting

`context-tasting --manifest tasting.json --output new-directory` reuses a pinned
context-ready writer capture through GenerationEngine's OpenRouter adapter. It
does not retrieve evidence, resume an APP turn, or publish anything. Manifest
schema `dmb_context_tasting_v1` requires `source_request` and `context_ready`
file/hash pins and distinct explicit `models`. The request body hash/size and
semantic frame hash are checked before dispatch.

The retained system prompt, input content, reasoning effort and output schema
are shared across models. GE accepts a single user string: original ordered user
message contents are joined with two newlines, without JSON-escaping their text.
This common message-boundary adaptation and provider-native wrappers differ from
the original OpenAI Responses wire; this is a provider-only comparison, not exact
original wire replay. Gold is not added.
The pinned GE OpenRouter adapter sends native strict JSON Schema in
`response_format` and requires parameter-supporting endpoints. It does not append
schema instructions to system/user prose or downgrade to prompt-only JSON.
Optional `endpoint_catalog` pins a model-keyed public endpoints response snapshot;
the workflow binds model IDs and allows only tags declaring `structured_outputs`,
`response_format` and the requested reasoning control. No eligible endpoint means
excluded, zero provider attempts. Explicit routes disable outside-list fallback.
The original prompt-only tasting remains retained as a historical diagnostic.
Models run once each, two concurrently, without transport/conformance retry.
Returned outputs and failures are retained.
OpenRouter's reported cost is authoritative when supplied; missing cost is unknown.

Random blind labels are assigned before execution. `identity-key.json` is separate
from `blind-answers.json`, which contains only labels, answers and failure status.
Model-bearing request/observation files remain audit-only.
Hosted open-weight runs do not measure local hardware performance. Existing output
directories are refused, so an interrupted or failed tasting cannot silently replay.

For a controlled presentation experiment, `presentation: flat_native_assertions_v2`
renders the one exact native evidence frame as tables. Original assertion and
qualification field paths form shared headers; cells preserve JSON values and `_`
denotes an absent field. Every fact, qualification, citation handle, original row
order, scalar type and empty container survives exact host readback. Source
excerpts and other frame fields remain unchanged. The readback layout is a
host-only verification artifact, never model context or a new evidence authority.
The system prompt and native output schema stay fixed. The original `retained_json`
presentation remains the frozen control; this explicit experiment is not a new
product default or an error fallback. Reuse retained control outputs and routes
rather than rerunning retrieval or unchanged baselines.

For prompt-only experiments, `instructions` pins a UTF-8 system-prompt file and
`prompt_components` pins its versioned host-only manifest. The latter records
contract, ordered named/versioned component texts and hashes. Every component hash
is recomputed and the exact joined texts must equal the final instructions before
any dispatch. Manifest data is retained separately, never added to messages.
`application_state.agent_conversation.response_prompt` compiles the initial
response-only voice/evidence/citation/output components; Rules guidance is added
only when active. Ordinary native conversation calls use this compiler at their
product owner; experimental context presentations remain separately selected.
Do not change prompt and evidence presentation in the same experiment. Known
bookkeeping leakage in retained legacy qualification prose must be resolved at
its owner before sending that context in another paid comparison.
# Reviewed qualification separation in writer experiments

Ordinary native Plan/Play/Build writer calls assemble the versioned response
compiler at `PlanJevWriter` after actual work reconstruction. Plan requires its
unique selected work; Build requires its actual answer-from-sources contract or
reviewed task binding; native Play owns a read-only Run question.
Actual clarification, reviewed discussion, capability-limit explanation and
destination explanation select one small task component through the same compiler.
Reviewed discussion takes only its bound selected task as the assignment; sibling
tasks remain context. Writing, review execution and image preparation retain
their capability owners. Native conversational replies carry no image instructions.
Rules guidance requires a supplied lookup; related-page guidance requires supplied
saved pages. `writer.prompt_components` is host-only inspectability, never model
input. Ordinary calls do not first construct the superseded broad instruction
string. Native schema, messages, admission and citation authority are unchanged.
This integration does not import experimental data repair or flat presentation
into runtime, repair historical database metadata, or deploy the app.

The current flat experiment uses `flat_native_assertions_v2`. It prints each
byte-identical complete qualification once, with the full list of its original
handles. Assertions still reference their original handles; no factual values or
citation handles change. Host-only readback restores original definition order
and object structure. Similar wording, different value types, whitespace or
object ordering do not qualify for grouping. The previous flat format is retired;
read historical artifacts with their pinned code, not a parallel runtime reader.

`context-tasting` optionally accepts a `qualification_review` file pin. The closed
`dmb_reviewed_qualification_parts_v1` artifact names its independent `reviewer`,
`source_frame_sha256`, and `records`. Each record has `qualification_handle`,
`domain_index`, `original_sha256`, and ordered `parts` with exactly `role` and
`text`. Roles are `meaning` or `host_audit`; pending decisions fail closed.
The frame fingerprint is SHA256 of UTF-8 compact JSON, preserving object order
(`ensure_ascii=False`, separators `,` and `:`). It is distinct from APP authority.

Every source-qualification slot must be covered exactly once. Parts must reproduce
its original bytes and digest; at least nonblank meaning remains. Only explicitly
reviewed audit parts are omitted. No patterns discover roles and no literal facts,
quotes, citation handles, other metadata or evidence records are changed.
Independent semantic review is essential: reconstruction cannot prove that a
reviewer classified a span correctly. A reviewer name is attribution, not a
cryptographic attestation or automatic approval.

The workflow verifies the original frozen request/context-ready binding before
applying this diagnostic presentation. `frozen-packet.json` stays original;
`qualification-review.json` retains the review, derived frame and separate hashes.
No replacement APP proof, publication or citation receipt is created. This option
does not clean live records or activate a new product prompt. Future source review
annotations should keep provenance in existing typed host fields, outside semantic
qualification prose. Use one change per comparison; combining this option with a
prompt or flattening change is not a controlled single-variable experiment.

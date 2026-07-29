# HANDOFF — TL01B: Evidence-Bound Model Shadow Temporal Extraction

**Created:** 2026-07-29
**Project:** DungeonBuddy / DungeonMindBuddy
**Repository:** `Drakosfire/DungeonMindBuddy`
**Status:** ACTIVE — next Timeline preparatory coding slice
**Suggested canonical path:** `Docs/Plans/HANDOFF-tl01b-model-shadow-temporal-extraction.md`
**Required dependency:** PR `#450`, merged as `d6ea4959c9bcc2f113ef50d912629864c1a1c04b`
**Required implementation base:** current clean `origin/main` containing that merge
**Suggested branch:** `feat/tl01b-model-shadow-temporal-extraction`
**Suggested worktree:** existing isolated Timeline worktree
**Expected PR count:** one
**Operating mode:** Eval-only structured extraction and sealed-cohort evaluation
**Authoritative graph writes:** forbidden
**Timeline API or UI:** forbidden

---

## §0 Mission

Build an evidence-bound model-shadow producer that reads one sealed candidate-only `GraphContribution`, examines only exact source evidence owned by selected assertions, emits a valid `TemporalAnnotationOverlayV1`, and passes that overlay through the existing TL01 shadow-preview builder.

The completed capability is:

```text
sealed candidate contribution
+ explicitly selected assertion IDs
+ exact assertion-owned source spans
+ structured model extraction
→ validated TemporalAnnotationOverlayV1
→ deterministic TemporalShadowPreviewV1
→ human-comparable evaluation report
```

This PR must prove that real campaign prose can be evaluated for:

* occurrence time;
* valid time;
* relative or incomplete time;
* temporal ambiguity;
* and temporal non-applicability

without changing graph truth.

The resulting overlay remains non-authoritative.

It must not enter contribution merge, graph revision publication, projection, Hermes, or any user-facing Timeline surface.

---

## §1 Why this slice exists

TL00 established a typed temporal contract:

```text
source_time
occurrence_time
valid_time
```

TL01 established:

```text
TemporalAnnotationOverlayV1
TemporalShadowPreviewV1
exact contribution binding
exact assertion targeting
evidence ownership validation
hypothetical assertion identity
no authoritative writes
```

What has not yet been proven is whether a model can produce useful temporal annotations from actual campaign prose while respecting those contracts.

Before adding temporal fields to authoritative extraction, we need evidence about:

1. whether explicit event time can be recovered reliably;
2. whether source-session provenance is incorrectly treated as occurrence time;
3. whether persistent-state boundaries can be distinguished from simple re-attestation;
4. whether relative and incomplete time can be represented conservatively;
5. whether ambiguity remains ambiguity instead of becoming invented precision;
6. whether model output can be bound to exact assertions and exact evidence;
7. whether the resulting temporal data is useful enough to justify participant-role and projected-occurrence work.

This PR creates that experiment.

---

## §2 Selected capability

### Capability

```text
Given one valid temporal extraction case,
produce one evidence-bound model overlay and one TL01 shadow preview.
```

### Primary invariant

```text
The model may propose temporal interpretation only for explicitly selected
assertions and may cite only exact evidence owned by each assertion.
```

### Authority invariant

```text
No output of this PR is graph authority.
```

### Temporal invariant

```text
Source provenance never becomes occurrence_time or valid_time automatically.
```

### Mission falsification test

The mission has widened beyond one capability if implementation requires:

* changing `GraphContributionAssertion`;
* changing `TemporalEnvelopeV1`;
* changing `TemporalAnnotationOverlayV1`;
* changing candidate graph extraction;
* modifying `candidate_graph_to_contribution`;
* accepting or rejecting assertions;
* writing contributions;
* rebuilding or publishing graph revisions;
* event identity resolution;
* participant-role storage;
* projected occurrences;
* timeline queries;
* or UI.

Stop rather than absorbing those capabilities.

---

## §3 Mandatory first moves

Before coding:

1. Read:

```text
AGENTS.md
.cursor/rules/external-agent-pr-loop.mdc
.cursor/skills/external-agent-pr-loop/SKILL.md
.cursor/rules/responses-api-structured-extraction.mdc

Docs/Design/CONTRACT-temporal-envelope-v1.md
Docs/Design/CONTRACT-temporal-shadow-overlay-v1.md
Docs/Backlog/GRAPH-V2.md
```

2. Record repository state:

```bash
git fetch origin
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git worktree list
```

3. Confirm the TL01 merge is in ancestry:

```bash
git merge-base --is-ancestor \
  d6ea4959c9bcc2f113ef50d912629864c1a1c04b \
  origin/main
```

4. Inspect current owning code:

```text
src/graph_memory/temporal_shadow.py
src/graph_memory/kernel/temporal.py
src/graph_memory/source_span.py
src/graph_memory/kernel/contributions.py
src/graph_memory/kernel/contribution_models.py
src/graph_memory/extraction/category_candidate_graph_extractor.py
src/llm/api_client.py
```

5. Confirm there is no overlapping open temporal-extraction PR.

6. Preserve unrelated local and runtime state.

---

## §4 Runtime isolation

The TL01B runner must not read from or write to:

```text
out/graph_memory/worlds/eldyrwild/
graph heads
revision stores
contribution stores
Graph Review state
ThreatDraft state
combat state
the primary product worktree’s writable out/
```

Inputs must be explicit files named by a sealed case manifest.

Outputs must be written only to an explicit evaluation directory.

Do not symlink the Timeline worktree’s runtime directory to the main product tree.

The model runner must not receive a world ID and then discover graph state implicitly.

---

## §5 Architecture decision

TL01B adds a model producer above TL01.

It does not alter TL01.

```text
GraphContribution
       │
       ├── selected assertion IDs
       │
       └── assertion-owned evidence refs
                    │
                    ▼
      TemporalShadowExtractionCaseV1
                    │
        exact evidence resolution
                    │
                    ▼
       structured model annotation batch
                    │
      deterministic local conversion
                    │
                    ▼
       TemporalAnnotationOverlayV1
                    │
                    ▼
       existing TL01 preview builder
                    │
                    ▼
       TemporalShadowPreviewV1
                    │
                    ▼
       optional gold comparison report
```

The model must not output:

* `overlay_id`;
* `annotation_id`;
* source time;
* graph contribution fields;
* assertion IDs other than the supplied target IDs;
* or any publication decision.

Those values are owned by deterministic local code.

---

## §6 Sealed extraction case

Create a strict case contract:

```text
dmb_temporal_shadow_extraction_case_v1
```

Suggested shape:

```json
{
  "schema": "dmb_temporal_shadow_extraction_case_v1",
  "case_id": "temporal-case:c2-temporal-cohort-v1",
  "base_contribution_path": "evals/.../base-contribution.json",
  "base_contribution_sha256": "<sha256>",
  "selected_assertion_ids": [
    "assertion:..."
  ],
  "source_artifacts": [
    {
      "source_artifact_id": "artifact:...",
      "source_ref_id": "source:...",
      "artifact_kind": "session_recap",
      "label": "Campaign 2 Session 12",
      "evidence_role": "canonical_source",
      "visibility_state": "gm",
      "path": "Corpus/.../session-12.md",
      "content_sha256": "<sha256>"
    }
  ],
  "evidence_registry": [
    {
      "evidence_ref_id": "evidence:...",
      "source_span_ref": {
        "source_ref_id": "source:...",
        "source_artifact_id": "artifact:...",
        "source_anchor_id": "anchor:...",
        "start_line": 10,
        "end_line": 13
      }
    }
  ],
  "gold_overlay_path": "evals/.../gold-overlay.json"
}
```

### Case rules

* Paths must be repository-relative.
* Absolute paths are forbidden.
* `..` traversal is forbidden.
* Every referenced file must remain within the resolved repository root.
* File digests must match before any model call.
* `selected_assertion_ids` must be non-empty and unique.
* Every selected ID must exist exactly once in the contribution.
* The base contribution must satisfy the TL01 candidate-only contract.
* Every evidence registry entry must have a unique `evidence_ref_id`.
* Every evidence reference used by a selected assertion must resolve through the supplied registry.
* Registry evidence not owned by the target assertion must not be placed in that assertion’s prompt packet.
* A missing source artifact, digest mismatch, unresolved span, or ambiguous evidence binding must fail before the model call.

Do not permit the case to refer to a graph root, world head, contribution store, or remote URL.

---

## §7 Assertion selection

The runner processes only:

```text
selected_assertion_ids
```

It must not silently annotate every assertion in the contribution.

Each selected assertion must be canonical and uniquely targetable according to TL01 rules.

The model must return exactly one annotation result for every selected assertion.

Required target-set behavior:

```text
missing selected assertion in model output
→ fail

extra assertion ID in model output
→ fail

duplicate assertion ID in model output
→ fail

unknown assertion ID
→ fail
```

A selected assertion may legitimately result in:

```text
resolved
ambiguous
unresolved
not_applicable
```

Omission is not a status.

---

## §8 Evidence packet construction

Resolve evidence using the existing source-span boundary.

For each selected assertion:

1. Obtain the assertion’s owned evidence IDs through the existing provenance helper.
2. Find the matching entries in the case evidence registry.
3. Resolve those `SourceSpanRef` objects against the supplied source artifacts.
4. Fail on:

   * missing artifact;
   * source-ref mismatch;
   * out-of-range span;
   * ambiguous text/structured reference;
   * missing highlightable text;
   * or any blocker/error-level evidence-resolution issue.
5. Build one assertion-specific packet containing only:

   * assertion semantic fields;
   * owned evidence IDs;
   * exact resolved evidence snippets;
   * restrained surrounding context.

Do not send the complete source document.

Do not send evidence owned only by another assertion.

### Assertion semantic packet

Include:

```text
base_assertion_id
assertion_kind
subject_node_id
target_node_id
predicate
label
semantic value with provenance-only collections removed
```

Do not send the existing source session as an instruction that the event occurred then.

### Evidence packet

For each evidence block include:

```text
evidence_ref_id
source_artifact_id
source_anchor_id
exact snippet
limited surrounding context
```

Use a sufficiently high snippet limit for the sealed cohort.

If the required temporal wording is truncated, narrow or repair the source span rather than asking the model to infer around the truncation.

---

## §9 Model-output contract

Create a strict structured-output schema:

```text
dmb_temporal_model_annotation_batch_v1
```

Suggested top-level shape:

```json
{
  "schema": "dmb_temporal_model_annotation_batch_v1",
  "annotations": [],
  "batch_diagnostics": []
}
```

Each annotation contains:

```json
{
  "base_assertion_id": "assertion:...",
  "interpretation_status": "resolved",
  "occurrence_time": null,
  "valid_time": null,
  "evidence_ref_ids": ["evidence:..."],
  "source_phrase": "during the siege",
  "extraction_confidence": "high",
  "diagnostics": []
}
```

Every property must be present because the Responses API schema is strict.

Optional semantic fields use explicit `null`.

### Status rules

#### `resolved`

Requires at least one of:

```text
occurrence_time
valid_time
```

Also requires:

```text
source_phrase
at least one evidence_ref_id
```

#### `ambiguous`

Requires:

```text
source_phrase
at least one diagnostic
at least one evidence_ref_id
```

Must not contain normalized occurrence or valid time.

#### `unresolved`

Requires:

```text
source_phrase or diagnostics
at least one evidence_ref_id
```

Must not contain normalized occurrence or valid time.

#### `not_applicable`

Must not contain occurrence or valid time.

Requires a diagnostic explaining why semantic time does not apply.

Examples:

```text
persistent relationship re-attested without a start/end boundary
descriptive attribute with no occurrence
source passage supplies observation time only
```

---

## §10 Temporal output shape

The structured-output schema may use a transport representation tailored to strict JSON Schema, but deterministic local code must convert it into the existing TL00 models.

The transport must support:

```text
point occurrence
interval occurrence
open valid-time interval
closed valid-time interval
relative time
campaign date
session time
textual/incomplete time
unknown time
```

Do not introduce additional temporal concepts.

After conversion, every semantic value must validate through:

```text
TemporalPointV1
TemporalExtentV1
TemporalIntervalV1
TemporalEnvelopeV1
```

Do not duplicate or weaken TL00 validation in the authoritative conversion step.

---

## §11 Prompt contract

Create one versioned prompt:

```text
TEMPORAL_SHADOW_PROMPT_VERSION = "tl01b-v1"
```

The prompt must explicitly state:

```text
You are producing review-only temporal annotations.

Source-document time is not occurrence time.

A session ID identifies where a claim was recorded unless the quoted prose
explicitly establishes that the described event happened in that session.

Do not infer start or end boundaries merely because prose uses present or past tense.

Use resolved only when the cited words support the normalized time.

Use ambiguous or unresolved instead of inventing precision.

Use not_applicable when the passage is only a re-attestation or has no
fictional temporal boundary.
```

The model must be instructed to:

* use only supplied evidence;
* return one result for every selected assertion;
* preserve uncertainty;
* quote a short exact source phrase;
* cite only supplied evidence IDs;
* avoid reasoning from filenames or session metadata;
* avoid creating node IDs, event IDs, or relationships;
* avoid publication decisions.

Do not put the full source text in system instructions, logs, exceptions, or PR comments.

---

## §12 Provider integration

Define a protocol suitable for fake-client tests:

```python
class TemporalShadowExtractionClient(Protocol):
    def extract_annotations(...) -> TemporalModelAnnotationBatchV1:
        ...
```

Provide one production implementation using:

```text
OpenAI Responses API
DungeonMindApiClient.responses_create
text.format.type = json_schema
strict = true
```

Do not use:

* Chat Completions;
* prompt-only JSON;
* permissive JSON parsing;
* or silent `{}` fallback.

### Model resolution

Use this order:

1. explicit CLI or request override;
2. existing graph-memory category-extraction model-policy resolution;
3. existing centralized fallback behavior owned by that resolver.

Do not introduce another unrelated hardcoded model default.

A dedicated temporal model-policy action may be proposed later if the cohort proves a distinct requirement.

### Provider failure behavior

Handle explicitly:

```text
refusal
incomplete response
missing output text
schema-invalid output
API exception
timeout
```

All failures become typed temporal-extraction errors.

Record provider response ID, model ID, token usage, elapsed time, and failure classification when available.

Do not persist the complete prompt or source packet in ordinary logs.

---

## §13 Post-model grounding checks

Structured schema validation is not sufficient.

After parsing, enforce:

1. Exact selected target set.
2. Every cited evidence ID is owned by the target assertion.
3. Every cited evidence ID was present in that assertion’s prompt packet.
4. `source_phrase` is a verbatim substring of at least one cited evidence snippet after restrained whitespace normalization.
5. Resolved annotations contain semantic time.
6. Non-resolved annotations contain no semantic time.
7. No source time was emitted by the model.
8. Every temporal object validates through TL00.
9. Blank diagnostics and phrases fail.
10. Extra fields fail.

Do not repair unsupported model output silently.

A failed annotation batch produces no overlay.

---

## §14 Deterministic overlay assembly

The model does not choose durable sidecar identities.

For each validated model annotation, compute:

```text
annotation_id
```

deterministically from:

```text
case_id
base_assertion_id
normalized model annotation payload
model ID
prompt version
```

Suggested form:

```text
temporal-annotation:<first-16-of-sha256>
```

Create:

```text
TemporalOverlayProducerV1(
    kind="model_shadow",
    name="temporal-shadow-extractor",
    version="tl01b-v1"
)
```

Then:

1. Construct `TemporalAssertionAnnotationV1`.
2. Compute the canonical TL01 overlay ID.
3. Construct and revalidate `TemporalAnnotationOverlayV1`.
4. Pass it to `build_temporal_shadow_preview`.
5. Do not duplicate TL01 composition or identity logic.

The final overlay must be acceptable to the unmodified TL01 loader.

---

## §15 Gold comparison

The sealed cohort includes a human-authored:

```text
TemporalAnnotationOverlayV1
```

with:

```text
producer.kind = human_gold
```

Create an evaluation contract:

```text
dmb_temporal_shadow_comparison_v1
```

Compare predicted and gold annotations by:

```text
base_assertion_id
```

Ignore:

```text
overlay_id
annotation_id
producer identity
diagnostic wording
source-phrase wording beyond grounding validity
```

Compare semantically:

```text
interpretation status
occurrence-time payload
valid-time payload
evidence selection
```

### Per-assertion classifications

Use:

```text
exact_match
safe_under_resolution
unsafe_over_resolution
wrong_temporal_lane
wrong_temporal_value
status_mismatch
missing_prediction
extra_prediction
```

### Safety metrics

At minimum:

```text
source_to_occurrence_false_positives
source_to_valid_time_false_positives
unsupported_resolved_annotations
foreign_evidence_attempts
ungrounded_source_phrases
invalid_temporal_payloads
```

### Quality metrics

At minimum:

```text
status_accuracy
exact_semantic_match_count
resolved_exact_match_count
safe_under_resolution_count
ambiguous_or_unresolved_count
not_applicable_accuracy
```

A conservative `unresolved` prediction where gold is `resolved` is a quality miss, not an unsafe assertion.

A `resolved` prediction where gold is ambiguous, unresolved, or not applicable is an unsafe over-resolution.

---

## §16 Evaluation verdict

The comparison report must produce one of:

```text
SAFE_FOR_NEXT_EXPERIMENT
ITERATE_PROMPT
BLOCKED_BY_EVIDENCE
BLOCKED_BY_CONTRACT
PROVIDER_FAILURE
```

Suggested interpretation:

### `SAFE_FOR_NEXT_EXPERIMENT`

* zero unsafe temporal claims;
* zero evidence-boundary violations;
* valid overlay and preview;
* enough correct resolved examples to justify participant-role experimentation.

### `ITERATE_PROMPT`

* infrastructure and evidence binding are sound;
* model output is too incomplete or inaccurate;
* no contract change is required.

### `BLOCKED_BY_EVIDENCE`

* source spans are missing, too broad, truncated, or not uniquely bound.

### `BLOCKED_BY_CONTRACT`

* actual campaign prose requires a temporal representation TL00 cannot express safely.

### `PROVIDER_FAILURE`

* the real provider path cannot complete.

This verdict does not publish temporal data.

A poor model verdict does not necessarily invalidate the PR.

The PR’s capability is trustworthy evaluation. Poor model performance blocks promotion, not the evaluator.

---

## §17 Run artifact

Create:

```text
dmb_temporal_shadow_extraction_run_v1
```

Write one explicit run directory containing:

```text
run-manifest.json
model-output.json
overlay.json
preview.json
comparison.json
provider-metadata.json
```

### Run manifest

Record:

```text
run_id
case_id
repository SHA
base contribution ID
base contribution digest
selected assertion IDs
source artifact IDs and digests
model ID
prompt version
schema version
overlay ID
preview verdict
comparison verdict
```

### Privacy and corpus handling

Do not copy complete source documents into the run directory.

Do not persist the complete rendered prompt.

`model-output.json` may contain only the structured annotation batch.

The output may preserve the short source phrases needed for grounding review.

Provider metadata must not include credentials or complete request content.

### Run identity

Compute `run_id` from canonical content including:

```text
case digest
model ID
prompt version
validated model output
```

Do not use wall-clock time as identity.

A timestamp may exist as non-identity metadata.

---

## §18 CLI

Provide:

```bash
python -m graph_memory.temporal_shadow_extraction_cli \
  --case evals/.../temporal-case.json \
  --output-dir out/temporal-shadow/<run-name> \
  [--model-id ...] \
  [--overwrite]
```

Required behavior:

```text
invalid case
→ non-zero exit before provider call

evidence-resolution failure
→ non-zero exit before provider call

provider refusal/incomplete
→ non-zero exit with typed diagnostic artifact

invalid model output
→ non-zero exit; no overlay or preview

valid model output
→ overlay + preview + comparison

existing output directory
→ fail unless --overwrite
```

The CLI must not accept:

```text
world ID
graph root
revision ID
contribution-store path
publish flag
merge flag
accept flag
```

---

## §19 Sealed real campaign cohort

Run a bounded cohort of approximately 7–12 assertions.

The cohort must include at least one of each:

1. Explicit event occurrence.
2. Source session different from fictional occurrence.
3. Persistent state or relationship with an explicit start.
4. Persistent state or relationship with an explicit end or transition.
5. Relative historical occurrence.
6. Ambiguous temporal language.
7. Re-attestation with no new semantic time.
8. Negative case where source-session provenance must not become occurrence time.

Strong candidate concepts include:

```text
Baergrom revives Caelynn
Lysandra begins commanding or holding a new role
North Gate becomes damaged or destroyed
a repeated party-membership relationship
Maelthor or another historical figure with relative past time
“long ago” or similarly ambiguous language
```

Use only examples actually supported by canonical source passages and sealed candidate assertions.

Do not invent source evidence to satisfy the cohort matrix.

When a desired case cannot be found, record the missing category.

---

## §20 Required live proof

Before merge, perform one real-provider run.

Record:

```text
repository SHA
case ID
base contribution ID and digest
model ID
prompt version
provider response ID
selected assertion count
overlay ID
preview verdict
comparison verdict
token usage
cost if available
elapsed time
```

The report must include:

* exact safety metrics;
* exact quality metrics;
* per-case classifications;
* model strengths;
* model failure modes;
* whether the next slice should be prompt iteration, evidence repair, participant roles, or a temporal-contract revision.

Do not paste full campaign passages into the PR body.

---

## §21 Expected changed paths

```text
CREATE  src/graph_memory/temporal_shadow_extraction.py
CREATE  src/graph_memory/temporal_shadow_extraction_schema.py
CREATE  src/graph_memory/temporal_shadow_extraction_cli.py
CREATE  tests/test_temporal_shadow_extraction.py

CREATE  evals/graph_memory_layer/temporal_shadow_evaluation.py
CREATE  evals/graph_memory_layer/examples/temporal_shadow_cohort/*
CREATE  Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md
CREATE  Docs/Reports/REPORT-tl01b-temporal-shadow-cohort.md
CREATE  Docs/Plans/HANDOFF-tl01b-model-shadow-temporal-extraction.md
```

Conditionally permitted:

```text
MODIFY  src/graph_memory/__init__.py
```

only when current package export conventions require it.

Explicitly prohibited:

```text
src/graph_memory/kernel/temporal.py
src/graph_memory/temporal_shadow.py
src/graph_memory/kernel/contributions.py
src/graph_memory/kernel/contribution_models.py
src/graph_memory/candidate_graph_preview.py
src/graph_memory/candidate_graph_to_contribution.py
src/graph_memory/kernel/contribution_merge.py
src/graph_memory/kernel/world_projection.py
apps/live_control_server/
apps/live-control-ui/
runtime graph stores
production extraction prompts
```

If a prohibited path appears necessary, stop and report the missing seam.

---

## §22 Required tests

### Case-contract tests

Prove:

* absolute paths rejected;
* path traversal rejected;
* missing file rejected;
* artifact digest mismatch rejected;
* contribution digest mismatch rejected;
* empty selected assertion list rejected;
* duplicate selected assertion IDs rejected;
* unknown selected assertion rejected;
* duplicate or non-canonical base assertions rejected.

### Evidence-resolution tests

Prove:

* exact owned evidence resolves;
* missing registry entry fails;
* foreign evidence cannot enter an assertion packet;
* source-ref mismatch fails;
* out-of-range span fails;
* unresolved evidence fails before model invocation;
* truncated critical evidence fails or is explicitly rejected by the case.

### Structured-output tests

Assert the request uses:

```text
Responses API
text.format.type == json_schema
strict == true
```

Prove:

* every schema property is required;
* nullable fields use explicit null;
* extra properties fail;
* invalid temporal shapes fail;
* refusal fails;
* incomplete response fails;
* missing output fails.

### Target-set tests

Prove:

* exact one-result-per-selected-assertion succeeds;
* missing target fails;
* extra target fails;
* duplicate target fails;
* unknown target fails.

### Grounding tests

Prove:

* exact source phrase succeeds;
* phrase from uncited evidence fails;
* paraphrased but non-verbatim phrase fails;
* foreign evidence ID fails;
* resolved annotation without phrase fails;
* ambiguous and unresolved outputs preserve uncertainty.

### Temporal-safety tests

Prove:

```text
source session only
→ not occurrence time
```

```text
explicit source phrase establishes occurrence
→ occurrence may equal source session
```

```text
present-tense re-attestation
→ no invented valid-time start
```

```text
ambiguous relative phrase
→ no invented campaign date
```

### Overlay compatibility tests

Prove:

* deterministic annotation IDs;
* deterministic overlay ID;
* TL01 overlay loader accepts the result;
* TL01 preview builder accepts the result;
* no base contribution mutation;
* no graph store access.

### Evaluation tests

Prove every comparison classification and verdict branch.

### CLI tests

Prove:

* successful run with fake client;
* failure before model call on bad evidence;
* provider failure artifact;
* output protection;
* no graph-runtime arguments or writes.

### Regression suite

Run at minimum:

```bash
uv run pytest tests/test_temporal_shadow_extraction.py -q
uv run pytest tests/test_temporal_shadow.py -q
uv run pytest tests/test_graph_kernel_temporal.py -q
uv run pytest tests/test_candidate_graph_to_contribution.py -q
uv run pytest tests/test_graph_kernel_contributions.py -q
uv run pytest tests/test_edge_core_semantic_fingerprint.py -q
git diff --check
```

Record exact commands and results.

---

## §23 Documentation contract

Create:

```text
Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md
```

Required sections:

```markdown
# Temporal Shadow Extraction V1

## Purpose

## Authority boundary

## Extraction case

## Assertion selection

## Evidence resolution

## Model prompt

## Structured-output schema

## No source-to-occurrence inference

## Target-set validation

## Source-phrase grounding

## Deterministic annotation identity

## TL01 overlay assembly

## Shadow preview

## Gold comparison

## Run artifacts

## Provider failures

## Corpus and privacy handling

## Non-goals

## Successor decision
```

---

## §24 Explicit non-goals

TL01B does not:

* change authoritative graph extraction;
* add temporal fields to candidate graph IR;
* create accepted temporal assertions;
* merge or publish contributions;
* mutate graph revisions;
* add event nodes;
* add participant-role bindings;
* reconcile repeated events;
* determine event identity;
* build current-state projections;
* order a complete timeline;
* expose a Timeline API;
* expose a Timeline UI;
* change Hermes;
* rejuvenate the full corpus;
* or implement Graph V2.

---

## §25 Demolition declaration

```text
Replaced path:
none

Deleted in this PR:
no

Retained path:
human-authored TemporalAnnotationOverlayV1 and deterministic TL01 preview

Retained reason:
TL01B adds one model producer above the reviewed sidecar contract

New path:
sealed case
→ evidence-bound model annotation batch
→ deterministic TL01 overlay
→ TL01 preview
→ human comparison

Required deletion or migration owner:
future authoritative temporal-producer cutover, only after repeated shadow evaluation
```

---

## §26 Acceptance criteria

TL01B is complete only when:

* [ ] Current `origin/main` SHA is recorded.
* [ ] PR `#450` merge is in ancestry.
* [ ] No overlapping temporal extraction PR exists.
* [ ] Work occurs in the isolated Timeline worktree.
* [ ] No graph runtime store is read or written.
* [ ] A strict sealed-case contract exists.
* [ ] Base and source files are content-digest bound.
* [ ] Assertions are selected explicitly.
* [ ] Exact evidence is resolved before model invocation.
* [ ] Only assertion-owned evidence enters each prompt packet.
* [ ] The model uses Responses API strict structured output.
* [ ] Model resolution follows existing policy behavior.
* [ ] Source time is not requested from the model.
* [ ] The model returns exactly one result per selected assertion.
* [ ] Source phrases are verified against cited evidence.
* [ ] Unsupported model output is rejected rather than repaired.
* [ ] Annotation IDs are deterministic.
* [ ] The resulting TL01 overlay revalidates unchanged.
* [ ] The existing TL01 preview builder produces the preview.
* [ ] The base contribution remains unchanged.
* [ ] Gold comparison distinguishes unsafe over-resolution from conservative misses.
* [ ] A bounded real campaign cohort is sealed.
* [ ] One real-provider run completes.
* [ ] The cohort report records exact metrics and limitations.
* [ ] Poor extraction quality does not get reframed as success.
* [ ] No authoritative producer cutover occurs.
* [ ] No participant roles, occurrence IR, timeline query, or UI are added.
* [ ] Focused tests pass.
* [ ] Changed paths remain within the allowlist.
* [ ] `git diff --check` passes.

---

## §27 Stop conditions

Stop and report when:

* exact assertion evidence cannot be reconstructed;
* selected evidence cannot be uniquely resolved;
* source spans are too broad or truncated to ground temporal phrases;
* the current contribution lacks uniquely targetable candidate assertions;
* the Responses API strict schema cannot represent TL00 time safely;
* the model requires complete source documents rather than exact spans;
* provider output cannot be grounded to verbatim evidence;
* real prose requires a temporal concept absent from TL00;
* implementation requires changing TL00 or TL01;
* implementation requires modifying authoritative extraction;
* implementation needs graph-store access;
* provider credentials or service availability block the live proof;
* or an open PR already owns this capability.

Use:

```text
Stop condition:
Repository SHA:
Case ID:
Base contribution ID:
Affected assertion ID:
Affected evidence IDs:
Exact failure:
Why TL01B cannot absorb it:
Required contract or evidence decision:
Suggested successor slice:
Operator decision required:
```

---

## §28 Required PR body

```markdown
## Mission

Add evidence-bound model-shadow temporal extraction and sealed-cohort evaluation without changing graph authority.

## Dependency

PR #450 / merge d6ea4959c9bcc2f113ef50d912629864c1a1c04b

## Capability

Selected candidate assertions
+ exact owned source spans
→ structured temporal annotations
→ TL01 overlay
→ TL01 preview
→ gold comparison

## Existing behavior preserved

- candidate extraction unchanged
- contribution mapper unchanged
- TL00 unchanged
- TL01 unchanged
- contribution ledger untouched
- graph revisions untouched
- product surfaces unchanged

## Live cohort result

<model, case, overlay, preview, metrics, verdict>

## Explicitly not implemented

- authoritative temporal production
- event nodes
- participant roles
- timeline query
- timeline UI
- corpus rejuvenation

## Demolition

<copy §25>

## Tests

<exact commands and results>

## Next decision

<SAFE_FOR_NEXT_EXPERIMENT | ITERATE_PROMPT | BLOCKED_BY_EVIDENCE | BLOCKED_BY_CONTRACT | PROVIDER_FAILURE>
```

---

## §29 Required handback

The coding-agent handback must include:

1. Actual base SHA.
2. Head SHA.
3. Branch and worktree path.
4. Confirmation that PR `#450` is in ancestry.
5. Exact changed paths.
6. Final case schema.
7. Final model-output schema.
8. Prompt version.
9. Model-resolution behavior.
10. Evidence-resolution behavior.
11. Target-set enforcement.
12. Source-phrase grounding behavior.
13. Deterministic annotation-ID contract.
14. Overlay ID and preview verdict.
15. Real campaign cohort matrix.
16. Gold overlay path.
17. Live model ID and provider response ID.
18. Token usage, elapsed time, and cost if available.
19. Comparison metrics.
20. Evaluation verdict.
21. Every test command and result.
22. Baseline failures, if any.
23. Paths outside the allowlist, or `none`.
24. Runtime graph state touched, expected `none`.
25. Confirmation that TL00 and TL01 were unchanged.
26. Confirmation that no `GraphContribution` was emitted.
27. Confirmation that no graph write occurred.
28. Confirmation that no Timeline API or UI was added.
29. Stop conditions encountered, or `none`.
30. Exact recommended next slice.

---

## §30 Successor decision

Do not assume TL02 is automatically next.

Choose based on the cohort.

### When the verdict is `SAFE_FOR_NEXT_EXPERIMENT`

The likely next slice is:

```text
TL02 — Participant-role annotation overlay
```

This adds the actor, patient, target, instrument, location, and affected-object roles needed for node-centric event projection.

### When the verdict is `ITERATE_PROMPT`

Dispatch a narrow extraction-quality slice.

Do not change the temporal contract merely to improve model accuracy.

### When the verdict is `BLOCKED_BY_EVIDENCE`

Repair the source-span or candidate-evidence seam.

Do not compensate with broader corpus access.

### When the verdict is `BLOCKED_BY_CONTRACT`

Write a contract decision before coding.

Do not add unreviewed temporal fields inside the model-output adapter.

### When the verdict is `PROVIDER_FAILURE`

Treat provider availability or compatibility as the next dependency.

Do not replace the real proof with a fake-client result.

---

## §31 Final directive

Build the experiment that tells us whether temporal extraction is trustworthy.

Do not build the Timeline yet.

The correct progression is:

```text
typed temporal contract
→ shadow overlay
→ evidence-bound real extraction
→ measured cohort result
→ participant roles
→ projected occurrences
→ node timelines
→ product surface
```

Preserve uncertainty.

Bind every temporal interpretation to exact evidence.

Let poor model performance remain visible.

The Timeline project should advance because the evidence supports it, not because the schema now permits it.

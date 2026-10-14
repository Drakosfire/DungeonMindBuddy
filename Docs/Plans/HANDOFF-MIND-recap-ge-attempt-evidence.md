# MIND — persist recap inference attempt evidence

**Status:** ACTIVE — one non-serving Buddy consumer PR authorized
**Owner:** DungeonMindBuddy MIND recap extraction
**Base:** `main@ac46913b596ef76b73bba7a73ec8a76ecd926116`
**Accepted GenerationEngine:** #19 merge `e4b683a459d9f0dfaa2a41d8b073ff6117c3aa6e`
**Topology:** one isolated Buddy PR, parallel-independent of SERVER #1014

## Re-anchor and ownership

Current Buddy main and open PRs were inspected before dispatch. The active
SERVER #1014 preparation touches disjoint paths; it changes no recap extraction
code, dependency files, or this lease. The existing serving source and
GenerationEngine #18 pin remain frozen: this PR may update Buddy's checked-in
package source pin/lock to the reviewed #19 merge for future builds and tests,
but does not install it into, restart, or otherwise mutate any serving runtime.

`HANDOFF-MIND-recap-pass-response-evidence.md` is accepted and complete at PR
#1129. `HANDOFF-MIND-recap-json-output-reliability.md` still says ACTIVE despite
its accepted PR #1133 merge at `72c2987f4f757cfe2be91b89c0229814392a0a1a`; the
new implementation PR must settle that predecessor handoff with its accepted
head/review/merge facts before this slice is considered complete.

The current `BoundedRecapPassClient` uses `generate_text()` for both provider
routes. DeepSeek requests `json_object=True` and applies the existing pass schema
only after the worker returns; OpenAI sends the pass schema through ordinary
text generation. The parent writes one final per-pass private envelope after
the worker receipt arrives. Therefore an initial invalid response can be lost
if a later GenerationEngine correction fails or the worker is terminated.

The existing private response writer and caller-provided
`response_artifact_dir`/context hashes are the sole evidence sink. Do not add a
second persistence framework or alter app/public graph artifacts.

## Objective

Use the accepted GenerationEngine #19 `generate_structured()` attempt hook for
the existing pass schema (`format.schema` and `format.name`) inside the owned
worker. When the private sink is configured, persist each completed response
from `on_attempt_completed` to the caller's context-bound private run directory
before GE parses, validates, refuses, or dispatches its one structural
correction. This must preserve the initial invalid response even if the
correction later fails or the worker is terminated.

Keep the ordinary final response/schema validation as a defense-in-depth
consumer check. A returned final observation or typed failure must preserve
actual GE accounting, including provider attempts, transport retries,
conformance retries, failure code, and nullable usage. The in-memory ledger may
contain safe event identifiers/ordinals/status, paths, digests and safe
observations, never response text or prompts.

For an incomplete or refused provider response, capture the GE event as
provided. Preserve `None` where source text or usage is unavailable; do not
describe missing text as an empty response. A transport attempt with no
completed response creates no response artifact, but its known attempt counts
remain in the GE observation. If the worker dies without a receipt, retain any
already-written attempt artifacts for inspection, classify the remaining
external outcome as unknown, and never replay or redispatch.

## Exact write lease

Only these paths may change:

1. `Docs/Plans/HANDOFF-MIND-recap-ge-attempt-evidence.md` (this pinned handoff)
2. `Docs/Plans/HANDOFF-MIND-recap-json-output-reliability.md` (settle accepted #1133 predecessor)
3. `src/graph_memory/extraction/bounded_recap_execution.py`
4. `src/graph_memory/extraction/_recap_inference_worker.py` (the hook executes in the spawned child)
5. `tests/test_bounded_recap_execution.py`
6. `tests/test_recap_inference_worker.py`
7. `pyproject.toml` (pin GenerationEngine source to accepted #19 merge)
8. `uv.lock` (corresponding exact lock update only)

No changes to other application/server/UI code, schemas, prompts beyond the
existing JSON instruction, fixtures containing real corpus/model output,
source artifacts, database/migrations, serving environments, providers, or
runtime processes. Any additional path requires returning to the steward before
editing.

## Required behavior and invariants

- At the existing pass boundary, use the already-selected pass JSON Schema; do
  not invent a permissive/placeholder schema. Call `generate_structured()` for
  both configured providers and pass the existing awaited attempt callback when
  the private evidence sink is configured.
- Keep the existing DeepSeek-only route (`DeepSeek`, no fallback,
  `require_parameters=True`), temperature/reasoning behavior, output limits,
  deadlines, outer pass ceiling and `max_transport_retries=0`. No transport
  retry or provider fallback is introduced.
- The technical one-correction behavior remains GE's existing conformance
  policy; it is not a new operator authorization ceiling or an outer pass.
  Initial invalid and corrected responses are distinct attempt evidence. Every
  actual provider invocation is accounted for, including no-response
  transport failures in the final observation when one exists.
- Each private per-attempt artifact is durably written outside the worker's
  `TemporaryDirectory`, under the caller's private run directory, using the
  existing restrictive permissions, request/prompt hashes, context hashes,
  no-overwrite publication and safe metadata conventions. Use unique pass plus
  GE event ordinals so a correction cannot overwrite the initial response.
- A sink write failure is terminal: GE's distinct
  `ATTEMPT_EVIDENCE_PERSISTENCE_FAILED` must stop before a correction/follow-up;
  Buddy marks the pass stopped, preserves the known failure observation and any
  earlier successful artifacts, and never retries or replays it.
- Inventory durable attempt files into the safe execution ledger after worker
  completion, failure, or termination. Include the actual ordinal gaps (for
  example, response events at 1 and 3 when attempt 2 returned no response) and
  safe event IDs/status/path/digest. Do not fabricate an event for attempt 2.
- Preserve exact source-fidelity labels and promotion hold. Valid JSON or schema
  conformance does not establish semantic correctness, source coverage, or
  attribution. No semantic-gold/corpus inputs, candidate promotion, ingestion,
  publication, or provider call are authorized.

## Acceptance proof

Focused fake-only owning-boundary tests must prove:

- invalid initial response → valid single GE correction, with each response
  persisted before validation/follow-up and exact attempt counts;
- invalid initial response → final invalid corrected response, preserving both
  artifacts and the final `STRUCTURED_OUTPUT_INVALID` observation;
- a correction transport failure with `max_transport_retries=0`, no response
  artifact for that attempt, no fallback/replay, and actual observation counts;
- sink failure aborts before correction and is not replayed;
- worker termination while a correction is pending leaves the first response
  artifact durable outside worker temporary storage, marks unresolved outcome
  unknown, and does not redispatch;
- nullable usage, refusal/incomplete status and source-text unknowns remain
  truthful; no response text enters the ledger.

Run only the focused owning test files, Ruff on changed Python files,
`uv lock --check`, and `git diff --check`. Inspect the exact cumulative base to
head diff and confirm this write lease. Commit/push/open one Buddy PR and request
the assigned independent PRIME review at the exact head. Do not merge or perform
any live/provider/runtime action as part of this handoff.

This handoff stays ACTIVE until exact-head review accepts the consumer slice.

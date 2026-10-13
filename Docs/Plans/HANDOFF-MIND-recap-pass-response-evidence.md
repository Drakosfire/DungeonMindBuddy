# MIND — preserve recap pass responses as private evidence

Status: ACTIVE under PRIME implementation approval, 2026-10-13.

## Lane and authority

- Owner: DungeonMindBuddy MIND recap extraction. GenerationEngine remains the
  inference and provider-IO owner.
- Remote base: Buddy `main` at
  `a1f8bdfdbc692f02879c3b68f58936838e902d21` (merged PR #1128).
- Branch: `codex/mind-recap-pass-response-evidence`.
- Checkout: `/tmp/buddy-recap-response-evidence`, a clean, non-serving clone
  pinned to the verified remote-main SHA above.
- Topology: serial, one implementation PR. The previous recap wall-clock lease
  is settled by merged #1128. No open PR or branch was found leasing these
  paths at dispatch.
- PRIME explicitly approved this bounded implementation after R5 established
  that six successfully returned pass bodies were lost when a later pass failed.
- Exact write allowlist:
  - `Docs/Plans/HANDOFF-MIND-recap-pass-response-evidence.md`
  - `src/graph_memory/extraction/bounded_recap_execution.py`
  - `tests/test_bounded_recap_execution.py`
- Any additional source/test path requires returning to PRIME before editing.

## Objective

For a caller that opts into a private response-evidence sink, preserve every
completed GenerationEngine text response and a safe receipt before local
conformance, JSON, schema, or application-consumer validation. Earlier
responses must remain available if a later pass fails. These files are local
review evidence/golden data, not approved graph facts.

R5 evidence motivating this slice is preserved outside the repository at
`/tmp/c1s16-ge-deepseek-reconciled-r5-result.json` and
`/tmp/c1s16-fresh-artifacts-20261012/out/c1s16-ge-deepseek-reconciled-r5/`.
The exact R5 result/ledger/raw response remain unchanged. R5's six earlier raw
pass responses are absent and cannot be recovered by this change; do not claim
that this implementation repairs or replays that run.

## Required behavior

- Add only optional private sink/context inputs to the internal
  `BoundedRecapPassClient`; callers that omit them retain current behavior.
- Persist one private per-pass envelope containing:
  - explicit capture state `unvalidated_snapshot`;
  - pass ordinal and pass name;
  - SHA-256 of the canonical serialized actual GenerationEngine request and
    separate hashes of its exact system and user prompt strings (never store
    prompt text in metadata);
  - caller-supplied source/context hash map;
  - allowlisted request facts (provider/model/route, retries, deadline, and
    output limit);
  - allowlisted safe GE observation fields, including state/model/attempts,
    token and cost/null-usage fields, latency, pricing source, and response ID;
  - exact raw response text, UTF-8 byte length, and response SHA-256.
- Capture the typed GE result before local response conformance/JSON/schema
  validation. The snapshot must say it is unvalidated and must not imply
  candidate validity or semantic acceptance.
- Missing worker receipt remains `unknown` and creates no fabricated response
  artifact. A known completed response remains known even if cleanup or later
  consumer validation fails.
- Write under a private run-local directory, outside the Graph manifest's
  public artifact references and candidate graph. Use restrictive directory
  and file permissions, same-directory staging, flush/fsync, atomic
  no-overwrite publication, and fail closed on collision or write failure.
- Record only the private artifact path and SHA-256 in the in-memory execution
  ledger. Never put prompts, raw output, credentials, headers, or arbitrary
  exception text in the ledger.
- If a later pass fails, all earlier successfully written response envelopes
  remain intact. Do not add cache/replay/resume authority; a later explicitly
  reviewed caller may consume reviewed saved pass data through existing test
  adapters.

## Non-goals and hard boundaries

- No public Graph/APP contract or manifest/artifact-reference change.
- No automatic cache, retry, replay, resume framework, pagination, or changes
  to provider/model/dependency policy.
- No change to publication, runtime behavior, durable state, corpus, registry,
  or database.
- No provider calls, full rerun, or publication in this slice.
- Do not treat the prompt's rough 10–30 edge expectation as a hard truth ceiling
  or the malformed R5 prefix as semantically correct/incorrect without
  source-fidelity review. Preserve all required durable IDs and source fields.
- The current 8,192 output limit is an application product setting, not an
  operator authorization ceiling or an immutable model limit. Any later output
  allowance experiment is separate and must retain bounded review/authority.

## Verification and delivery

Add focused tests in `tests/test_bounded_recap_execution.py` covering successful
capture; malformed JSON and schema-invalid responses captured before failure;
earlier artifacts retained across a later-pass failure; private permissions,
no-overwrite and atomic visibility; prompt/secret privacy in the envelope and
ledger; and missing worker receipt classified unknown without a response
artifact. Keep tests offline and within this module's fake-worker seam.

Run the focused owning-boundary test file, Ruff on the changed Python paths,
and `git diff --check`. Inspect the exact cumulative base-to-head diff and
confirm the three-path allowlist. Commit, push, open one PR, and request an
independent review from PRIME against the exact head. Do not merge or run
ingestion as part of this handoff.

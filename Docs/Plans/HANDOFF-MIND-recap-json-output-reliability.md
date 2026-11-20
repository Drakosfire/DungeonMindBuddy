# MIND — bounded recap JSON output reliability

**Status:** COMPLETE — accepted and merged as PR #1133; superseded by the
per-attempt evidence handoff for the follow-on GenerationEngine #19 consumer.
**Buddy base:** `2dcd5b40f28757f8b398ad0a3ffcaf248db51bf0` (main after #1131)
**Accepted GenerationEngine pin:** `e8f0fec98eef1a7c1a7fc0bb0b7d867420306929` (#18)
**Topology:** serial; one Buddy consumer PR after the accepted GenerationEngine prerequisite.

## Contract ownership

Buddy chooses JSON-mode support requirements for its extraction request.
GenerationEngine owns OpenRouter route translation and provider I/O. The
accepted `ProviderRoute.require_parameters=True` asks OpenRouter to filter
route endpoints that cannot support all requested parameters. It does not
guarantee syntactically valid JSON, semantic correctness, or source fidelity,
and it is not evidence that endpoint filtering caused the R6 malformed output.

## Objective

Make one bounded, local Buddy consumer request explicitly ask for JSON-mode
endpoint support, clearly instruct the model to emit one complete JSON object,
and report a known completed response rejected by Buddy as a consumer validation
failure. Preserve unknown external outcomes when the worker has no receipt.
Keep malformed output invalid. Do not salvage, repair, replay, or resume it.

## R6 evidence and disposition

R6 is stopped. Four DeepSeek calls (actor, location, collective, object)
returned; the object response was known completed but invalid JSON. It used 719
output tokens against an 8,192-token request, so token exhaustion is not
supported by the evidence. The malformed response's exact private bytes,
attempts, result, and full source-fidelity review remain local and immutable.
The original response SHA-256 is
`794bd770b3c324d2530e9f662ce12d747dfc08c49c68e8ee0268d13fe443a649` (2,557
UTF-8 bytes); its envelope hash is
`0d6c7143fcd7c615f4de90caf756c4bebb84b1f2e6e0c2e937358b357ceda819`.
Do not commit the response or corpus-bearing per-node labels. The local private
handback records the known-completed-invalid disposition and semantic review.

Three earlier responses parsed and supplied 47 exact source quotes across 19
nodes, but quote fidelity is not semantic acceptance. The private audit found
at least one source-contradictory attribution and additional unresolved
identity, grouping, timing, and spatial claims. No candidate graph was created;
no edge pass, retry, follow-up call, or publication occurred. No part of R6 may
be reused by this slice.

## Exact write lease

Only these seven repository paths may change:

1. `Docs/Plans/HANDOFF-MIND-recap-json-output-reliability.md`
2. `src/graph_memory/extraction/bounded_recap_execution.py`
3. `tests/test_bounded_recap_execution.py`
4. `tests/fixtures/graph_memory/recap_json_output/r6-object-invalid.txt` — synthetic, corpus-free shape only
5. `tests/fixtures/graph_memory/recap_json_output/r6-response-classification-labels.json` — corpus-free labels only
6. `pyproject.toml`
7. `uv.lock`

The dependency-file lease is held by this serial Buddy consumer after GE #18
merged; #1132's current files are disjoint. Do not edit the settled edge-budget
handoff unless a required durable contract correction is discovered. Do not
touch live source/runtime state, provider credentials, output/corpus files, or
the immutable R6 artifacts.

## Implementation and proof obligations

- Pin GE exactly to the accepted merge `e8f0fec98eef1a7c1a7fc0bb0b7d867420306929` in `pyproject.toml` and `uv.lock`; make no unrelated dependency changes.
- Set `ProviderRoute.require_parameters=True` only for the bounded DeepSeek JSON request; include it in safe request ledger facts.
- In the existing product prompt, request one complete JSON object, no Markdown or surrounding prose, correct escaping, and closed strings/containers. This is an instruction, not a guarantee.
- Keep the current DeepSeek-only route, no fallback, zero retries, eight-call ceiling, 60-second per-call and 480-second run deadlines, and token ceilings (8,192 general; 16,384 only for the actual typed edge pass).
- At the actual offline boundary, prove `TextRequest` → accepted GenerationEngine `TextGenerationCall` → OpenRouter SDK kwargs includes `response_format={"type":"json_object"}` and `provider.require_parameters=true`, with route order/fallback unchanged. Prove false/default routes omit the new wire field.
- A completed result rejected by JSON parsing records external outcome `completed` and consumer outcome `invalid_json`. Record parse position, line, column, text lengths, and SHA-256 only; never put response text in the public ledger.
- A missing worker receipt remains external outcome `unknown`; do not fabricate completion, a private response artifact, or a candidate.
- Use a synthetic malformed JSON fixture only. The corpus-free labels must explicitly preserve `candidate_promotion=false`, `automatic_salvage=false`, and `replay_authorized=false`.
- The malformed fixture remains invalid and is retained in the private response sink before local validation when that sink is configured. Stop after this consumer failure; make no next call.
- Preserve source-fidelity limits: no label or prompt may claim that valid JSON proves semantic correctness, complete source coverage, or fixed attribution.

## Verification and delivery

Run the focused owning test file, changed-file Ruff, lock consistency, and
`git diff --check`. Inspect the complete base-to-head diff and exact seven-path
allowlist. Commit, push, open one Buddy PR, and request PRIME review on the exact
head. No provider/runtime/publication call is part of this handoff. Merge remains
separate authority.

## Completion record

Disposition: `MIND_RECAP_JSON_OUTPUT_RELIABILITY_ACCEPTED`

- PR: [#1133](https://github.com/Drakosfire/DungeonMindBuddy/pull/1133)
- Exact reviewed head: `08765df702b253532f76fab6c5fecb76ce2a39c9`
- PRIME review: PASS, exact-head review recorded in PR comment `6157599433`
- Merge commit: `72c2987f4f757cfe2be91b89c0229814392a0a1a`
- Merged: 2026-10-13
- Owning focused tests: 40 passed; Ruff, lock consistency, and diff check passed.
- No provider, ingestion, serving/runtime, candidate publication, retry,
  replay, or salvage operation was performed.

This handoff is closed. The next consumer slice uses the accepted GenerationEngine
#19 pin and preserves the JSON reliability behavior while adding durable
per-attempt response evidence.

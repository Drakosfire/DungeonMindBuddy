# HANDOFF — SERVER: safe Plan Graph answer-validation diagnostics

**Status:** ACTIVE — PRIME authorized this bounded source slice on 2026-10-06. Independent APP-STATE/PRIME review is required before merge; no runtime rollout is authorized.
**Owner:** DungeonMindBuddy SERVER.
**Base:** fetched Buddy `origin/main@a92371b7b2e727d1d45bef1c8e1d7a3d01b58193`, including merged #980.
**Branch/topology:** `codex/server-graph-answer-validation-diagnostics`, serial independent draft PR against `main`. #980 managed-World target binding merged from reviewed head `7010dba072407bcee76db91b0f815689f3266646` at `a92371b7b2e727d1d45bef1c8e1d7a3d01b58193` and has no runtime rollout authority.
**Collision check:** #917 has an older preserved prototype touching `agent_turn_service.py`, with no active reservation per the accepted SERVER route handoff. Current open #922 is handoff-only. No other open PR leases the diagnostic test paths; re-check before review.

## Primary question

When a provider response is durably acknowledged but its Plan/Graph answer is rejected, can SERVER report a fixed safe rejection stage/reason tied to the client turn, durable turn, and producing attempt without storing or logging user/provider content or changing admission?

The concrete production incident is client turn `632ed737-d3a9-4ca3-b6df-a612ebcb4613`, conversation `4dfb51ed-38dd-49bc-b17a-204c643aea12`. SERVER's UUID5 idempotency derivation maps that client turn to persisted key `dfef1ba3-1c10-5cf4-9afa-819c2ba9674c`; the durable row is `f884e07f-77c9-4d09-b88c-7efa686d0406`. It failed with `answer_validation_failed` after two `response_received` events and one validated Graph expansion, without a completion binding. The current parser folds JSON, typed schema, citation, and evidence failures into the same public code and does not retain a safe subtype. Raw final text is intentionally not durable.

## Exclusive implementation lease

- This handoff.
- `Docs/Plans/HANDOFF-SERVER-managed-world-publication-target-binding.md` — backward-looking settlement of PRIME's now-merged predecessor only, as explicitly requested; no new target behavior.
- `apps/live_control_server/services/agent_turn_service.py` — classify answer admission failures into fixed safe stage/reason values; emit one bounded diagnostic with client turn/request correlation, durable turn ID, producing attempt ID, final-text SHA-256 and UTF-8 byte length. Keep the existing public `answer_validation_failed` and fail-closed behavior.
- `tests/test_agent_turn_service.py` — deterministic final-text fixtures and valid two-attempt Graph expansion at the owning service boundary.
- `tests/test_agent_turn_route.py` only if an actual HTTP witness is required to prove no content leakage or unchanged public 502 contract.

Do not change APP-STATE schema/contracts, provider/Hermes execution, retries, request dispatch, output parser acceptance, Graph evidence policy, product UI, production runtime, or the historical failed turn. Do not log raw final text, prompt, user content, evidence body, exception string, or provider body. If behavior repair or a different path is needed, stop and return a concrete finding to PRIME as a separate scope decision.

## Acceptance witness

- Fixed diagnostic categories distinguish malformed JSON, top-level shape, typed segment/citation rejection, producing-envelope support, and final completion binding. The classification must be deterministic; unknown exceptions stay a safe `unknown` category.
- Each rejection still raises the existing public failure code and results in no typed completion and no additional provider attempt. The diagnostic contains only allowlisted IDs, a fixed stage/reason, digest, and byte length; tests prove it excludes raw text and validation exception messages.
- A valid two-attempt expansion still binds the final Graph claim to the second producing envelope and completes normally, with no rejection diagnostic.
- Run focused owning tests and relevant repository checks; inspect the exact cumulative base-to-head diff; update this handoff with implementation head, results, and any limits before requesting independent review.

**Acceptance token:** `SERVER_GRAPH_ANSWER_VALIDATION_DIAGNOSTICS_ACCEPTED` — PRIME/APP-STATE may grant it only after exact-head review.

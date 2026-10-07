# HANDOFF — SERVER: safe Plan Graph answer-validation diagnostics

**Status:** MERGED — Buddy PR #981 merged at `87308f996289e5c3fde5c82d29c24a6203b95302` from APP-STATE/PRIME accepted source head `09e579d55384b3322ff7f54dbd3503b4e915598d`. Runtime rollout remains separate and is not authorized by this merge.
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

**Accepted token:** `SERVER_GRAPH_ANSWER_VALIDATION_DIAGNOSTICS_ACCEPTED` — PRIME and APP-STATE accepted exact head `09e579d55384b3322ff7f54dbd3503b4e915598d` before merge. This source acceptance does not authorize runtime rollout.

## Implementation handback — 2026-10-06

**Source implementation commit:** `86ea2cba6776a522fa41a0197404dc010bb02639`; final PR head also includes this evidence update. Base remains `a92371b7b2e727d1d45bef1c8e1d7a3d01b58193`.

- SERVER wraps the existing fail-closed parser errors with fixed stage/reason values and emits one safe warning on answer rejection. It records the request turn's SHA-256 (the untrusted client turn string is not logged), durable idempotency key, durable turn UUID, producing provider attempt UUID, final-text SHA-256, and UTF-8 byte count. The public code/status and admission rules are unchanged.
- Deterministic fixtures cover malformed JSON, top-level and segment shapes, typed segment/citation failures, missing producing attempt, unsupported Graph claim in the producing envelope, and completion-binding rejection. A fresh two-attempt Graph expansion admits a cited claim through the owning completion boundary and records its final binding. The service-boundary rejection witness proves one provider authorization, no typed completion, unchanged failure code, and no raw final text or validation exception in its diagnostic.
- `tests/test_agent_turn_service.py -k 'not history_http'`: 49 passed, 2 deselected. The two `history_http` tests were excluded because the local AnyIO/FastAPI worker-pool harness stalled at `test_history_http_opt_in_uses_persisted_key_not_durable_turn_id` after 18 preceding passes; the run was interrupted without a test assertion failure.
- `tests/test_agent_turn_route.py -k 'policy_predispatch_failure or policy_unproven_or_unmapped_failure'`: 4 passed. A broader sandboxed route selection produced those 4 passes and a PostgreSQL fixture setup error for `test_policy_resolver_reads_real_pinned_native_graph_with_distinct_managed_id`; the sandbox cannot reach the host's disposable PostgreSQL. The same test passed (1 passed, 16.63 seconds) when rerun with host access against the repository's uniquely named, created-and-dropped test database. No route file changed.
- Focused Ruff and Python compilation passed; `git diff --check` passed. The cumulative base-to-source-commit diff is limited to this handoff, the predecessor handoff's merged-status settlement, the SERVER parser/logging code, and its owning service test.

No deterministic prompt/schema mismatch was established from the checked-in prompt and typed completion contract. The original production answer body was intentionally not persisted, so this source-only change cannot identify its exact rejection reason retroactively. At handback time, independent exact-head review and any later diagnostics-only rollout remained with PRIME; this handoff had not yet granted the acceptance token. The later review and merge are recorded below.

### PRIME review correction — 2026-10-06

PRIME found that the parser could retain `typed/segment_attribution` from an earlier Plan or Graph segment when a later array element was not an object. Source correction `7976177416138dcba3b7480c222fd069f8be2df4` resets the stage to `shape/segment_shape` at each loop iteration before the object check. Mixed Plan-first and Graph-first fixtures now prove the later non-object receives the shape category, still raises `answer_validation_failed`, and exposes no private fixture content. The owning service suite passed again: 49 passed, 2 unrelated history HTTP tests deselected. Focused Ruff, Python compilation, and `git diff --check` passed. The prior handback's source commit documents the original implementation; this correction is part of the reviewable cumulative PR diff. Acceptance remains with PRIME's next exact-head review.

### APP-STATE review correction — 2026-10-06

APP-STATE found that strict UTF-8 encoding in the rejection logger could itself fail on an unpaired surrogate in an arbitrary provider string, bypassing the normal `answer_validation_failed`/`fail_turn` path. Source correction `0c9b09a6aaaecc1bc8e874ef81b74407c566a70a` uses UTF-8 with `surrogatepass` for diagnostic hash/byte length and request-turn hash. Ordinary valid-UTF-8 digests remain identical. A service-boundary fixture with an actual unpaired surrogate proves one failure recording, one provider authorization, no completion, the same 502 code, and content-free log fields. The owning service suite passed again: 49 passed, 2 unrelated history HTTP tests deselected. Focused Ruff, Python compilation, and diff check passed. At the time of this correction, no runtime rollout or acceptance token was claimed; the subsequent acceptance and merge are recorded below.


## Merge settlement

Buddy PR #981 merged at `87308f996289e5c3fde5c82d29c24a6203b95302` from accepted source head `09e579d55384b3322ff7f54dbd3503b4e915598d`. PRIME and APP-STATE accepted `SERVER_GRAPH_ANSWER_VALIDATION_DIAGNOSTICS_ACCEPTED` for that exact head. PRIME reported its owning service rerun passed 49 tests with 2 unrelated history HTTP tests deselected. The focused route and host-backed PostgreSQL evidence above are author-reported; APP-STATE did not rerun tests. No GitHub status checks were present at review. This does not establish full-suite coverage.

The historical failed Ask remains failed. It was not replayed, and no provider call or runtime rollout is authorized by this merge. PRIME directed a separate SERVER diagnostics-only portable-candidate/handoff that preserves the current UI code `0456354f884e1f5667fdce6e11abd6f7be52aac7` and backend/runtime `521a63518a1dd0188b76244c5382d8fb897878d4`, and excludes #980 publication-target changes until DEMO callers are ready. That follow-on is pinned as the BLOCKED proposal in Buddy PR #982 at head `6c2434249f0c477338c18fa20fd01461d2ee1240`, in `Docs/Plans/HANDOFF-SERVER-graph-answer-diagnostics-only-rollout.md`; it is not activated, and Root retains review/activation.

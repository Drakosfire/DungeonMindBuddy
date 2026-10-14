# MIND — bounded logical deadline for C1S16 evidence

Status: SETTLED — PRIME independently reviewed and merged PR #1136. The
120-second logical GenerationEngine operation is implemented; no R6 execution is claimed.

## Lane and authority

- Owner: DungeonMindBuddy MIND recap extraction. GenerationEngine remains the
  exclusive inference/provider-IO owner.
- Verified Buddy remote base: `main@f2964c12e82c149c3d69a9798626a90164303707`.
- Branch: `codex/mind-recap-logical-deadline-120s`.
- Checkout: `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/c1s16-r6-prep-20261013/implementation`,
  fresh, clean, and non-serving at the verified base.
- Topology: serial, one capability PR. No open PR was found leasing the bounded
  recap execution source or its focused tests.
- Exact write allowlist:
  - `Docs/Plans/HANDOFF-MIND-c1s16-edge-output-budget-v1.md`
  - `src/graph_memory/extraction/bounded_recap_execution.py`
  - `tests/test_bounded_recap_execution.py`
- No additional file or checkout/runtime state is in this lease.

## Accepted predecessor and reason for this slice

PR #1129's response-evidence capability passed PRIME review at exact head
`60f536b8051ed54c6a6b8d8a29afa311fd5604b3`, base
`a1f8bdfdbc692f02879c3b68f58936838e902d21`, and merged as
`597c69b1ca5449947894311af83756812b2318fe`. It adds an opt-in private sink;
any future real extraction must supply that sink and its complete source/context
hash map. The predecessor is already merged and settled on the current main.

R5's `edge_pass` requested and returned exactly 8,192 output tokens and failed
JSON parsing at the response tail. The original R5 authority, result, raw
response, ledger, and manifest remain preserved and unchanged. Six successful
R5 pass bodies were not persisted, so R6 must be a fresh full extraction; this
PR cannot resume or recover those responses. The R5 partial edge prefix is not
a candidate and provides no semantic judgment about its edge count.

## Capability and implementation contract

Permit/select a `per_call_deadline_ms` of 120,000 for each logical
GenerationEngine operation. GenerationEngine owns the initial attempt plus at
most one conformance correction under that single deadline. This is not two
separate 120-second attempts and does not change transport retry policy. The
existing edge-only output allowance and all other output policy remain
unchanged: only a typed edge pass can receive the configured 16,384-token cap;
non-edge requests remain at 8,192 tokens.

- Keep max calls 8, total run deadline 480,000 ms, transport retries 0,
  DeepSeek-only route, and no fallback unchanged. Each request's selected
  deadline is `min(120,000 ms, remaining whole-run budget)`.
- Keep all required edge schema fields, durable IDs, endpoint bindings, and
  source/evidence fields unchanged. Do not add an edge-count ceiling or claim
  that the rough prompt guidance is a truth cap.

The focused tests must prove 120,000 ms reaches both `TextRequest.deadline_ms`
and the owned worker's parent deadline when budget allows; a shortened remaining
run budget clips both; and the 480,000 ms whole-run ceiling is unchanged. Retain
the existing edge output, zero transport retries, and DeepSeek-only/no-fallback
assertions. Do not replay the broad suite; run only this owning test file, Ruff
on the two Python paths, and `git diff --check`.

## Separate experiment authority

The historical R6 proposal and its old temporary input pins are preserved in
Git history at `f2964c12e82c149c3d69a9798626a90164303707`; they are not current
launch authority. Any fresh experiment must pin its reviewed current source,
input derivatives, context, evaluator separation and durable evidence sink.
Eight logical pass invocations are distinct from actual provider attempts and
from operator authorization. No provider execution is authorized by this lease.

## Delivery boundary

Commit this ACTIVE handoff before source/test changes. Implement only the
three-path allowlist above. Push and open one PR, then request PRIME's independent
review on the exact head. Merge remains separate authority. Do not run R6 in
this PR; no provider call, serving, or publication is authorized here.

## Acceptance and solo takeover

PR #1136 reviewed at `3777011ff8f1c860c53e77640c0013d4938fe0c4`, merged at
`f6a4990c10fc28d79642fe1a963727ca25e6f6e1`. PRIME personally inspected the
three-path change and independently ran six targeted logical-deadline,
remaining-budget and unknown-receipt cases: passed in 0.29 seconds.
[Acceptance record](https://github.com/Drakosfire/DungeonMindBuddy/pull/1136#issuecomment-6159156441).
MIND authored this implementation before the solo phase. Further execution is
PRIME-only under the operator's foundational-work instruction; no agents are
dispatched by this handoff. No serving, provider or publication result is claimed.

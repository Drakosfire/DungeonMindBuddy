# MIND — bounded edge-pass output allowance for C1S16 evidence

Status: ACTIVE under PRIME approval, 2026-10-13. This bounded PR permits a
120-second logical GenerationEngine operation; it does not execute R6.

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
hash map. This PR records the predecessor COMPLETE in the same necessary change,
not in a separate bookkeeping PR.

R5's `edge_pass` requested and returned exactly 8,192 output tokens and failed
JSON parsing at the response tail. The original R5 authority, result, raw
response, ledger, and manifest remain preserved and unchanged. Six successful
R5 pass bodies were not persisted, so R6 must be a fresh full extraction; this
PR cannot resume or recover those responses. The R5 partial edge prefix is not
a candidate and provides no semantic judgment about its edge count.

## Capability and implementation contract

Preserve the existing edge-only output allowance and permit/select a
`per_call_deadline_ms` of 120,000 for each logical GenerationEngine operation.
GenerationEngine owns the initial attempt plus at most one conformance
correction under that single deadline. This is not two separate 120-second
attempts and does not change transport retry policy.

- `None` preserves current behavior exactly.
- An explicit value must be a strict Python `int` (not `bool`) in `1..16384`.
- Keep the existing general `max_output_tokens` field and its `1..8192`
  validation unchanged.
- Apply the override only when the actual supplied `pass_spec.kind == "edge"`.
  Do not infer edge-ness from a string pass name.
- All non-edge requests continue using `max_output_tokens` (8,192 in R6).
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

## R6 candidate-only experiment proposal (not released in this PR)

After this capability is reviewed and merged, prepare one fresh, one-shot R6
runner/proof/authority/output bundle pinned to the accepted code source. Keep
the same `longmont-c1/session-16`, settled identity `pc:karsemine`, source
artifact `artifact:recap:longmont-c1:session-16:d44898920ee0`, and exact input
hashes:

- Raw recap: `e8b8399abc94ba38daa3151d68b550f0ebc1c90e7a9181552ac71aecb098c161`
- Normalized recap: `d44898920ee091ec32ca23fdfd07c83b4abaa452042ce4d70f45c3ab114b2330`
- Source-span index: `e7c742f7578ecd40d497e11339b25caf23d55b8db0d8c429c730ae587c50a81b`
- Context files: the exact eight-file hash map in preserved R5 authority
  `ff1c6cf7b1cbeb8e05bc35d70a3e4b01938e570b9205f65abf7ec12f64df09d1`:
  `PCs/baergrom/README.md` `cdf8ffa035f87cdc11decb3022d0e017f9e456ec1d959991dd0d218a4f3fe13e`;
  `PCs/bonogo/README.md` `782c80e1fae8b7eb8457b9622cdebca6de15db0eaa2a48fe97cc580d92113055`;
  `PCs/caelynn/README.md` `be74152335feb56acf12cb69948826eef0b4a8c252a149397d4f5532f3bfb538`;
  `PCs/ephanna/README.md` `9655dd9cc665b87088760b4c93fe51641306753efec7daf117f647f068f1d873`;
  `PCs/karsemine/README.md` `9bf826045d6a58ff20a1d6af10a91c66053a4f366cdc453cac061092dd2474db`;
  `PCs/stafl/README.md` `ee0bf3393fd1e3848e4cf7ce92ec7f3f5662688672095a36b0b4aa7483e5d953`;
  `_npc_registry.json` `9bbac67da3d9978ad88b7923e6c3629e2023f47861447063625250beec567b88`;
  `_party_registry.json` `f0f49045df06f7baf61aa9c43f3739d16483eeb20ac8ed1bbf29f8209474af25`.

Use OpenRouter `deepseek/deepseek-v4.1-flash`, DeepSeek route only, no fallback,
zero retries, max 8 calls, 120 seconds per logical pass (initial attempt plus
one correction), 480 seconds total; request 8,192
output tokens on non-edge passes and 16,384 only on the typed edge pass. The
whole-run deadline clips each logical pass; timeout/unknown stops without replay.
Supply the #1129 private response sink and the exact hashes above to the client.
Use a fresh output path (proposed
`out/c1s16-ge-deepseek-reconciled-r6`); never overwrite R5. The run remains
candidate-only: no manifest/public artifact exposure, native publication, World
write, or runtime upgrade. No provider call is authorized by this code PR.

The full fresh run is required because R5's six successful pass bodies are
missing. If R6 later fails, retain all already-returned pass responses privately
before validation; future manual reuse requires a separate source-fidelity and
identity review. No automatic resume/replay is introduced. Review every edge
against exact source spans and listed durable endpoint IDs. Do not claim semantic
quality from schema validity alone, and do not impose a cardinality cap.

## Delivery boundary

Commit this ACTIVE handoff before source/test changes. Implement only the
three-path allowlist above. Push and open one PR, then request PRIME's independent
review on the exact head. Merge remains separate authority. Do not run R6 in
this PR; no provider call, serving, or publication is authorized here.

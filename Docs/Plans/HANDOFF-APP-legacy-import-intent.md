# APP: preserve explicit intent absence in verified legacy import

**Status:** SETTLED — #2294 merged `0d0f5af3418ae3327a4760376ba1f25385626b5d` after root exact-head PASS at `a8b5d8382fc2fca0ded3b4eef796a5d6ffbd6a16` and all8 green hosted checks. Verified on main; no deployment. Historical authority: the coordinator's assignment to investigate and correct
the reproduced exact-base legacy-import failures as part of CI qualification.
**Base revision:** `d39db0c6a2a0493800f82eb77d69e3ef3deb3d4e`
Owner: narrow APP legacy-import successor, executed by the CI worker.
Branch/worktree: `codex/agent-legacy-import-intent`, isolated task-owned checkout.

## Scope, authority and coordination

Topology: parallel-independent from runtime #2291 and CI #2288. No unmerged code
dependency; this product fix is a separate PR2 qualification dependency. Root review
still gates #2291 merge; neither its branch nor its files are edited here.

The newly allocated current-main checkout is d39db0c6 (unrelated #2292 UI changes;
APP source/test bytes are unchanged from the reproduced7abfacc base). No rebase
was performed. Before edits, current main and all open PRs (limit200) were inspected: no open PR
writes the APP repository or conversation-service test module. Supported ownership
is pinned handoffs; no tracked .agents lease registry exists. Historical broad
leases are reconciled in this consuming change: World conversation #822 merged
0e49c4d708d3e16c8068384549adb50e863bf64a; recovery #867 merged
21af97cdc5fe4d10c10032b35c9b26c9ff23ac2b. Native codec #2285 merged
1128c3eb605d69fe93d75da2fe2c3085bb4eae1c and its handoff's Settlement already
explicitly releases the implementation lease. Correct only stale implementation
status headers; broader performance/integration goals are not declared complete.
The coordinator adopts this narrow APP successor; no concurrent writer is found.

CI2 exclusively owns the stale historical migration witness in the existing
conversation-service test module; this lane reads/runs its two original import
cases but does not edit that file. CI2 pauses classification writes while this lane
adds exactly the new owner-test filename to domain-integration classification.
That one-entry append is the explicit classification lease split; no selection or
existing classification/config entry changes. Shared fixture, migration, native
codec, service/API and graph writes remain outside this lease.

## §4 Expected path allowlist

| Path | Purpose |
| --- | --- |
| `src/application_state/agent_conversation/repository.py` | Only insert_legacy_turn's trusted legacy submission producer: explicit absent current intent. |
| `tests/test_agent_legacy_import_intent.py` | Real verified import, stored absence, legacy/fresh replay distinction and strict fresh-writer regression. |
| `ci/test-classification.json` | Add exactly the new owner module to domain-integration. |
| `.github/workflows/agent-legacy-import.yml` | Additive complete owner module plus two unchanged original import cases. |
| `Docs/Plans/HANDOFF-APP-legacy-import-intent.md` | Bounded authority and evidence. |
| `Docs/Plans/HANDOFF-APP-STATE-world-agent-conversation-v1.md` | Factual already-merged implementation settlement only. |
| `Docs/Plans/HANDOFF-APP-STATE-agent-turn-claim-recovery-v1.md` | Factual already-merged implementation settlement only. |
| `Docs/Plans/HANDOFF-RETRIEVAL-repository-native-codec.md` | Align stale header with existing explicit lease-release settlement. |

## Contract and failure cases

Current insert_turn reads submission.submitted_intent_v1 to distinguish typed Play
intent. The existing verified legacy producer omits that attribute and raises
AttributeError before either successful import or injected receipt rollback can be
observed. Correct the producer with explicit None: a verified legacy transcript has
no current submitted intent. Do not use getattr/default fallback in insert_turn,
fabricate a current intent/fingerprint/discriminator, revive an old protocol, or
relax verified-World/import bounds, CAS, idempotence, transactions or schema checks.

Preserve all original test IDs and assertions. New real-PostgreSQL cases prove
answered and unanswered import state, stored None markers, import replay equality,
current-intent replay rejection and refusal of unknown fresh submissions missing
intent metadata. Existing two import tests prove exact-world/conflicting-data and
receipt-failure atomic rollback. The stale historical migration case remains
visible and is repaired separately in CI2 using real pinned templates/clones.

Use exact-owned RAM-only PostgreSQL and random loopback port locally, disposable
CI service and synthetic records only. No provider/runtime, operator database,
live data, production migration/fence, graph merge, deployment or protection edits.
Independent exact-head review and owning/old hosted CI are required; publishing a
draft is authorized, merge needs coordinator disposition. Qualification stays HOLD
until all complete proof and remaining failures are resolved.

## Prepublication evidence

Actual base d39db0c6 reproduces four import failures (new answered/unanswered cases
and the two untouched originals); strict unknown fresh submission already refuses.
Producer-only correction then passes all five cases in5.17s, including atomic
receipt-failure rollback and current-intent replay denial. AST comparison proves
insert_legacy_turn is the only changed repository function; insert_turn and the
entire original95-case service module remain byte/AST unchanged in this lane.
Ruff, workflow syntax/full owning command, inventory and whitespace pass. Owned
RAM-only PostgreSQL containers were removed. Independent exact-head review,
hosted CI and consuming full qualification remain pending; no merge claim.

# RULES: honor the declared uncapped provider budget

**Status:** SETTLED — #2291 merged `d3182d5e7b890722518c1ef2e14a5d56982bbfe3` after root exact-head PASS at `a6923b5421ff7971508055b84c043e1470be63c7` and all8 green hosted checks. Verified on main; no deployment. Historical authorization: the CI coordinator explicitly authorizes the narrowly reproduced
RulesOnlyRuntime.authorize repair as a separately owned/reviewable PR2 dependency.
Owner: Buddy runtime repair lane, executed by the CI worker under that assignment.
**Base revision:** `7abfaccaccf63737a31a52e33c79a0df75e1b873`

## Lane and coordination

Branch `codex/rules-only-uncapped-authorization`, isolated task-owned worktree of the
same name. Topology: parallel-independent from CI #2288 with disjoint writes; this
product fix is a dependency for successful PR2 full qualification. CI source edits
pause while this lane owns the runtime method. Publish a separate draft PR against
main. Merge requires coordinator disposition; no deployment is authorized.

Before edits, fetched current main and checked all open PRs (limit200): none writes
the runtime/test paths below. Supported ownership is pinned repository handoffs;
no tracked .agents lease registry exists. HANDOFF-RULES-runtime-lookup is DELIVERED
by #1506; HANDOFF-AGENT-native-completion-trace-order is DELIVERED by #1528.
Their historical leases are not active competing writers. The coordinator adopts
this narrow successor lease; no transfer from a running implementation is needed.
CI #2288 owns its workflow/contracts/qualification tests and graph #2276 retains
its Surface/canvas paths; neither is edited here.

## Invariant and failure cases

The actual current budget producer declares contextLimitTokens=None and output
reserve0. RulesOnlyRuntime currently compares an integer estimate against None,
denies a valid uncapped envelope and blocks real Plan/Play conversation tests.
Honor that declared provider-owned capacity without substituting a finite cap.
Match existing Hermes request-guard semantics: skip context arithmetic only for
None; zero reserve admits an omitted output cap and rejects retained non-null SDK
caps; finite contexts/reserves retain their explicit limits and validation.

Keep exact model/provider/API identity, request hash/bytes/wire bound, tool/function
capability, claim, lifecycle, native reply capture and durable Rules authority
unchanged. Malformed/foreign/over-budget envelopes still fail before delegation.
No schema, production downgrade fence, provider configuration, retry policy, Graph
admission, shared test-runtime helper or Rules source/capability budget changes.

## §4 Expected path allowlist

| Path | Bounded purpose |
| --- | --- |
| `apps/live_control_server/services/rules_only_runtime.py` | Correct only declared context/output-cap validation. |
| `tests/test_rules_only_parent.py` | Valid uncapped regression, finite-budget boundaries and existing real parent cases; omit obsolete zero SDK cap in the synthetic provider. |
| `.github/workflows/rules-only-runtime.yml` | Additive owning regression CI with disposable PostgreSQL; leave every current gate intact. |
| `Docs/Plans/HANDOFF-RULES-uncapped-authorization.md` | Authority, dependency and actual verification evidence. |

No new test file/classification or shared workflow/manifest lease is needed: new
cases live in the already classified owner test module. The new focused workflow
runs that complete module; it never suppresses any existing PR workflow.

## Verification and owned state

Reproduce the new valid-envelope regression before applying the source fix. Verify
an envelope exceeding a former finite capacity passes when capacity is None;
bounded exact/over context and output cases remain correct, malformed cap aliases,
identity/hash/tool failures remain closed, and actual parent authorization/capture
and persistence/replay cases run. Preserve all original owner case IDs/parameters.

Use uniquely named disposable PostgreSQL with random loopback port and RAM-only
PG data locally; clone-per-test/session template fixtures remain unchanged. Synthetic
provider IO only; no operator database/provider call, profile or live data. CI uses
its own service. Remove only exact-owned containers and retain logs/cleanup proof.
No local production image builds while Docker storage is below its headroom guard.

Require independent exact-head semantic review, focused hosted regression plus old
required CI, and an explicitly labeled PR2/runtime/graph candidate composition to
retain the two originally failing cases and all declared full qualification. Image
proof is separate from full-suite/main readiness. No graph merge, protection change,
deployment or test exclusions/xfails/budget overrides are authorized.

## Implementation evidence before publication

The actual-producer valid-envelope regression fails unchanged production code with
TypeError(int > None) before the source fix; retained runtime-uncapped-red.log.
After the narrow fix all66 owning cases pass in20.11s against exact-owned RAM-only
PostgreSQL with synthetic provider IO. The34 originals retain identical test bodies,
parameter expressions and collected IDs;32 new cases cover actual-producer uncapped
input larger than the former finite capacity, all three SDK cap aliases, bounded
context/output edges, malformed reserves and a cap hidden behind a null alias.
No finite policy substitution is used. The old synthetic provider now omits its
obsolete zero-valued SDK cap when reserve0; finite policy fixtures retain their cap.
Ruff and whitespace pass. This is local observed timing, not hosted performance
proof. Independent exact-head review, hosted CI and consuming PR2 proof are pending.

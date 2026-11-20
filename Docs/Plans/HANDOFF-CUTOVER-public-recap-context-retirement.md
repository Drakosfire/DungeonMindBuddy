# Public legacy recap-context retirement

Status: ACTIVE. Owner MIND. Operator authorizes full optimized Elderwyld vNext
cutover design, implementation, independent review and merge. Serial delivery.

## Current anchor and outcome

Base/main4715f169d28f2fc6cade2f883fba4730b67445e8, actual merged PR4238.
Source7d963474, seal49b378751, reviews5994836165/5994854040. Merge/seal tree
450ed39a10e61c06def8efa3ad275752544db29b. No separate merged execution/deployment.
V10 remains in progress, deployed V11 remains ahead. Core/WK pins unchanged.

Retire public recap-context/v2/index and /read POST authority. Preserve saved
historical related-recap opening through the existing claim-bound graph-evidence
GET for local and hosted clients. No new compatibility API, historical reader,
public contract, dependency, migration, provider or serving deployment.

## Exclusive nine-path lease

1. Docs/Plans/HANDOFF-CUTOVER-public-recap-context-retirement.md
2. Docs/Plans/HANDOFF-CUTOVER-native-body-opener-import-isolation.md
3. apps/live_control_server/routes/world_graph_retrieval.py
4. apps/live-control-ui/src/api/liveApi.ts
5. tests/test_world_graph_retrieval_contract.py
6. tests/test_hosted_native_graph_access.py
7. apps/live-control-ui/src/api/liveApi.test.ts
8. apps/live-control-ui/src/api/liveApi.nativeGraphExplorerAuth.test.ts
9. apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx

Hubble owns route and retrieval-contract test only. MIND owns remaining files.
Aristotle reviews read-only. Rebrief MIND before another path or capability.
Fetched main/open-PR audit:3824 overlaps API/auth/history/hosted tests,3808 hosted,
2405 API/runtime,2298 APItests,2104/2090/2087 APIruntime,1014 historytests. MIND
allocates only current recap function/handler/proof regions; older proposal heads
remain unmodified/unmerged, no adjacent auth/portrait/transport behavior adopted.
Exact head inventory retained in predecessor scratch/next-open-prs.json.

## Behavior and proof obligations

Keep registered POST routes, request models, router GM dependency and query
rejection. Valid admitted requests return typed410 in existing retrieval-error
envelope before classic services/Core/source access. Invalid authenticated
model/query requests remain422; mounted valid-body unauthenticated401/player403.
Preserve FastAPI malformed-JSON precedence rather than claiming auth always first.

Saved coordinates always use existing graph-evidence GET, local and hosted,
with exact World/turn/claim/anchor/continuation. Without saved coordinates, typed
retirement error without lookup. No POST fallback after absence/denial/timeout.
Saved GET fixed12000 page bound matches actual UI; no arbitrary maxChars parity.
Historical readers/brokers remain unchanged and cannot discover fresh authority.
Preserve original revision/source/citation bytes, pagination correspondence,
wrong owner/World/claim/anchor refusal, changed binding and late access denial.
Mismatched pages must not append text; failures stay unavailable. Native search,
object, neighborhood and evidence remain unchanged. Other projection routes/UI
are outside this slice and require later disposition with actual consumers.

Run focused backend/transport/history tests, owning auth/current/native cohorts,
exact-source official hosted frontend and full default-discovered diagnostic at
integrated checkpoint because frontend changes. Keep inherited failures visibly
RED; compare uncertain failures to exact base without rerunning frozen retrieval
baseline. Independent exact source review, docs seal review and short checks precede
merge. Record source SHA/commands/results/isolation/install/resource audit.

## Storage and remaining truth

Reuse existing task worktree and qualified projection-import Python environment,
without sync/mutation. New scratch/cache under task v10-public-recap-context-retirement.
Projects parent verified UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and writable before
allocation. Own disposable test DBs only; record teardown accurately, no arbitrary
client termination/deletion. No manual cleanup authorization implied. Inventory
retained task paths/owners/reasons and cleanup followups at completion.

Inherited fixture debt from4238 remains separate: intentional Build seed missingGM,
historical Play policy literal,0057 downgrade fixture. Exactbase21same failures;
no full qualification waiver. Full default frontend also remains RED/unqualified.
Still false: complete public legacy retirement, full deployed cutover, later-write-safe
rollback and V11 acceptance. Next after this outcome: raw projection/recap-projection
retirement with actual consumers, then remaining Core exports and deployment gates.

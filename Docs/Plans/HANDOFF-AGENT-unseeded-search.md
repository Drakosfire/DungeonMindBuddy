# Agent Harness — honor unseeded discovery searches

Status: ACTIVE. PRIME implements solo; ARCHITECTURE independently reviews.
Base: `1e46adb74e55b5e6b8f21fe537db2dadef3c810a`.
Branch: `codex/agent-unseeded-search`; topology: serial.

## Outcome and evidence

The predecessor private capture is merged. Actual ordinary Build turn
`dd5dc662-7402-469f-b8c1-0c02df04932e` completed but missed cult concerns.
Its retained session operations show two discovery searches with targets[]
automatically inheriting eight preflight nodes (city/locations/Elara/council).
Those seeds fill the bounded result before the searched representatives.
A fresh unseeded diagnostic retrieves the reviewed descriptions. This is request
semantics starvation, not authority to republish or edit graph knowledge.

Honor the existing search cardinality of zero to eight explicit seeds. An empty
search target list must remain empty, regardless of selected/preflight context.
Preserve explicitly supplied search seeds. Keep existing fallback for object,
neighborhood and support. Share target resolution between direct expansion and
parent broker so surfaces cannot disagree. No Core change, new retrieval route,
context reset, bound increase, provider change or automatic query rewrite.

## Exact write lease

- `Docs/Plans/HANDOFF-AGENT-unseeded-search.md`
- `src/graph_memory/interaction/expansion_executor.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/hermes_graph_interaction_tools.py`
- `tests/test_graph_search_seed_resolution.py`

Remote main and completed predecessor/active work inspected; no competing lease.
Non-serving checkout `/tmp/prime-mirathorn-governance-current`. DOGFOOD5202/API8000
untouched. Stable5876/API8002 rollout only after exact independent review.

## Evidence gates

Prove direct and parent native request boundaries retain an empty search seed
list even with eight preflight nodes/selected referents, while explicit seeds,
non-search fallback, frozen scope and cardinality remain unchanged. Deterministic
retained-data comparison must show relevant subjects are discoverable without
implicit seeds; no provider or World writes for that comparison. Inspect full
cumulative diff, commit/push/open one PR, request independent exact-head review.
After accepted merge, repeat ordinary Build conversation and review source reads,
answer fidelity, latency and actual usage. No helper-only acceptance. Preserve
begin/end refs and private evidence; public APP trace remains a separate gap.

## Implementation evidence

31 focused target/direct/parent-boundary and mounted/source-mapping tests pass.
The retained exact captured search, pinned to the same native World revision,
previously returned only the eight inherited city/location/council seeds. With
no implicit seeds it discovers Barin, Merril, Rurik and Torrin descriptions and
additional named-subject matches. Native truncation remains explicit; this is
not a claim that one bounded search covers every representative. No provider
call or World write in this comparison. Parent tests inspect the exact native
request and stop before unrelated APP persistence; they do not claim a full
parent execution/publication witness. Ordinary answer quality remains pending.

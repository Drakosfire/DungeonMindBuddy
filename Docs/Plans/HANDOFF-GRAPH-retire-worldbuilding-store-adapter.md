# GRAPH: retire the unreachable Worldbuilding store adapter

Status: MERGED_DELIVERED; original implementation/delivery leases RELEASED. Owner: PRIME under operator cleanup/demolition authority.
Base: origin/main@ce41c101cd7af7a19d4ab467638bbbbc0c969b7e.
Branch: codex/retire-worldbuilding-store-adapter. Reuse buddy-context-loop checkout.
Topology: serial GRAPH successor to merged/delivered2052; parallel-independent
of2053@24ca0d07ba868e5d205795df8be0711d08154099 (three disjoint catalogue paths)
and ADVERSARY's blocked predicate-meaning design. Older1235 review lane touches
UI files only. No unmerged behavioral dependency. API delivery is serial and
requires a re-anchored resource lease; no implementation provider/DB/runtime lease.

## One outcome and proof

Remove mutation_context_from_store, its export/import, and the fallback inside
_assert_create_new_id_is_free. Its only executable consumer is that fallback.
The helper's only caller is build_worldbuilding_write_plan, which has already
passed _admit_parent_context requiring WorldGraphMutationContext. First-world
creation directly materializes a contribution and never calls this helper.
Use the existing typed context directly; add no shim or alternate adapter.

Exclusive expected writes:
- apps/live_control_server/models/world_graph_mutation_context.py
- src/graph_memory/worldbuilding_write_plan.py
- Docs/Plans/HANDOFF-GRAPH-retire-worldbuilding-store-adapter.md
- Docs/Plans/HANDOFF-GRAPH-retire-union-preview-client.md

The last path truthfully settles completed2052 authority. Do not alter native
context producers, identity/revision admission, first-world materialization,
Graph/Gold data, sources, profile/catalogue semantics, publication behavior or
models. mutation_context_from_world_root still has callers and is a separate
investigation; do not absorb its removal. No tests need to be deleted or rewritten.

## Validation

Retain caller/type-gate evidence and before/after existing pure plan boundary
checks: free-ID success, occupied-ID and active-redirect rejection, exact binding,
merged/provisional failure, stale-parent rejection and sealed identity digest.
Invoke these existing test functions directly without their DB autofixtures;
label this boundary-only verification, not mounted DB/publication acceptance.
Run existing pure first-world evidence checks as applicable. Inspect import/caller
closure, cumulative diff and Ruff without cache. New mirrored deletion tests are
unnecessary. Independent Bugbot review and CI must precede merge, then qualify
actual merge and deliver with primary state conserved. Preserve inherited failures.

## Author verification

The same12existing checks pass before and after (seven pure plan/identity cases
and five typed first-world evidence cases), invoked directly without DB
autofixtures. Logs match exactly. All retained mutation-context functions/classes
have identical ASTs; only the store adapter was removed. Caller search has no
remaining Python reference to it. Ruff --no-cache and diff checks pass. Evidence:
worldbuilding-store-adapter-{baseline,after}.log and author-verification.json in
the established private runtime-evidence root. Independent review, CI, merge and
conserved delivery remain pending; no mounted DB/full publication claim.

## Completed predecessor settlement

Merged/delivered 0aca7c9ccb4a40eb00f76a53ceeab3f782392cf7 after independent review, actual-merge
qualification and all seven original-head CI checks. Exact API delivery proof:
worldbuilding-store-adapter-api-delivery-proof.json under the established private runtime-evidence/
q01-published-graph-authority root. All91primary tables,nine session files,
savedPlanHTTP,UI and439nativeobjects conserved; provider0,DBwrites0,dependencies
unchanged. Existing verification limits remain. This closes the predecessor
lease and does not claim overall demolition or model/publication acceptance.

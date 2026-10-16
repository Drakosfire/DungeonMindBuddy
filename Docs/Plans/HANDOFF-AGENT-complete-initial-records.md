# AGENT: Complete small records in initial Graph presentations

Status ACTIVE. PRIME solo implementation, ARCHITECTURE review/advice. Base f80b377c260c7b9a7abce9b151d7008b9a834af4. Branch codex/agent-complete-initial-records. Serial successor to merged #1239. DOGFOOD presentation leases are disjoint.

## Outcome
An ordinary Agent can receive whole compact Graph claims and their complete supporting anchor records in the first 8KB presentation, without confusing discovery IDs with admitted facts. Oversized claims remain discoverable and require optional exact detail pages. Current-envelope exact record inclusion, scope/revision, selector and fragment protections remain unchanged. Source opening is separate; a document header does not semantically support a trade claim.

Actual rendered Float Goat turn d2ca1f3f ended in71.7s with claim_target_not_in_envelope: the model cited a Mirathorn discovery ID whose full record was absent, despite returning a typed answer. Preserve this failure; do not manually rewrite it or relax validation. ARCHITECTURE recommends whole small record packing over introducing an automatic answer repair loop.

## Exclusive six-path lease
- This handoff
- apps/live_control_server/services/graph_tool_presentation.py
- tests/test_graph_tool_presentation.py
- tests/test_agent_verified_detail_pages.py
- tests/test_agent_build_governed_graph.py
- tests/test_agent_initial_complete_records.py

No provider calls, serving/retained-state changes, new Graph fact/publication, dependencies or schema migrations during implementation. Complete via tested pushed PR and independent review before adoption. Preserve beginning/end refs for local-model task experiments.

## Required evidence
Deterministic whole-record packing within unchanged8KB, full qualifications and complete source refs, mixed small-admitted/oversized-discovery packets, source-anchor closure, exact-boundary packing, mutated/foreign records rejected, no previous-envelope leakage, detail continuation unchanged, real disposable APP completion accepts delivered small target and rejects omitted target. A fresh ordinary UI answer and source-fidelity evaluation follow accepted deployment; technical passage opening alone does not prove entailment.

## Author verification
72 focused tests pass across initial record packing, exact parent exposure, existing transport/detail pages, real Harness serialization and real disposable PostgreSQL APP Build completion. Small claims retain the full original row and all matching source anchors as one packing bundle; missing anchor closure or oversize omits the entire claim. Discovery pointers never confer authority. The APP regression proves the producing envelope includes only the compact target although the raw validated operation also returned an oversized target. Mutated/foreign presentations, missing fragments and unseen claims remain rejected. Ruff and cumulative diff checks pass. No provider call or runtime/state mutation during implementation. Ordinary answer and substantive source-fidelity acceptance remain pending independent review/deployment.

## Real-projection refinement
A read-only replay found the failing65-character Mirathorn assertion carries12source refs, so its whole anchor closure cannot fit8KB. For targeted object expansion only, when the frozen SDK-verified detail capacity is32KB and the entire result fits exactly one existing detail page, return that complete page immediately. Measure the wrapped page, not raw-result length. Search, default8KB capacity and multi-page objects retain compact initial presentation and optional continuation. No cap increase or second native operation. New exact-head independent review required. This is still the same initial-delivery capability; source-fidelity hold remains.

Wrapped-page measurement: the real Mirathorn first detail page is31,997bytes with a continuation, and it contains assertion53bae plus all12supporting references (19totalanchors). Refine the object shortcut to return the existing first32KB page when it carries at least one whole source-backed claim and all that claim's anchors; remaining records stay explicitly paged. If no such closure fits, retain the8KB compact presentation. Search/default8KB behavior unchanged. This avoids requiring unrelated trailing metadata to fit before a complete useful target can be delivered.

Final author run:79tests pass, including targeted object32KB first-page delivery, explicit continuation, default8KB/search behavior, actual SDK capacity refusal tests and real APP multi-reference completion. Real read-only Mirathorn projection now delivers assertion53bae and all12refs initially in31,997bytes; this reconstructs current read behavior, not a captured historical provider body. No new provider call. This evidence supersedes the earlier packing-only qualification; ordinary answer and citation-fidelity acceptance remain pending.

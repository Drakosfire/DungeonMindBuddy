# INGEST: optional advisory edge review

Status BLOCKED: ARCHITECTURE reviews this bounded contract before activation.
PRIME owns solo implementation. Base f1ef5ba5a0bc3c40eabff44af3afbf1101012f84.
One capability: an explicitly selected Gazetteer1.4 performs a separate advisory
review of generated edge proposals. It may retain only original edge IDs; the
application copies original objects unchanged and preserves omissions as deferred
proposals, not disproved facts. Model selection is NOT source/native/identity
acceptance. No World publication or default profile change.

Evidence: private26-case development benchmark and separate review experiment
showed12→2 unsupported proposals retained, with all6 clear supported proposals
retained. Six context-dependent and two unresolved cases remain separate. This
is known development data, not held-out/general accuracy.1.3 role guard remains
independent/inherited. Full Mirathorn fidelity/publication remains incomplete.

## Flow and invariants

Add optional edge_review_pass spec to code-owned ExtractionProfile, defaultNone.
New internal pass kind edge_review returns only {retained_edge_ids:[string]}.
Validate exact keys/types, unique input IDs, unique returned IDs, subset membership;
unknown/new/duplicate/malformed IDs FAIL the run, never silently salvage. Reorder
by original candidate order; do not let the model rewrite labels, refs, endpoints,
qualifiers, nodes, descriptions or identity. Empty subset allowed with truthful
all-deferred coverage, never a fidelity PASS. Old profiles make no extra calls.

Opt-in Gazetteer1.4 inherits1.3; review AFTER its source compiler so existing
role dispositions survive. Review input includes exact full source packet,
candidate endpoint navigation, and current edge proposals. Endpoint descriptions
and candidate kinds are NOT accepted truth. No hidden gold IDs/expected answers,
source omission, public corpus export or new native predicates. Generation's
prompt remains unchanged; compact navigation is local to the NEW review request.

Keep generation raw pass outputs immutable. Save review result/telemetry and an
advisory before/retained/deferred diagnostic with original objects/hashes. Omitted
edges become existing deferred_items with original refs and stable IDs, reason
advisory_review_omitted_not_proven_false. Collision fails closed. Retained edges
keep their existing candidate semantic states; no reviewed/accepted promotion.
All output artifacts must identify canonical post-review candidate separately
from pre-review/raw generation envelope; do not publish divergent candidates.

Review adds one normal GenerationEngine call under existing provider/budget and
cost tracking. No retry/fallback; skip empty generated edge set without a call.
On review failure/malformed output, no reviewable post-review candidate. Preserve
completed pass outputs AND exact raw responses where returned, review response
where available, request/profile/source hashes, usage/response IDs and unknown
costs. Use existing private RAW_MODEL_RESPONSE failure artifact with explicit
versioned evidence-bundle labeling; never pretend the bundle is one raw provider
response. Existing packaging must durably retain the bundle before FAILED state.
A failed sixth call must not erase successful generation or authorize replay.

## Ownership / exact prospective write lease

- this handoff
- src/graph_memory/extraction/extraction_profile.py (optional spec only)
- src/graph_memory/extraction/category_candidate_graph_schema.py (internal pass kind)
- src/graph_memory/extraction/category_candidate_graph_extractor.py
  (optional review orchestration/raw-response preservation only)
- src/graph_memory/extraction/worldbuilding_edge_review.py (new pure review helpers)
- src/graph_memory/extraction/worldbuilding_gazetteer_profile.py (opt-in1.4)
- src/graph_memory/extraction/worldbuilding_profile_catalog.py (exact1.4 identity)
- tests/test_worldbuilding_edge_review.py (new)
- tests/test_worldbuilding_gazetteer_profile.py (newversion owning pipeline cases)

Parallel-independent of DOGFOOD1178 UI/turn/surface work; disjoint paths/runtime.
Frozen historical MIND extractor PRs are NOT dependencies: PRIME reserves only
this optional review orchestration hunk; roster/recap/identity/consolidation hunks
remain untouched. Rebase/re-review those old PRs before any future merge.
No serving, native DB or retained source/document write lease. Disposable APP
fixtures may test actual registered packaging; private research outputs stay out
of Git. If failure packaging needs another source path, amend contract explicitly.

## Required evidence / gates

Owning fake-provider pipeline compares1.3(no review)/1.4(one review), exact original
kept objects, raw-generation immutability, omitted/deferred refs and diagnostics,
role-guard retention, empty/no-call, unknown/duplicate/rewritten ID failures,
no node/source/provenance change, source-qualified defaults and no new accepted
facts. Actual registered failure packaging must retain earlier raw responses and
review failure without a promotable result; hash-verify/fresh-process reopen.

Registered saved-source replay may reuse responses ONLY if request bytes/hashes
match; distinguish replay/zero new calls from fresh provider output and billing.
Any new semantic benchmark is separate exact-head evidence after independent code
review. Complete implementation→tests→cumulative diff→commit/push/PR, independent
review before merge. No full gold, native eligibility, retained publication,
source edit/restart or operator acceptance is pre-marked complete.

# HANDOFF — PR011A3 slice 2: existing-object observation

**Status:** `DOING` (GitHub PR #370)  
**Base:** `main` @ `c8f436c4`  
**Branch:** `agent/pr011a3-existing-object-observation`  
**Tip:** `7ba6b9e5e93f52bd645a0ab0e0f02bbd1f54d16d` (review-fix tip; docs pin may follow)
**Umbrella:** #367 (DO NOT MERGE fat tip `eb509dae`)

## §1 Mission

Close REQUEST CHANGES blockers for connect-existing **support-only** observation on promote:

- Break the `contribution_merge` ↔ `candidate_graph_to_contribution` import cycle via neutral `source_artifact_domains`.
- Preserve edge projection integrity while ignoring additive session stamps (`value.session_ids`, `temporal_scope.session_id`) but not other temporal qualifiers.
- Wire `CandidateNode.aliases` into identity resolution and connect-existing emit; refuse alias ownership hijack at emit and kernel merge.
- Fail-closed Session 24 PC overlap repair script guards (exact accepted-assertion payload fingerprint) before filtering assertions.
- Prove alias + support assertions survive publish and revision-pinned projection.

## §2 Invariant

Live A3 acceptance remains **PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL** until a fresh prepare→confirm→**exact committed revision reload** (+ Hermes retrieve if claimed) is recorded on the repaired head. This slice removes known integrity blockers; it does not declare full A3 acceptance.

## §3 Observable paths

- `graph_memory.kernel` and `candidate_graph_to_contribution` import in either order without partial-init failure.
- `map_connect_existing_support_assertions` emits attribute + alias support for `resolved_existing` nodes; skips foreign-owned aliases; no competing node assert.
- `_apply_alias_assertion` refuses alias hijack when casefolded alias maps to a different durable node.
- `_edge_core_semantic_fingerprint` includes stripped `temporal_scope` (session_id removed).
- `supersede_session24_overlapping_pc_node_assertions.py` validates campaign/source revision, assertion_id/body coherence, accepted-assertion id-set + dump SHA256, and drop-subject presence before mutation.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/source_artifact_domains.py` | Neutral `CAMPAIGN_STABLE_SOURCE_DOMAINS` constant |
| Modify | `src/graph_memory/kernel/contribution_merge.py` | Stable-domain import; alias hijack refuse; merge `session_ids` on existing edges |
| Modify | `src/graph_memory/candidate_graph_to_contribution.py` | Connect-existing alias emit + foreign-owner skip; revert creature/source_kind creep |
| Modify | `src/graph_memory/extract_identity_gate.py` | `_candidate_aliases`; alias owners passed to connect-existing emit |
| Modify | `src/graph_memory/kernel/world_projection.py` | Edge fingerprint temporal_scope policy; union `session_ids` across active edge supports |
| Modify | `src/graph_memory/candidate_graph_preview.py` | `CandidateNode.aliases` + dict parse |
| Modify | `scripts/supersede_session24_overlapping_pc_node_assertions.py` | Exact accepted-assertion payload fingerprint guards |
| Modify | `tests/test_source_artifact_compatible_stable_domains.py` | Neutral import + import-order smoke |
| Modify | `tests/test_extract_identity_gate.py` | Publish + projection proof; cross-kind alias collision |
| Create | `tests/test_edge_core_semantic_fingerprint.py` | Edge fingerprint agree/disagree cases |
| Create | `tests/test_multi_session_edge_session_ids.py` | E2E: same edge from two sessions → both session IDs on store + projection |
| Create | `tests/test_supersede_session24_repair_guards.py` | Repair validation unit tests |
| Create | `tests/test_alias_ownership_guards.py` | Emit skip + kernel `_apply_alias_assertion` refuse-hijack |
| Create | `Docs/Plans/HANDOFF-pr011a3-existing-object-observation-slice.md` | This handoff |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Point slice 2 / PR #370 in tracker authority |

**Bounded discovery exception:** Not applicable — paths enumerated above.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `src/prompts/*.py` | Prompt behavior outside connect-existing publish proof |
| `evals/*/gold/*.json` | No oracle/gold drift |
| Plan UI / hover / Author Node / standing_context | Product slices |
| Atomic multi-contribution confirm | Successor work |
| Fat tip `eb509dae` reconstitution beyond these fixes | Read-only reference |
| Dogfood report Head SHA update | Point authority at PR #370 instead |
| `creature` node_type mapping / `source_kind` mapper param | Reverted as unexplained scope creep vs `main` |

## §6 Implementation contract

```text
Input:
  Candidate graph with resolved_existing nodes (+ optional aliases)
  Session 24 contribution contribution:a01be11c6967afd9 for repair script

Output:
  Support-only attribute + alias assertions on durable ids (foreign-owned aliases skipped)
  Edge fingerprints that ignore session stamps only
  Multi-session edge supports accumulate session_ids on merge and projection
  Repair script refuses wrong contribution before filtering

Invariant:
  No competing node assert for connect-existing
  No alias hijack across durable nodes
  temporal_scope.as_of (etc.) still disagrees across active edge asserts
  Same edge from two sessions → projected relationship contains both session IDs

Failure behavior:
  Repair script exits nonzero on campaign/source/assertion-fingerprint/drop-subject mismatch
  Projection integrity error when non-session temporal fields disagree
  Kernel merge raises on alias hijack assertion

Replay / idempotency:
  Repair script idempotent when successor carries repair diagnostic marker
```

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
|---|---|---|---|
| Import cycle broken | neutral module + merge import | import-order smoke + stable-domain tests | both import orders succeed |
| Edge session-stamp fingerprint | world_projection | `test_edge_core_semantic_fingerprint.py` | agree on session_id drift; disagree on as_of |
| Multi-session edge provenance | merge + projection | `test_multi_session_edge_session_ids.py` | store + projected relationship both contain session-22 and session-25 |
| Alias publish proof | identity gate + kernel merge | `test_extract_identity_gate.py` alias publish test | alias + attribute at pinned revision |
| Alias ownership | emit + kernel merge | `test_alias_ownership_guards.py` | skip foreign-owned; refuse hijack |
| Repair guards | supersede script | `test_supersede_session24_repair_guards.py` | ValueError on mismatch |
| Focused allowlist integrity | git | `git diff --stat` on §4 paths only | no scope creep |

```bash
python -m pytest \
  tests/test_source_artifact_compatible_stable_domains.py \
  tests/test_extract_identity_gate.py \
  tests/test_candidate_graph_to_contribution.py \
  tests/test_supersede_session24_repair_guards.py \
  tests/test_edge_core_semantic_fingerprint.py \
  tests/test_multi_session_edge_session_ids.py \
  tests/test_alias_ownership_guards.py \
  -q --tb=short

python -c "import graph_memory.kernel; import graph_memory.candidate_graph_to_contribution; print('ok1')"
python -c "import graph_memory.candidate_graph_to_contribution; import graph_memory.kernel; print('ok2')"
```

**GitHub PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/370

# MIND: validate explicit existing actor kinds

Status: ACTIVE. Owner: PRIME; solo implementation.
Base: `c9f5c21f3b835f35660b85fbd2e9a38312c401d4`.
Branch: `codex/explicit-candidate-anchor-kinds`; isolated non-serving checkout.

## Outcome

Current candidate preview validation accepts `pc` and `party`, whose meanings and contribution mappings already exist. Preserve those kinds through typed preview and contribution mapping rather than rejecting them or representing known PCs as NPCs and established Parties as Groups. This is a validation vocabulary extension, not identity authentication or authorization to publish.

Observed boundary failure: a source-reviewed correction to an established Party was rejected because `party` is missing from `NODE_TYPES`, although `kernel_kind_for_node_type` already maps it. The same mismatch exists for `pc`. Existing Group, character/NPC and all unknown-kind rejection behavior remain intact. No mapper overrides, new source formats, schema fields, migrations, roster changes, provider calls or World writes.

## Exclusive write set and topology

- `src/graph_memory/candidate_graph_preview.py`
- `tests/test_explicit_candidate_anchor_kinds.py`
- `src/graph_memory/extract_identity_gate.py`
- `tests/test_known_party_anchor_admission.py`
- this handoff

Parallel-independent of #1142 (registered identity context), #1143 (party endpoint order), and #1139 (collective defaults): no overlapping paths or unmerged behavioral dependency. Remote main and open PRs rechecked. No serving ports or databases leased.

Verify through typed preview validation → contribution assertion mapping, using synthetic source evidence: PC remains PC, Party remains Party, Group remains Group, character retains NPC mapping, and unknown kinds still fail. Run neighboring preview/mapping tests, lint and cumulative diff inspection; commit, push and open PR. Independent review is required before PRIME merges its own code.

After acceptance, re-anchor the held source package and exercise explicit kind correction before any publication. Producer defaults and complete selected-World acceptance are separate remaining work; this slice does not claim they are solved.

## Native identity boundary refinement

The private Session 14 owning-boundary rehearsal proves explicit `pc` fails `_known_party_anchor` after mapper success. Extend this same capability through native identity resolution: permit explicit pc only with a resolved PC reference and the existing exact pinned canonical target checks. Character/NPC behavior remains intact; pc with NPC reference must reject. Add native planner regressions proving support-only observations, no replacement actor assertion, unchanged context, and rejection of mismatched references. No native identity or publication authority is broadened.

Reviewed binding clarification: its transport is NPC-only. Do not widen it to PC or bypass its literal via model_copy fixtures. Explicit PCs use existing resolved PC references through _known_party_anchor; exact reviewed NPC binding contract remains unchanged.

# V6 preservation acceptance report

**Disposition:** `V6_5_IMPLEMENTED_AWAITING_PRIME_REVIEW`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design ref:** `1c43888fc29c4d2e8e9354f103f1cdcb6b1b10d3`
**Activation base:** `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3`
**Implementation branch:** `codex/v6-5-activate`
**Reviewed head / PR / review:** pending
**Inherited PLAY-2 acceptance:** PR #779, head
`2d5ab6ade1d89ec608c941093819ea36404fd18e`, PRIME Cycle 2 PASS
`5331441470`, merge `2ccc96ff2a7d76328578609d5289fd3babcf6442`

## Scope and authority

This proof consumes the accepted V6.1 Buddy request/context mapper, V6.2
complete-object adapter, and DungeonMind's native V4.2 `EvidenceReadService`.
It adds no runtime API, repository, migration, package pin, fixture mutation,
source-body reader, frontend behavior, WorldKeeper behavior, or production
cutover. PLAY-2's PostgreSQL durability evidence is inherited rather than
repeated by this hermetic in-memory proof.

The executable implementation uses exactly:

- `tests/test_v6_5_evidence_anchor_preservation.py`
- `Docs/Reports/REPORT-v6-preservation-acceptance.md`

The cumulative PR also contains
`Docs/Plans/HANDOFF-v6-5-native-evidence-anchor-preservation.md`. The ACTIVE
handoff travels in this PR under the user's standing ruling that a
Steward need not pre-land it separately. It is authority metadata, not an
expansion of the executable lease.

## Exact identities

- Buddy activation base: `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3`
- DungeonMind main checkpoint: `0ab1ae0133ca9038a1d82eb488ed805f09e49feb`
- Installed DungeonMind pin: `0f709d76fdc53bac9c9258d1751463ae2c76ca71`
- Installed WorldKeeper pin: `49a8620f066ce7ef8972a699020c012f50af9158`
- Installed GenerationEngine pin: `9122257f5a8842e4771990a3316130bc1bf7e332`
- Preservation fixture canonical digest:
  `4fdc327cdf6887dc4ae154e44da9904974c82e40d310a807f590ce2db6d21121`
- DomainContract revision 2 canonical digest:
  `d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd`
- Semantic profile revision 1 canonical digest:
  `51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14`

## Requirement-to-evidence receipt

1. **Evidence/source/span identity.**
   `test_exact_native_reads_preserve_evidence_source_and_span_identity` invokes
   native assertion-evidence lookup, exact evidence lookup, and anchor
   resolution. It proves evidence/artifact/revision identity, digest, locator,
   URI, source locator, line reference, explicit span reference, navigation
   flags, admitted supporters, completeness, and deterministic result digests.
   `test_missing_span_is_preserved_and_never_derived_from_locator` proves that a
   missing span remains missing even when `paragraph:14` and highlight
   capability are present.

2. **Complete-object join.**
   `test_complete_object_evidence_ids_join_to_native_reads_without_semantic_drift`
   exercises the production V6.2 adapter, joins its selected-object evidence ID
   to a native evidence read under the same Buddy context, and verifies temporal
   metadata, source classification, session context, and content digest remain
   coherent. No legacy World reader or full-graph reconstruction is used.

3. **Scope.**
   `test_campaign_world_role_and_standing_boundaries_fail_closed` proves
   world-global/campaign-A support in campaign A, campaign-B denial in campaign
   A, and campaign-B admission through world wildcard scope. Exact evidence IDs
   do not bypass scope.

4. **Visibility and standing.**
   The same test proves player denial of GM-only, provisional-only and
   retracted-only support. Denials expose no evidence record, source artifact,
   source revision, anchor, locator, or supporter identity. GM admission remains
   available where authorized. The canonical shared evidence remains visible
   because admitted public supporters exist.

5. **Determinism and context binding.**
   `test_anchor_tokens_are_deterministic_context_bound_and_fail_closed` proves
   same-context determinism and equivalent-context reconstruction, plus
   malformed, forged, foreign-space, changed-revision, changed-role, and
   changed-focus failure.

6. **Focus and fictional time.**
   `test_focus_changes_anchor_identity_not_truth_or_fictional_time` proves focus
   changes neither admitted evidence/supporter membership nor fictional-time
   metadata, while the full request remains part of anchor identity.

7. **Pinned coherence and fresh-source revalidation.**
   `test_pinned_context_stays_coherent_while_fresh_context_rejects_stale_anchor`
   proves the original context remains coherent after live-reader mutation and
   a fresh context rejects the old token after missing artifact, missing
   revision, retracted lifecycle, changed current revision, source-revision /
   artifact mismatch, or revision-digest drift. Fresh direct admission is also
   checked for each mutation rather than inferred from token failure.

8. **Generic native boundary.**
   `test_native_vnext_boundaries_do_not_import_buddy_or_legacy_policy` audits
   `dungeonmind.application.vnext.admission`, `evidence_reads`,
   `materialization`, and `publication`. Those native serving/materialization /
   publication entry points import no Buddy, live-control, or WorldKeeper
   implementation and contain no DungeonBuddy GM/player/campaign/NPC/fictional-
   time term. Buddy semantics remain in `graph_memory.vnext.domain_runtime`.
   Historical compatibility readers and exports are outside this V6/V10 gate.

## Verification

Clean activation environment:

```text
uv sync --locked
PASS; exact direct-url pins matched the identities above
```

Focused proof:

```text
uv run pytest -q tests/test_v6_5_evidence_anchor_preservation.py
13 passed
```

```text
uv run pytest -q \
  tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py \
  tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py \
  tests/test_v6_2_vnext_complete_object_adapter.py \
  tests/test_con_ready_play_worldkeeper_consumer.py
83 passed

uv run ruff check tests/test_v6_5_evidence_anchor_preservation.py
All checks passed

git diff --check
PASS
```

All required witnesses ran with zero skips.

## Limitations and proposed exit judgment

This proves authorization-preserving native evidence navigation metadata and
anchor revalidation. It deliberately does not open source bodies, render
highlights, wire a browser, switch product routes, migrate legacy Worlds, or
repeat PostgreSQL durability. Those remain later consumer/cutover obligations.

Subject to green required regressions and independent PRIME acceptance, this
report proposes `V6_DUNGEONBUDDY_PRESERVATION_ACCEPTED`. V7 remains
undispatched until MIND records the accepted V6 exit and designs its first
bounded bridge-genesis slice.

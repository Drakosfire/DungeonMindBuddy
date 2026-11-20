# MIND — registered extraction verified identity context

Status: ACTIVE. PRIME implements solo under the operator's foundational-work authorization.
Base: Buddy origin/main `31c5044872076a9bdfd17fced71caf11510121c1`.
Branch: `codex/registered-known-entity-context`.
Lane: `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/known-npc-endpoints-20261014/source` (non-serving).

## Outcome and existing contract

Pass caller-supplied verified known entities through the registered recap extraction facade and production controller to the existing category options. Persist ordinary run/source/candidate/mention artifacts so canonical NPC endpoints survive registered-run readback. This bridges the existing KnownEntity trust contract; callers remain responsible for matching verified identities to their authorized World/revision. It adds no browser fields, automatic Graph fetch, recognition admission, summary generation or World publication.

The Pippa experiment now works at category level on accepted code, but the registered runner drops this input because its request has no forwarding field. Do not substitute direct category outputs for an ordinary registered-run witness.

## Exclusive write set

- `apps/live_control_server/services/graph_preview_runner.py`
- `src/graph_memory/extraction/graph_preview_runner.py`
- `src/graph_memory/extraction/known_entity_mention_matcher.py`
- `tests/test_registered_known_entity_context.py`
- this handoff

Topology: serial successor after merged #1140 and #1141. Current main includes merge commits #1140 `1a2fd31ee76648dfbaeb66a6830ca889af6c027c` and #1141 `364a1f54c2bf7a0d20810515bfab02bb0a62aa9c`. Current open sequence is #1142 → #1143 → #1145 → #1189: #1143 is the next serial consolidation slice, #1145 is stacked on #1143, and #1189 has overlapping extraction-runner/category-extractor paths and remains frozen until #1145 settles. These write leases are serialized, not parallel. No serving ports/state leased. Existing source lifecycle, candidate schema, provider selection, corpus context and publication gates remain authoritative. No unreviewed World binding is inferred from a campaign ID.

## Verification and completion

Use a synthetic registered source and fixture client, with a fresh disposable APP database. Prove the supplied NPC reaches the ledger/consolidated edge input, its canonical endpoint and explicit source-backed edge persist, and the registered run/components reopen with verified hashes. Exercise absent context and unmentioned context without provider calls. Run focused existing runner tests, lint and exact cumulative diff.

Implementation includes commit/push/PR. PRIME-authored: ARCHITECTURE independently reviews the updated exact head before merge under the operator's standing review assignment; PRIME retains merge authority. Rollout and source-backed production evaluation follow accepted merge; this capability alone does not prove full World readiness or automatic context enrichment.

## Owning-boundary refinement

The registered candidate validator rejects the existing World helper's `corpus_ref.resolution=world_head`. Add the matcher path to this lease before repair. Native canonical node IDs identify World objects; they must not masquerade as corpus-file references. Omit that native-only corpus_ref on inserted NPC anchors, retaining ordinary verified corpus refs. No new resolution enum or historical format compatibility is introduced. The earlier category-only test did not cover registered validation; record this limitation in the review packet.

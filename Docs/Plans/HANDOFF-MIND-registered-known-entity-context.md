# MIND — registered extraction verified identity context

Status: ACTIVE. PRIME implements solo under the operator's foundational-work authorization.
Base: Buddy origin/main `c9f5c21f3b835f35660b85fbd2e9a38312c401d4`.
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

Topology: serial successor after merged #1140/#1141; current open PR #1139 and other inspected lanes have distinct paths. No serving ports/state leased. Existing source lifecycle, candidate schema, provider selection, corpus context and publication gates remain authoritative. No unreviewed World binding is inferred from a campaign ID.

## Verification and completion

Use a synthetic registered source and fixture client, with a fresh disposable APP database. Prove the supplied NPC reaches the ledger/consolidated edge input, its canonical endpoint and explicit source-backed edge persist, and the registered run/components reopen with verified hashes. Exercise absent context and unmentioned context without provider calls. Run focused existing runner tests, lint and exact cumulative diff.

Implementation includes commit/push/PR. PRIME-authored: independent review required before merge; the previous operator review exception covered #1140/#1141 only. No other agent dispatch authorized here. Rollout and source-backed production evaluation follow accepted merge; this capability alone does not prove full World readiness or automatic context enrichment.

## Owning-boundary refinement

The registered candidate validator rejects the existing World helper's `corpus_ref.resolution=world_head`. Add the matcher path to this lease before repair. Native canonical node IDs identify World objects; they must not masquerade as corpus-file references. Omit that native-only corpus_ref on inserted NPC anchors, retaining ordinary verified corpus refs. No new resolution enum or historical format compatibility is introduced. The earlier category-only test did not cover registered validation; record this limitation in the review packet.

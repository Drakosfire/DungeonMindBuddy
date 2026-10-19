# PLAY — saved session context and durable answer basis

Status: ACTIVE. Base origin/main76f765d3c77d9cf84ac529b0f07617c5875cb58e; branch codex/play-session-agent-context, existing buddy-context-loop checkout. PRIME owns design, integration, PR/merge and5202 delivery. One serial implementation PR, with explicit concurrent nonoverlapping source leases below. No new checkout/environment. Independent review of cumulative exact head required.

## Outcome and failure critique

Buddy reads the exact saved session-copy current Beat/Scene Markdown (including media references) and current-scene saved note. Saving/reopening or later changes must not rewrite the historical context of a prior answer. A stale World/Run/edition/structure pin rejects before provider dispatch. No fallback to the Plan/current head for a missing historical edition. Unsaved browser drafts remain blocked; saving enables Buddy against the accepted edition. This is read context only; session-copy edit proposals are a separate successor with existing edition CAS, not implied by reading.

Progress has no immutable history, so a revision/digest alone cannot recover old note text. Add an additive nullable JSONB play_context_receipt on agent.turn; legacy rows remain readable. Preserve typed origin references as search/identity witnesses, but new V2 receipt is authoritative for edition/note history. Preserve legacy idempotency hashes byte-for-byte when additive fields are null.

## Pinned interface

- PlayContentBasis: edition_revision>=0; edition_revision_id UUID iff revision>0; content_sha25664lowercasehex. Optional play_content_basis on submitted primary-work/API work locator, only valid for kind run. Current UI always supplies it; fresh missing-basis Play submissions reject with refresh guidance. Old accepted-turn retries retain their old receipt behavior.
- PlayRunTurnContextReceiptV2 subclasses/retains the origin/current moment fields of V1, schema dmb_play_run_turn_context_receipt_v2, plus world_id, edition_revision, edition_revision_id, content_sha256, scene_note (str|null), scene_note_sha256 (matching UTF8 SHA iff note present). Missing note differs from an empty saved note. Note UTF8 max32KiB. No scene implies no note. No truncation is hidden.
- TurnSubmission.play_context_receipt and Turn.play_context_receipt accept V2|null, validate exact World/Run/current element/origin witnesses against typed provenance. Store/round-trip through agent.turn. Replayed acceptance cannot substitute a different receipt. Null fields omitted from legacy fingerprints.
- New resolve_world_play_session_turn_snapshot(root,world_id,run_id,run_revision,content_basis) returns (AgentSurfaceContext,V2). Existing V1 APIs stay available for accepted legacy history. resolve_historical_world_play_turn_snapshot accepts V1|V2 and rehydrates immutable edition plus stored note for V2.
- Atomic edition-service read_context_snapshot(run_id,world_id) returns (PlayRun,RunContent) from one existing locked-state transaction. Compare requested Run/edition and original sealed structure against this snapshot. No new data writes/read migrations in resolver.
- Runtime AgentPlayCurrentMomentContext gains optional edition_revision and saved_scene_note; V2 rendering uses full admitted relevant Markdown/note, bounded to64KiB UTF8 total or explicit rejection, not old640-character scene clipping. Legacy rendering remains compatible.
- Route historical resolver receives optional keyword play_context_receipt for V2 only; legacy3-argument callbacks remain unchanged. Turn service persists exactly the admitted V2 receipt and historical retry uses it. No context identity grants write authority.

## Exclusive write leases

Storage worker (Luna low): src/application_state/agent_conversation/types.py, repository.py, service.py; new migration20261018_0036_play_context_receipt.py; tests/application_state/test_agent_conversation_service.py and owning Postgres counterpart/receipt tests. Own PlayContentBasis/V2 model and intent compatibility. No server/UI edits.

Context worker (existing session audit agent, Luna low): apps/live_control_server/services/agent_play_surface_context.py and agent_runtime.py; src/application_state/play/edition_service.py; tests/test_agent_play_surface_context.py and focused edition snapshot tests. Own snapshot/resolver/rendering. No types.py/storage/route/UI edits.

PRIME: this contract, predecessor pane handoff and ROADMAP-demo.md; apps/live_control_server/models/agent_turn.py, routes/agent.py, services/agent_turn_service.py; apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx/.test.tsx, agentInteraction/WorldAgentConversation.tsx, planSurface/components/WorldPlanAgentConversation.tsx, api/types.ts and affected mounted integration/persistence tests. No provider configuration, Graph authority, lockfiles, campaign-content edits or unrelated recovery fixes. Workers do not stage/commit; PRIME integrates, reviews full diff and opens one PR.

## Verification and delivery

Synthetic owning-boundary tests: exact current edition+media+note; foreign/stale/mismatched structure rejected pre-provider; concurrent snapshot consistency; durable receipt round-trip and history after edition+note change; corrupt/missing historical edition fails closed; legacy null-fingerprint compatibility and old history retained; UI keeps unsaved draft gate then enables exact accepted edition. Session-copy proposals remain unimplemented in this slice.

Run relevant Python/model/repository/Postgres tests and UI tests/build. Inspect cumulative diff; commit/push/PR; independent exact-head review. Migration delivery requires existing serving-DB backup and schema/runtime parity, owned API restart and retained state/health; UI uses guarded adoption with old assets retained. Prove actual saved edited fixture context and saved note on normal5202 with a trace/receipt and a bounded authorized dogfood turn if needed; do not publish Graph facts or alter real Edge content. Settle predecessor and this contract truthfully in the next consuming change.

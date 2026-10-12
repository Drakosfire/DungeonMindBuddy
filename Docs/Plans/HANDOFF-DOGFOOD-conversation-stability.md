# DOGFOOD: stable conversation reading and typing

Status: ACTIVE; directly authorized by operator feedback on 2026-10-11: flickering chat, confusing floating Plan label, unclear input focus, icon fullscreen/close, and misleading impression of graph use.
Base: fetched main bb541a49085623a68a173acb46bf709248537c00, merged Plan-bar #1081. The preceding header/toolbar remains inherited unchanged.
Branch/check-out: codex/conversation-stability, /tmp/buddy-automatic-chat-reconciliation.
Topology: serial, one independently useful chat-stability PR. Relevant open conversation work inspected; no overlapping active implementation found.
Write lease: this handoff; apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx; planSurface/components/WorldPlanAgentConversation.tsx/.css; WorldPlanAgentAnswer.tsx/.test.tsx; ui/ConversationDock.tsx/.css/.test.tsx.
Runtime: existing operator-selected5202 serves authorized UI edits through Vite HMR; no restart, new ports, provider request, source/Plan/Graph/APP mutation. Runtime-created tracked Hermes pointers and untracked profile/state files are preserved and excluded from this PR. The .venv runtime symlink is intentionally untracked.

Invariants and failure cases:
- Preserve last validated history during a read in the same World/document scope; clear it on a changed scope. Loading chrome is initial-load only. Receipt validation and stale-response generation fences remain intact; failed/new invalid reads never become new transcript data.
- Permit drafting while background history, Ask or proposal is pending; Send/Enter dispatch guards remain unchanged and blocked while busy. Never repost recovery automatically.
- Memoize unchanged plain/structured answer content by actual text/segment values, retaining rendered message nodes and selection across unrelated refreshes. Changed text/segments still update.
- Remove only the generic Plan eyebrow; meaningful other-surface/target attribution and full provenance in Details remain.
- Display actual basis only for completed validated turns, with explicit four-status mapping: World+Plan/Run, partial, or Plan/Run only. Unknown/failed/unconfirmed data receives no fabricated source label; unknown completion is rejected by owning history validator. Context permission is explicitly different from evidence used in a reply.
- Icon fullscreen/restore/close retain accessible names, tooltips, keyboard behavior and focus management; input has explicit normal and focus-visible borders.

Verification: app TypeScript passes. Mounted World conversation + shared dock:194 tests pass. Answer renderer:all6 tests pass (four existing formatting/escaping/hook-order cases retained plus two plain/structured DOM-stability/update regressions). Combined distinct owning total200. Full cumulative leased diff checked. Background-reconciliation regression holds history GET pending and proves same message node, typed draft, focus, initial-load indicator absence and exactly one Ask POST in fake transport; no production Ask. Partial/Plan-only/unknown basis assertions and icon keyboard names are covered. Actual updated screenshot not obtained: browser inspection was interrupted; no visual acceptance is claimed.

Read-only live incident evidence: the completed operator-visible uppercase Test has a durable completion with status plan_only_insufficient_evidence, retrieval empty, sufficiency insufficient and packet omitted_insufficient; a Plan-only response is truthful. It is not assumed to be the earlier lowercase unconfirmed test or the separately authorized technical Mossglade probe. Exact correlation/receipt metadata remains private in .run/test-turn-reconciliation.json; no prompt/Plan/source payload is published. This slice fixes presentation/reconciliation stability, not graph completeness, retrieval policy or source adoption.

# RECOVERY: retain an unresolved World request without blocking new work

Status: ACTIVE. PRIME owns this bounded slice under the operator-authorized
References/recovery goal. Base origin/main8f1d0f8745e879dd7dd106aa5020b5054bc3b4b5.
Branch codex/conversation-retained-request-recovery in the existing
buddy-context-loop checkout. Topology: serial after merged/delivered #2158.

## Outcome and invariant

An operator can explicitly keep an unresolved saved Build/Play request for later,
continue drafting/sending, inspect the retained exact envelope and restore it to
pending recovery without automatically dispatching it. This does not classify
its server outcome, cancel execution, change a Run or grant new retry authority.
The original IDs, payload and references remain exact. Newer pending requests
and composer drafts cannot be overwritten. A storage failure leaves the pending
copy and sending guard intact. No automatic request disposal or provider replay.

The ordinary Build measurement found a retained unaccepted Play request blocks
new sends across the World. Refreshing World history does not resolve it. The
separate native Play Graph integration failure remains open; this recovery slice
does not claim to fix admission or establish References acceptance.

## Adoption and exclusive write set

- This handoff; consume settlement in HANDOFF-TRACE-retrieval-host-timing.md and
  HANDOFF-PLAY-retained-source-references.md.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx.
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx.

Adopt the existing validated pending envelope and storage owner. Retain its exact
bytes under an immutable per-turn suffix in that namespace; no new envelope
format, DB table, execution ledger or rejection classifier. Existing rejected
reference receipts keep their distinct meaning. Reuse current request parsing,
World binding, draft and explicit retry controls. The operator action moves the
active pending copy only after the retained copy is verified; restore requires
an empty pending slot. Keep the retained copy after restore.

No API, migration, inference, Graph, source or publication change. Open ingestion
PRs were inspected; none owns this UI path. #2104 remains held. Runtime8000/5202
remain integrated44b5c416727a81ec270f9dc81af2420406df54c2 until reviewed delivery.
No runtime/state write lease during implementation. Reuse current dependencies.

## Verification and delivery

Owning UI tests must prove exact Build/Play reference retention, preserved newer
composer text, no provider POST from keep/restore, restored original retry IDs,
reload discovery, collision and quota failures, and no overwrite of another
pending request. Run owning integration checks and typecheck; inspect the full
cumulative diff; independent Bugbot review and CI precede merge/delivery. Deliver
only the reviewed UI change over the current integrated runtime, retaining
in-flight work and all saved data. Ordinary dogfood must verify keep, restore and
explicit retry availability; do not retry the known Play admission failure merely
to exercise the button.

The successor remains actual Play native Graph/source acquisition and producing
input integration, followed by cross-surface References acceptance and measured
code-efficiency work. No retrieval strategy or model change belongs in this PR.

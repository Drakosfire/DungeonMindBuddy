# ACTIVITY: observe native authorization before provider transport

Status: ACTIVE. PRIME owns this bounded operator-authorized activity correction.
Base: bc405328880e2e5abed8d7bb06d6f1b26b3b10d3, fetched remote main.
Branch: codex/native-authorization-activity, existing buddy-context-loop checkout.
Topology: serial after merged and delivered PR2185. Existing INGEST lanes do not
own these paths; held Play2172 has no overlapping changed paths and remains held.
No new checkout, dependency environment, provider call or active runtime lease.

## Outcome and critique

Native prompt capture records an actual prepared request but omits the existing
provider_call/authorized observation. The ordinary67c7 run therefore displayed
Preparing the request from56.4s until its writer response at72.2s. The newer
Corrupted Edge proposal reproduced this during its44.8–86.8s writer phase.
The UI already renders an authorized OpenAI call as waiting; fix the observation
at its capture owner instead of inferring dispatch from text, making another call
or adding a second polling/timeline mechanism.

After a native prompt reference is durably captured, record its actual durable
authorization identity in the existing trace shape. Use the concrete current
SurfaceNativeExecutionV1 owner so this covers its routing, retrieval, evidence
selection and writer authorizations while leaving the separate existing legacy
observation path unchanged. This observation grants no execution authority and
never claims transport or completion. Preserve prompt-capture refusal, terminal
failures, response/usage identity, and the existing full timeline.

Keep capture failure behavior at its existing owner. Do not nest the collector's
non-reentrant claim lock. No schema or response contract changes, token/output
limits, source/Graph changes or UI production changes.

Independent review found that optional generic prompt capture also reaches this
collector and already publishes a richer authorization observation. Scope the new
emission explicitly to direct native authorization callers: generic authorize()
disables it and retains its existing observation, including conservative input
estimate. Remove the duplicate coalescer entirely. No immutable trace rows are
rewritten or discarded. This adds agent_turn_service.py only for the explicit
caller/collector argument, within the same single activity outcome.
Exercise prompt capture enabled and disabled at actual transport entry.

## Exclusive expected writes

- This handoff.
- Docs/Plans/HANDOFF-RETRIEVAL-native-keyword-recovery-focus.md (truthful
  predecessor settlement only).
- apps/live_control_server/services/agent_context_trace_collector.py.
- apps/live_control_server/services/agent_turn_service.py (explicit generic caller observation ownership only).
- tests/test_surface_native_build_ordinary.py (actual SDK → APP/trace → transport
  observation hook and regression cases).
- tests/test_agent_context_trace_collector.py if an existing owner test requires
  strengthening; do not replace actual admission with a fake authority fixture.
- apps/live-control-ui/src/planSurface/components/BuddyActivity.test.tsx.

## Verification and delivery

Exercise actual native HTTP/SDK dispatch with the existing disposable APP54329
and synthetic Core fixtures. At transport entry require exactly one matching
prompt and authorized observation, bound to the actual trace and provider
attempt, before a response. Cover ordinary success and an incomplete terminal
writer result; preserve existing rejection and read/claim checks. Verify the UI
shows waiting after a recorded writer authorization despite older retrieval
activity, and shows the full timeline and terminal error without new prompt reads.
Run owning collector/ordinary Build/UI checks and inspect the cumulative diff.
Obtain independent Bugbot review and all CI, then merge under PRIME authority.

Delivery uses a separately reviewed API-only integration over deployed51501,
not a wholesale main replacement. Preserve APP54331, Core54330, UI5202, drafts,
original failures and session state. Keep the held Play and source-transfer
boundaries. After delivery dogfood live and delayed/terminal activity through
ordinary controls; technical tests do not establish operator acceptance.

# DEMO: Ingest Agent conversation adoption

## Status

**BLOCKED.** This handoff defines an identity-only Ingest conversation scoped to a selected managed World and the Ingest surface. It makes no claim about an active extraction Run. It grants no implementation lease, runtime authority, provider/spend approval, or write permission.

Steward: DEMO. Implementation owner: DungeonMindBuddy. Source-aware and Run-aware Ingest assistance are separate future capabilities.

## Pinned baseline and topology

- Buddy main at design: `3608663a950cde7472ea942628170f083e533b14` (2026-10-02).
- At re-anchor, #836 (World-to-native-Graph binding), #839 (Plan diagnostics), #842 (Play Agent handoff), and #843 (Build Agent handoff) were open. PRIME owns review, merge, and activation.
- Default topology is **serial**. The saved managed-World Plan conversation remains the next product gate; this Ingest slice is a later surface-adoption candidate. Re-anchor and confirm PRIME’s order after the Plan gate and the queued Play/Build slots resolve. Recheck current main, open PRs, and path/runtime leases before activation.
- This is only a BLOCKED design record. It does not dispatch an implementation lane or authorize a parallel PR.

## Current evidence

At the pinned main:

- `MemoryIngestPage` publishes a surface context but mounts no Ask plugin and registers no Ask presence. It displays Graph Review only for an exact extraction-run handoff.
- Its existing context is campaign/session-shaped. Comparisons between a selected World ID and `campaign_id` are not World ownership authority and must not become the Agent owner contract.
- The Agent turn request model accepts `surface_id: ingest` and a World owner with no primary work. The server independently resolves a supplied World owner, while its saved-work resolver currently supports Plan only.
- The older `/api/live/query` context adapter is campaign/document/session-shaped and is not the managed-World Ingest conversation path.
- The shared `AgentInteractionChrome` and `AskPluginSlot` are the accepted conversation host. Ingest does not currently register a plugin there.

These are source findings, not a live browser or provider witness.

## Bounded first-slice contract

1. Reuse the global Agent host. Add an Ingest-specific Ask plugin under the Ingest surface; do not create a separate chat shell or redesign the shared host.
2. Make Ask available only for an independently selected managed World. The turn identifies that World and `surface_id: ingest`; it has no active Run/work claim. A selected extraction Run, source, candidate, or Graph Review state is not included in this first turn.
3. Send the user’s question with an explicit World owner scope. Omit `primary_work`, set `client_work_state: none`, set `graph_request: none`, and set `graph_selection: null`.
4. Before dispatch, tell the user that the Agent receives the selected World/Ingest identity and their question only. It has not read the source, extracted content, graph, or selected Run. Do not send campaign IDs, session numbers, run IDs, source text, evidence, candidates, graph payloads, or other run/source data.
5. Keep thread storage partitioned by the non-wire local key `ingest-owner:world:<world-id>`, following the established Index pattern. The request owner is the explicit verified World ID. Do not put the World ID or the local key in a `campaignId` field or represent it as campaign scope.
6. If no managed World is selected, or the server cannot resolve the supplied World owner, keep Ask unavailable or fail the turn before provider dispatch. Do not infer World ownership from `campaign_id == world_id`, the query string, Graph Review handoff, or UI context.
7. A switch to another World or thread invalidates pending results from the previous identity; no late response may render or persist in the new World’s conversation.

## Verification required at activation

The future ACTIVE handoff must pin exact refs, enumerate an exclusive expected-path allowlist, name verification/runtime owners and PR topology, and include any required truthful roadmap or predecessor-state sync. Candidate paths below are investigative hints, not a lease.

At minimum, verify at the owning boundaries:

- A mounted `App` + Ingest + shared Agent host test proves Ask presence only for a verified managed World and unavailable behavior for no/legacy/unresolved World selection.
- A captured request contains `surface_id: ingest`, the exact World owner, no primary work, `client_work_state: none`, and `graph_request: none`. It contains no campaign/session/run/document/source/Graph fields or source payload.
- A backend route test with an injected fake runtime proves a valid registered World reaches the no-work Ingest turn, while an unknown/unavailable World fails before runtime/provider dispatch.
- A pending response from World A cannot display, save, or rehydrate under World B. The local thread partition key remains surface + World and is not emitted as campaign identity.
- The UI plainly discloses that no Run/source/Graph content was sent. Questions about the selected Run are not presented as run-aware answers.
- Review the cumulative base-to-head diff and run the relevant Ingest/Agent mounted tests, Agent route tests, and type checks. Record inherited failures. PRIME approval is required for any live configured-provider witness; no model/spending request or live witness is authorized here.

Candidate implementation boundaries to recheck after re-anchoring:

- Ingest page/context and a new Ask plugin plus mounted tests under `apps/live-control-ui/src/ingestSurface`.
- A typed Ingest turn request/client wrapper under `apps/live-control-ui/src/api`.
- Existing Agent route tests under `tests`; change `apps/live_control_server` only if the server owner-resolution contract requires it.
- Add or change shared Agent context/provider types only if the Index-style local thread partition cannot remain separate from wire World scope; require a narrow design review first.

## Separate Run-aware follow-up

Do not claim or expose a selected extraction Run as the current work object until its owner service provides an authoritative persisted Run record/contract proving its World relation. Buddy must resolve that exact identity and any exposed status/revision server-side before a Run-aware turn. The current `campaign_id` comparisons are not proof. If the owning Run-to-World authority cannot be named, keep Run-aware Ask unavailable and return for owner design.

## Explicit exclusions

No campaign-to-World mapping, Run resolver, source or evidence retrieval, committed Markdown read, extraction-candidate/Graph payload, graph query/citation, ingestion/admission change, document edit, shared chat-shell redesign, shared owner-type migration, provider call, database/runtime action, or implementation PR is authorized by this BLOCKED handoff.

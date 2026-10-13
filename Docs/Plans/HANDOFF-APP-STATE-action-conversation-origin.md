# APP-STATE: sourced Plan action conversation origin

Status: ACTIVE, bounded APP predecessor for SERVER's saved Plan consultation cutover.

Base: GitHub `main` at `f05de67561eefd3afb46e1beda757eab89568c4a`. The retained database has not applied `20261012_0020`, and the prior inventory found zero real action consultation receipts. The already merged nullable `plan_action.action.consultation` JSONB owns this contract. No migration or new table is required.

## Contract

- A new sourced Plan selection consultation receipt requires a server supplied `origin_conversation_id` and `origin_pointer_revision`, including Graph unavailable outcomes. These fields enter the action input and consultation receipt digests. The separate `history_conversation_id` identifies optional attributed Ask history and, when present, must equal the origin.
- Reservation accepts a transient typed expected World pointer. APP checks it in the reservation transaction, then checks the frozen receipt against the active World pointer in `freeze_consultation` and before appending each provider authorization event. These short transactions serialize with New conversation. No provider I/O runs under a database lock. SERVER includes the pointer binding in its computed request fingerprint and captures the expected active pointer before dispatch.
- A linked clarification reply requires the same conversation origin and the existing exact Plan/draft/selection/surface predecessor identity. Its pointer must still be current to freeze or authorize fresh provider work. Already authorized work may settle in its old action record after a New conversation.
- Conversation history selects by World and viewed conversation across Plan revisions and documents, in bounded pages. Each projected action keeps its historical `PlanActionBasis`. An archived conversation may be read, while current UI uses the active pointer. Existing exact basis status remains available for legacy and current edit status; plain actions with null consultation do not acquire invented conversation ownership.
- Current consultation receipts require the origin. Do not add an old receipt decoder for synthetic fixtures. No Ask Turn, second store, new lifecycle, Graph policy change, or generic response replay is introduced.

## Write lease and proof

Only `src/application_state/plan_action_dialogue/{types.py,graph_consultation.py,repository.py,service.py}`, `tests/application_state/{test_plan_action_consultation.py,test_plan_action_dialogue_postgres.py}`, and this handoff are writable in this slice. Agent conversation and SERVER/UI source are read only. The APP worker owns focused PostgreSQL and typed proof for stale pointer reservation/freeze/authorization, changed pointer with same key, cross revision/document conversation history, archived read, linked reply origin and basis, fresh service readback, Graph unavailable receipt origin, and plain legacy action behavior. Inspect the cumulative base to head diff and open a PR for independent PRIME review. Merge requires separate authority.

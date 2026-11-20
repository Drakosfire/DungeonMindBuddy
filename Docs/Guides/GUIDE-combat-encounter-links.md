# Saved Combat encounters

Open a saved encounter with `/combat?world=<managed-world-id>&encounter=<encounter-uuid>`.
Use the World slug from Buddy's World picker. The link uses the existing
signed-in Combat access check. The encounter UUID stays stable as the
record changes, so opening the link loads the latest committed revision.

## Read boundary for future Map and VTT adapters

Read `GET /api/live/combat/encounters/{encounter_id}?world_id={world_id}`
through the authorized Combat client. Combat owns the encounter and its
revision. Use `(world_id, encounter_id)` for encounter identity and
`draft.entities[].id` within that encounter for participant identity.
Participant names, order, and group membership can change. Treat the
numeric encounter `revision` as a version of the entire committed record.

Dispatch on `draft.schema`. The v1 draft carries the active and round-start
actor IDs and round, while v2 carries turn state according to the selected
profile. Both drafts include stable participants and group membership.
A future map can derive its display from each committed snapshot and key
its own token bindings by encounter and participant ID. Keep private notes
and exact mechanics within the current Combat audience. Map positions and
player-facing disclosure belong to the future map or VTT owner.

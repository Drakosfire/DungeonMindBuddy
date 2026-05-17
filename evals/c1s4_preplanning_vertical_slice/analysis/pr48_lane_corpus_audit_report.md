# PR48 Lane Corpus Audit Report (Revised)

Audit-only: no active-gold, retrieval, or admission behavior changes.

| Question | Desired lanes | Existing artifacts | Missing artifacts | Current packet observations (by mode) | Next required PR |
|---|---|---|---|---|---|
| Q1 NPCs in Stone Bridge | prior_campaign_memory, character_npc_continuity, location_worldbuilding | Session 3 recap; NPC hubs for Pippa/Bubbles/Grishna exist | Stone Bridge + River's Edge location hubs | Admitted context still dominated by `prior_campaign_memory` across modes; character/location lanes not populated | PR49 location hubs + PR50 lane mapping for existing NPC hubs |
| Q3 distance to Mirathorn | known_gaps, location_worldbuilding, prior_campaign_memory | Session memory exists | Stone Bridge route/location baseline hubs | Benchmark known-gap expectations hit, but packet-lane surfaces still mostly prior-memory; treat benchmark-hit vs rendered-lane as separate checks | PR50 known-gap surface clarity + PR51 lane-specific gold |
| Q5 gigantic tree in hemp | support_adaptation, location_worldbuilding, prior_campaign_memory, known_gaps | Hempholm location hub and support cards exist | none mandatory for support lane; location lane retrieval/classification still needs verification | `prior_only` has no support by policy; support modes show non-zero support share and support burial metrics | PR50 verify Hempholm location-lane retrieval separate from support-card retrieval |

## Key corrections
- Pippa/Bubbles/Grishna hubs already exist; follow-up is indexing/retrieval/admission/classification verification, not duplicate creation.
- Q5 observations are mode-specific: support appears in support-enabled modes.
- Q3 known-gap expectations can be satisfied at benchmark-matching level even when admitted lane rendering does not explicitly show known-gap entries; this distinction must remain explicit.

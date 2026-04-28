"""Stage B ``route_sentence_units_to_hubs`` system prompt — extracted for versioning and A/B experiments.

Content-addressed IDs use blake3 truncated to 24 hex chars (same convention as
``src/prompts/corpus_session_planner.py`` ``INSTRUCTIONS_TEMPLATE_ID``).
"""

from __future__ import annotations

import blake3

_PARTY_CONTINUATION_V1_BODY: str = (
    "\n\nBenchmark addendum — party continuation (experimental): "
    "When routing_context.session_pc_roster_slugs is present and a unit uses they, the group, "
    "our team, the team, teammates, or the rest of the group as the joint subject of "
    "movement, rest, camp, travel, watching, or shared field action without naming an "
    "individual PC, set assigned_hubs to [\"the_party\"] exactly (server expands to "
    "routing_context.session_pc_roster_slugs). "
    "Favor this when the immediately previous sentence_unit in this batch already "
    "established named PCs or joint scene context for the same beat. Do not use this "
    "for pure scenery or object narration with no PC as subject.\n"
)

_NARROW_MULTI_PC_GUARD: str = (
    "Narrow-multi-PC counter-example (do NOT roster-expand): when a unit names two or three "
    "specific PCs each in a distinct in-unit role (actor + object/locus, rescuer + target, "
    "attacker + victim, addressee + speaker), assign exactly those named PCs and no others. "
    "Do not add other PCs from prior roster context, prior beats, or hub_manifest just because "
    "a party label is in scope. "
    "Example: \"Marla then grapples Bonogo and is about to do much worse when Caelynn comes to "
    "the rescue.\" -> [bonogo, caelynn]; do NOT add baergrom, ephanna, karsemine, or stafl even "
    "if a previous beat established the full party. The party-continuation rule above only "
    "applies when no individual PC is named as actor or object in the same unit.\n"
)

PROMPT_VARIANT_APPENDS: dict[str, str] = {
    "party_continuation_v1": _PARTY_CONTINUATION_V1_BODY,
    "party_roster_strict_v1": _PARTY_CONTINUATION_V1_BODY + _NARROW_MULTI_PC_GUARD,
}

ROUTING_SYSTEM_PROMPT_BASE: str = (
    "You map recap sentence units to campaign hub slugs for continuity and retrieval.\n\n"
    "Output contract:\n"
    "- Return one JSON object matching the schema; no markdown fences.\n"
    "- assigned_hubs may contain multiple hub_manifest slugs, or the sentinel "
    "\"the_party\" for a whole-band beat (server expands to routing_context.session_pc_roster_slugs "
    "from recap frontmatter / registry). If \"the_party\" appears, do not also list individual "
    "PC slugs; it may coexist only with non-PC hub slugs when the same unit genuinely routes "
    "to both the party and that non-PC hub.\n"
    "- Set routing_diagnostic_bucket on every route row (see Diagnostic buckets below).\n"
    "- Rationale must quote or cite phrases from the sentence_unit.text that justify the route "
    "and the diagnostic bucket.\n"
    "- Use needs_new_hub_candidate=true only when assigned_hubs is empty and the unit clearly "
    "implies a real entity with no fitting hub.\n\n"
    "Diagnostic buckets (routing_diagnostic_bucket; semantic classification, not retrieval):\n"
    "- npc_placeholder: focal subject is a specific non-PC person/creature (named NPC, pronoun "
    "clearly anchored to an NPC, reported speech centered on an NPC) and no NPC hub exists in "
    "hub_manifest.\n"
    "- location_placeholder: focal subject is a place, route, region, town, camp, forest, tower, "
    "city, etc., with no matching location hub in hub_manifest.\n"
    "- event_or_object_placeholder: focal subject is an object, substance, environmental state, "
    "plan beat, or abstract situation (meat contamination, wagon/crates, storm/magic weather, "
    "generic consequence of an object).\n"
    "- new_hub_candidate: assigned_hubs is empty and the unit clearly implies a durable named "
    "entity worth a future hub or registry entry (use together with needs_new_hub_candidate=true "
    "when appropriate).\n"
    "- true_empty: generic bookkeeping, transitions, or no durable retrieval subject; "
    "assigned_hubs=[] and needs_new_hub_candidate=false.\n"
    "- Diagnostics are mutually exclusive with assigned_hubs except this one case: when the row "
    "assigns at least one PC hub (or \"the_party\") and a named NPC without any NPC hub in "
    "hub_manifest is also a clear focal of the same unit, keep the PC assignment and set "
    "routing_diagnostic_bucket to npc_placeholder. For all other rows with assigned_hubs, set "
    "routing_diagnostic_bucket to null.\n\n"
    "Normalization:\n"
    "- Recap prose may spell a PC differently from the slug: Karesmine = karsemine; "
    "Beargrom / Baegrom / Baergom / Baergorm = baergrom, when those slugs appear in hub_manifest.\n\n"
    "Decision procedure for each sentence_unit:\n"
    "1. Start from the unit text, not from source path, recap filename, or hub anchor path. "
    "Do not assign a hub only because a path mentions it.\n"
    "2. If the unit is generic bookkeeping or has no entity/location/faction/item/event/world "
    "subject, abstain with assigned_hubs=[] and needs_new_hub_candidate=false and "
    "routing_diagnostic_bucket set to true_empty.\n"
    "3. PC-only role rule: when every hub_manifest entry has subject_class=\"pc\", assign a PC "
    "only when that PC is an actor, object, addressee, rescuer, target, listener, affected party, "
    "or object/locus of the same beat. Object/locus means this unit's focal action is on that PC "
    "(struck, enveloped, grappled, rescued, directly addressed as the decision point). "
    "When two manifest PCs each have an in-scene role in the same beat inside one unit, assign both "
    "(hypothetical slugs): \"With the swarm crowding River, Morgan drives her blade home\" -> "
    "[river, morgan] (River = locus under pressure; Morgan = actor in the same beat). "
    "\"Dust chokes Morgan; River drags her clear\" -> [morgan, river]. "
    "Do not drop the second PC when they are in clear bodily peril, grappled, enveloped, or the "
    "explicit rescue target in that same unit. "
    "It does not add a hub for a PC named only in a subordinate setup clause that backgrounds "
    "continuity while another PC acts in the main clause **unless** that clause still places the "
    "second PC in object/locus as above (then include both). "
    "A passing PC name in an NPC/location/event-centered beat is not enough. "
    "Never use a PC hub as a stand-in for an NPC, location, faction, item, or event.\n"
    "4. Roster copy rule (group beat): when routing_context.session_pc_roster_slugs is present "
    "and a unit uses a party name from routing_context.pc_party_names as the acting/deciding/"
    "resting/watching/preparing/moving band, include \"the_party\" instead of individual PC slugs. "
    "The server expands \"the_party\" to routing_context.session_pc_roster_slugs (GM-declared: "
    "optional recap frontmatter session_pc_roster, else campaign _party_registry.json "
    "session_pc_rosters; canonical order follows hub_manifest). "
    "Do not list individual PC slugs for a group beat; do not reconstruct the session roster from "
    "names visible in the recap text. Only add other hub slugs alongside \"the_party\" when they are "
    "non-PC hubs with their own same-unit routing role.\n"
    "   Examples: \"Questionable Company watches...\" -> [\"the_party\"]. "
    "\"The rest of the Questionable Company decide to take a short rest\" -> [\"the_party\"].\n"
    "5. Team/group rule without a named party: use [\"the_party\"] when **the team** / "
    "**our team** / **teammates** is acting in a fight or agreed job, when **the team decides** "
    "or shares a plan, or when **the group** clearly denotes the PCs as the joint subject of "
    "movement/approach/arrival. Abstain when group/team wording is only vague framing and no PC "
    "has a role from rule 3.\n"
    "6. Exceptions to roster/group expansion: reported speech about the party without joint action "
    "uses only rule 3 roles; a single named PC as main-clause actor stays narrow when a subordinate "
    "phrase only mentions another PC without an in-unit object/locus role for that second PC "
    "(contrast rule 3 dual-PC examples). Focal scouting/perception by one PC stays narrow unless the "
    "unit center is the whole band's joint act.\n"
    "7. Previous-unit pronoun binding (one-hop): a PC may be assigned from the immediately previous "
    "sentence_unit.text only when the current unit is pronoun-led or deictic-led "
    "(he/she/they/him/her/them/his/her/their/this/that/then/afterward/alarmed) and the previous "
    "unit unambiguously binds that cue to one manifest PC. This is coreference, not scene memory. "
    "Cap this at one carried PC slug. Do not carry when the current unit introduces a new focal actor, "
    "pivots to ambient/object/location narration, or would require whole-party assignment by carryover "
    "alone. When using this rule, rationale must quote both the binding phrase from the previous unit "
    "and the pronoun/deictic cue from the current unit.\n\n"
    "Final self-check:\n"
    "- If a rationale says Questionable Company, party name, team, group, whole party, or roster "
    "for a joint band beat, assigned_hubs should include \"the_party\" when routing_context."
    "session_pc_roster_slugs is present — do not enumerate PCs by hand. "
    "When routing_context.pc_party_names lists a band label used in the unit, apply rule 4.\n"
    "- Prefer abstain over a wrong hub when no rule applies. Do not abstain from a roster-copy "
    "unit just because one session roster member is not named in the recap prose — session roster "
    "comes from routing_context.session_pc_roster_slugs (frontmatter or registry), not from inferring "
    "names from sentence_units.\n"
)

ROUTING_PROMPT_BASE_ID: str = blake3.blake3(ROUTING_SYSTEM_PROMPT_BASE.encode("utf-8")).hexdigest()[:24]


def build_routing_system_prompt(prompt_variant: str | None) -> tuple[str, str]:
    """
    Build the full system prompt and its content id (base + optional variant append).

    Returns ``(system_text, routing_prompt_id)`` where ``routing_prompt_id`` is a 24-hex blake3
    digest of the exact system string sent to the model.
    """
    system = ROUTING_SYSTEM_PROMPT_BASE
    if prompt_variant is not None and str(prompt_variant).strip():
        key = str(prompt_variant).strip()
        extra = PROMPT_VARIANT_APPENDS.get(key)
        if extra is None:
            raise ValueError(
                f"Unknown --prompt-variant {key!r}; known: {sorted(PROMPT_VARIANT_APPENDS)}"
            )
        system = f"{system}{extra}"
    full_id = blake3.blake3(system.encode("utf-8")).hexdigest()[:24]
    return system, full_id

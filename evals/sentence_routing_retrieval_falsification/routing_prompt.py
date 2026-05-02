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
    "Session NPC negative evidence:\n"
    "- When routing_context.session_npc_names is present, those names are known session NPCs/non-PCs. "
    "Never map them to manifest PC slugs. If such a name is focal and no NPC hub exists in hub_manifest, "
    "use routing_diagnostic_bucket=npc_placeholder (or another placeholder when appropriate). If a manifest "
    "PC is also named in the same unit, keep the PC assignment and set the placeholder diagnostic as needed.\n\n"
    "Per-unit routing_context (optional; benchmark harness only):\n"
    "- When a sentence_unit object includes a \"routing_context\" field, treat those keys as applying "
    "**only** to that unit. They supplement (do not replace) top-level user payload routing_context "
    "for roster labels and session_pc_roster_slugs.\n"
    "- Supported keys for falsification runs: active_scene_owner_hubs (list of PC hub slugs), "
    "active_collective_actor (e.g. \"the_party\"), party_expansion_allowed (boolean), "
    "narrow_pc_only (boolean). When narrow_pc_only is true, assign only PCs that have a concrete "
    "sentence-local role in that unit; do not expand to the full session roster from group words. "
    "When party_expansion_allowed is false, do not use [\"the_party\"] or roster-copy for that unit "
    "unless explicit_party or implicit_party rules still apply from unit text alone.\n\n"
    "Decision procedure for each sentence_unit (choose a routing mode first, then assign hubs):\n"
    "Routing modes: true_empty, explicit_pc, explicit_party, implicit_party, "
    "previous_unit_pc_continuation, scene_owner_pc, placeholder_only.\n"
    "0. Start from the unit text and routing_context, not from source path, recap filename, "
    "or hub anchor path. Do not assign a hub only because a path mentions it.\n"
    "1. true_empty: if the unit is generic bookkeeping, transition prose, or has no durable "
    "retrieval subject, use assigned_hubs=[] and routing_diagnostic_bucket=true_empty.\n"
    "2. explicit_pc: when every hub_manifest entry has subject_class=\"pc\", assign every named "
    "manifest PC with a direct sentence-local role: actor, object, addressee, rescuer, target, "
    "listener, affected party, object/locus, perceiver/finder, or topic/object of a question, "
    "concern, judgment, accusation, warning, plan, reported problem, or handling decision. "
    "Named PC as topic/object of decision: assign the PC even if the PC is not the grammatical "
    "actor. Examples: \"Marla asks Caelynn how she should deal with Bonogo\" -> [caelynn, bonogo]. "
    "\"The mayor asks what should be done about Karsemine\" -> [karsemine]. "
    "\"Ephanna warns them that Stafl may be compromised\" -> [ephanna, stafl] if Ephanna is "
    "the speaker/actor and Stafl is the concern. Do not expand to the_party from this rule. "
    "When two or three manifest PCs each have concrete in-unit roles, assign exactly those PCs "
    "unless the whole party is the grammatical actor of the unit.\n"
    "3. perceiver/finder is a first-class explicit_pc role: assign a manifest PC when the unit "
    "states that the PC finds, sees, hears, notices, discovers, observes, smells, detects, "
    "approaches and perceives, or otherwise uncovers the focal subject. If previous-unit binding "
    "unambiguously makes the pronoun the perceiving PC, carry that PC. The perceived NPC/location/"
    "object may still trigger a placeholder diagnostic if no matching hub exists, but do not drop "
    "the perceiving PC.\n"
    "4. Anti-expansion precedence: narrow PC beats beat roster expansion. Group words such as "
    "team, group, rest of the group, party, or Questionable Company do not trigger the_party when "
    "they appear inside a future plan stated by one PC, a command/instruction, a subordinate clause, "
    "reported speech, a destination phrase, or a sentence whose main concrete action belongs to "
    "one to three named PCs. Examples: \"Caelynn tells her to stop where she is and make camp; "
    "Karsemine will lead the team to her\" -> [caelynn, karsemine], not the_party. "
    "\"As Thrin and Caelynn move back, the swarm gives up\" -> [caelynn] plus npc_placeholder "
    "for Thrin if no NPC hub exists, not the_party.\n"
    "5. Explicit party / Roster copy rule (explicit_party): use [\"the_party\"] only when the "
    "party, group, team, or a party name from routing_context.pc_party_names is the actual "
    "collective actor of the sentence: acting, deciding, moving, resting, watching, preparing, "
    "or approaching together. The server expands \"the_party\" to routing_context."
    "session_pc_roster_slugs (GM-declared: optional recap frontmatter session_pc_roster, else "
    "campaign _party_registry.json session_pc_rosters; canonical order follows hub_manifest). "
    "Do not list individual PC slugs for a group beat; do not reconstruct the roster from recap "
    "names. Good: \"Questionable Company watches...\" -> [\"the_party\"]. "
    "\"The group decides to rest\" -> [\"the_party\"]. Bad: \"Karesmine will lead the team\" -> "
    "not the_party; assign Karesmine and any other named PC thread owner.\n"
    "6. implicit_party: if routing_context.active_collective_actor is \"the_party\", assign "
    "[\"the_party\"] only when the current unit is pronoun-led by they/the group/the team and "
    "describes continued movement, arrival, discovery, watching, resting, preparing, or travel. "
    "Do not apply active_collective_actor to pure scenery unless the unit says the party/group/they "
    "encounter, discover, approach, react to, or are affected by that scenery.\n"
    "7. Previous-unit binding for PC continuity (previous_unit_pc_continuation): carry at most "
    "one PC from the immediately previous sentence_unit when the current unit is pronoun-led or "
    "deictic-led (he/she/they/him/her/them/his/her/their/this/that/then/afterward/alarmed), the "
    "previous unit unambiguously binds that cue to one manifest PC, and the current unit continues "
    "the same local action or perception beat. Do not use previous-unit binding to assign the whole "
    "party, continue across ambient/object/location narration, override a new named focal actor, "
    "or infer a scene owner without textual support. Rationale must quote both the binding phrase "
    "from the previous unit and the pronoun/deictic cue from the current unit.\n"
    "8. Scene-owner continuity fallback (scene_owner_pc): assign a PC as scene owner only when "
    "one of these is true: (a) the unit contains an explicit phrase tying the event to that PC's "
    "ongoing scene, question, problem, search, conflict, or decision; (b) routing_context."
    "active_scene_owner_hubs explicitly lists that PC and the unit is pronoun-led, deictic-led, "
    "reported-speech, discovery, confrontation, search, or consequence text continuing that scene; "
    "or (c) routing_context.previous_unit_assignments plus pronoun/deictic text make the continuation "
    "unambiguous. Do not use scene-owner continuity to infer full-party routing. Do not use it for "
    "ambient scenery, object narration, or location description unless the PC/party explicitly "
    "encounters, discovers, approaches, reacts to, or is affected by it.\n"
    "9. Placeholder diagnostics: if no PC or party mode applies, use an appropriate "
    "placeholder diagnostic for the non-manifest focal subject. If a PC or the_party is assigned "
    "and the same unit foregrounds a distinct named NPC without a hub, keep the PC routing and set "
    "routing_diagnostic_bucket=npc_placeholder; do not treat PC+NPC as a separate routing mode. "
    "Otherwise set routing_diagnostic_bucket=null when "
    "assigned_hubs is non-empty.\n\n"
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

"""Versioned collective/relationship prompting experiment; not an entailment gate."""

from dataclasses import replace

from .extraction_profile import register_extraction_profile
from .worldbuilding_definition_observations import (
    GAZETTEER_DEFINITION_OBSERVATION_PROFILE,
)

_COLLECTIVE_FIDELITY = (
    " Keep each collective description source-extractive and scoped to that exact referent. "
    "Cite the source's naming clause plus the passages supporting each descriptive claim. "
    "Do not build a membership roster by pooling people from nearby NPC entries or role "
    "headings. A representative of commerce, agriculture, crafts or another domain is not "
    "therefore a member of a council, organization or guild; preserve the stated role in "
    "the person's description unless the source explicitly connects that person to the "
    "collective. Explicit leadership remains extractable. Preserve uncertainty and dissent "
    "rather than upgrading roles, beliefs or allegations into established membership. "
    "Two institutions mentioned in the same setting remain distinct candidates unless the "
    "source explicitly establishes their identity. Do not manufacture parenthetical aliases, "
    "institutional equivalence or membership from shared location, function or association. "
    "Do not enrich a collective description with facts whose only support is another "
    "candidate's generated description. Generic headings such as Key NPCs merely organize "
    "entries. An explicit relational heading such as Members of the Harbour Council can "
    "establish membership context for its scoped entries; cite both that heading and the "
    "named entry. Do not treat every heading as either a relationship or irrelevant text."
)
_RELATIONSHIP_FIDELITY = (
    " For each relation, identify the source clause or explicit relational heading and scoped "
    "entry connecting these exact two referents "
    "with this meaning and direction. A domain representative role alone does not state "
    "membership in a council or guild. Nearby entries, headings, shared location or "
    "function do not establish membership, ownership or institutional identity. Generated "
    "node descriptions and aliases are hypotheses, not extra evidence. Preserve explicitly "
    "stated leadership and other supported connections; do not discard them merely because "
    "other relationships remain unresolved. Keep institutions distinct unless the source "
    "explicitly identifies them as the same entity."
)

GAZETTEER_COLLECTIVE_SOURCE_FIDELITY_PROFILE = register_extraction_profile(
    replace(
        GAZETTEER_DEFINITION_OBSERVATION_PROFILE,
        profile_version="1.12",
        node_passes=tuple(
            replace(spec, instruction=spec.instruction + _COLLECTIVE_FIDELITY)
            if spec.pass_id == "collective_pass"
            else spec
            for spec in GAZETTEER_DEFINITION_OBSERVATION_PROFILE.node_passes
        ),
        edge_pass=replace(
            GAZETTEER_DEFINITION_OBSERVATION_PROFILE.edge_pass,
            instruction=(
                GAZETTEER_DEFINITION_OBSERVATION_PROFILE.edge_pass.instruction
                + _RELATIONSHIP_FIDELITY
            ),
        ),
        edge_review_pass=replace(
            GAZETTEER_DEFINITION_OBSERVATION_PROFILE.edge_review_pass,
            instruction=(
                GAZETTEER_DEFINITION_OBSERVATION_PROFILE.edge_review_pass.instruction
                + _RELATIONSHIP_FIDELITY
            ),
        ),
    )
)

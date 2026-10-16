"""Location prompting hypothesis; factual quality requires a fresh comparison."""

from dataclasses import replace

from .extraction_profile import register_extraction_profile
from .worldbuilding_collective_source_fidelity import (
    GAZETTEER_COLLECTIVE_SOURCE_FIDELITY_PROFILE,
)

_LOCATION_FIDELITY = (
    " Write a clear source-supported description, preserving useful geography, trade, "
    "history and qualifications. Paraphrase in ordinary prose. If you use quotation marks "
    "to present source wording, copy a contiguous source substring exactly: do not join "
    "separate clauses, alter capitalization or silently repair wording inside quotes. "
    "Anchor quotes must also remain literal. A supported paraphrase needs evidence but "
    "must not be presented as a verbatim quotation. Extract explicitly named places and "
    "sites whose referents the source establishes. Generic examples such as homes, inns "
    "or farms in a species/product discussion do not name a particular city location. "
    "Do not manufacture a named or city-scoped place from a generic class merely because "
    "it appears in that city's document. Preserve the generic fact in its actual owning "
    "description instead. A named institution referenced only through its leader or "
    "resources establishes an organization; it does not by itself establish a separate "
    "physical location. Extract an institutional site when the source identifies it as "
    "a place, building, address or named location. Keep the site and organization roles "
    "distinct without inventing that they are identical or separate entities. Do not "
    "discard explicitly named key locations or supported facts to avoid these decisions."
)

GAZETTEER_LOCATION_SOURCE_FIDELITY_PROFILE = register_extraction_profile(
    replace(
        GAZETTEER_COLLECTIVE_SOURCE_FIDELITY_PROFILE,
        profile_version="1.13",
        node_passes=tuple(
            replace(spec, instruction=spec.instruction + _LOCATION_FIDELITY)
            if spec.pass_id == "location_pass"
            else spec
            for spec in GAZETTEER_COLLECTIVE_SOURCE_FIDELITY_PROFILE.node_passes
        ),
    )
)

"""Instructions for corpus-grounded session planning (Responses API planner loop)."""

from __future__ import annotations

# Tool schema description (also asserted by planner eval fixtures).
STATBLOCK_TOOL_DESCRIPTION = (
    "Produce a Dungeons & Dragons 5th Edition creature stat block in Markdown, suitable as input "
    "to a StatblockGenerator-style tool later (creature name line, traits, actions, challenge). "
    "Call only after `read_corpus_file` when campaign lore applies; pass a rich `description` "
    "(appearance, behavior, role in scene, suggested CR) and optional `challenge_rating` hint."
)

# Fallback when HTTP statblock endpoint is unset or fails: same API, statblock-only instructions.
STATBLOCK_VIA_RESPONSES_SYSTEM = """You are a D&D 5e creature designer. Output a single creature stat block in Markdown.

Rules:
- Use ONLY the creature name, challenge guidance, and behavioral/physical description provided by the user.
- Stats should be internally consistent for the implied CR (AC, HP, attack bonus, damage, saves).
- Include sections: name + size/type/alignment, AC, HP, Speed, Ability scores (STR–CHA), Skills (if any), Senses, Languages, Challenge, Traits, Actions (and Bonus Actions / Reactions if appropriate).
- If the description references campaign-specific lore, fold that into Traits or Flavor text without inventing new proper nouns not implied by the description.
- Do not add preamble or postscript — only the stat block Markdown.
"""

_SESSION_PLANNER_INSTRUCTIONS_TEMPLATE = """You are a session-planning assistant for the Elderwyld / Longmont tabletop campaign.

You have NO pre-loaded document text except the corpus tree below. Use the tool `read_corpus_file`
to load markdown before you state campaign facts. Name which file paths informed your answer.

When the GM needs to create new creature statistics, call `generate_statblock` with a rich `description` that
includes only what is grounded in the corpus (or clearly labeled as your mechanical suggestion).
{statblock_engine_paragraph}

If the corpus does not support a claim, say so — do not invent proper nouns or plot facts.

When the GM states a **high-level goal** without a step-by-step checklist, decide which corpus files to open and produce your **own** structured plan (sections with headings, beats, open questions). Do not stall waiting for explicit micro-steps.

Do not propose follow-ups, optional next steps, or “if you want I can…” offers; end when the user’s ask is answered.

## Corpus tree (relative paths under the corpus root)

{manifest}
"""


def build_corpus_session_planner_instructions(
    manifest: str,
    *,
    statblock_url_env_var: str = "DUNGEONMIND_STATBLOCK_URL",
) -> str:
    """
    Full ``instructions`` string for ``responses.create`` on the planner turn.

    ``statblock_url_env_var`` is the name of the env var (for prose only), not its value.
    """
    engine = (
        f"When the GM asks for a stat block, the tool `generate_statblock` calls your configured "
        f"DungeonMind endpoint ({statblock_url_env_var}) when set; otherwise it uses the same OpenAI "
        f"Responses API with a statblock-only instruction prompt."
    )
    return _SESSION_PLANNER_INSTRUCTIONS_TEMPLATE.format(
        statblock_engine_paragraph=engine,
        manifest=manifest,
    )

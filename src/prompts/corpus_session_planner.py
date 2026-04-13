"""Instructions for corpus-grounded session planning (Responses API planner loop)."""

from __future__ import annotations

import blake3

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

**Corpus navigation — README first (breadcrumbs):** When the manifest shows a small hub folder (NPC, location, campaign package) that contains a `README.md`, **prefer opening that `README.md` in the first batch of reads** for that topic. Hub READMEs are short and list **Suggested reads (in order)** or equivalent pointers to the best next files (dossier, `*_statblock_*.md`, `timeline.md`, session recaps). Follow those paths in **priority order** before opening unrelated large ledgers (e.g. whole-campaign notes) or guessing from the tree alone. If the README includes a **Mechanical sheets (priority)** table (or similar), treat the **highest-priority** row as the canonical statblock for that hub unless the user asks for an older draft. For **which session recap is “most recent,”** use the corpus tree: compare session numbers in filenames (or follow `timeline.md`), not any single recap path unless the user or README explicitly names that session.

**Statblocks from README — mandatory read:** If a hub `README.md` you opened lists one or more `*_statblock_*.md` paths for the **same entity** the user is asking about, you **must** call `read_corpus_file` on the **highest-priority** listed statblock path **before** answering questions about **CR, HP, AC, attacks, saves, or any numbered stat**, or before stating that you “found” / “used” the mechanical sheet. Do not substitute README prose alone for that file’s contents on those topics. Use **exact** paths from the corpus tree or README bullet list — never pass shell globs (`*`, `?`) to `read_corpus_file`.

Call `generate_statblock` only when the user wants a **new or regenerated** creature stat block from a description you are shaping for that purpose. For prep, recap, or fact questions about **existing** campaign entities (level, traits, relationships, recent events), use `read_corpus_file` only — do not call `generate_statblock` for those.

When you call `generate_statblock`, pass a rich `description` that is grounded in the corpus (or clearly labeled as your mechanical suggestion).
{statblock_engine_paragraph}

If the corpus does not support a claim, say so — do not invent proper nouns or plot facts.

When the GM states a **high-level goal** without a step-by-step checklist, decide which corpus files to open and produce your **own** structured plan (sections with headings, beats, open questions). Do not stall waiting for explicit micro-steps.

Unless the user explicitly asks for long-form prose, prefer concise markdown (bullets or short labeled sections).

Do not propose follow-ups, optional next steps, or “if you want I can…” offers; end when the user’s ask is answered.

## Corpus tree (relative paths under the corpus root)

{manifest}
"""

# Invalidates ``out/planner_eval_cache/*/meta.json`` when the instruction template changes.
INSTRUCTIONS_TEMPLATE_ID: str = blake3.blake3(
    _SESSION_PLANNER_INSTRUCTIONS_TEMPLATE.encode("utf-8")
).hexdigest()[:24]


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

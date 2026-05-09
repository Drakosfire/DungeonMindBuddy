"""Inline-recap breadcrumb prompts for the under-tagged continuation experiment.

This module keeps both the control prompt (mirroring the wording shipped in
``Docs/Plans/EXPERIMENT-Inline-Recap-Breadcrumbing.md`` and used by the prior
indexed cohort) and the variant prompt that adds an
``UNDER-TAGGED CONTINUATION CHECK`` rule.

Both prompts share an envelope that injects:

* the source recap body,
* the frontmatter-only entity index pulled from the manual baseline (route table
  the model is allowed to use),
* the schema/route grammar the normalizer enforces.

The model is told to return a single fenced block containing the breadcrumb
markdown artifact. The runner extracts the fenced block before writing it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

PROMPT_VARIANT_CONTROL = "control_v1"
PROMPT_VARIANT_CONTINUATION = "under_tagged_continuation_v1"
PROMPT_VARIANT_PRONOUN_RESOLUTION = "pronoun_resolution_v1"

ALLOWED_VARIANTS = {
    PROMPT_VARIANT_CONTROL,
    PROMPT_VARIANT_CONTINUATION,
    PROMPT_VARIANT_PRONOUN_RESOLUTION,
}


_SHARED_RULES = """\
You are generating an inline-recap breadcrumb artifact (schema
``dmb_recap_breadcrumbs_v1``) over a Dungeons & Dragons session recap.

Output contract:
1. Reuse the provided frontmatter verbatim. Append nothing to the frontmatter
   except updating ``counts_by_subject_type.inline_tags`` to match the actual
   counts you emit. Keep frontmatter keys and indentation exactly as shown.
2. Place inline tags **immediately after** the smallest source-derived span
   that should route to that hub. Do **not** replace the recap text with tags
   and do **not** rewrite the prose — the recap body is the canonical source
   and the breadcrumb plain text (with tags stripped and whitespace
   normalized) must equal the recap body. Concretely: every word in the
   source recap must appear in your output in the same order. Preserve source
   spelling, punctuation, line breaks, and typos exactly; do not "clean up"
   grammar or formatting.
3. Allowed tag types: ``PC``, ``NPC``, ``Location``, ``Party``,
   ``NewHubCandidate``. Use only routes that appear in the provided entity
   index (or the existing manual baseline's ``new_hub_candidates`` /
   ``unresolved_open_questions`` block) — do not invent new routes.
4. Tag grammar: ``[TagType][corpus-relative hub route]``. Routes must match
   the exact strings from the entity index; the trailing slash on directory
   routes is significant.
5. Selectivity: tag spans with durable retrieval value (table-significant
   actions, discoveries, relationship beats, location-state changes,
   reputation beats, collective decisions, affected groups, unresolved
   durable entities). Do not tag every mere mention.
6. Multi-hub: when the same span is durable for multiple hubs, emit multiple
   tags after that span (e.g. ``[NPC][...captain_lysandra_ironveil/]
   [NewHubCandidate][.../Voices Tower/]``). Tag order does not matter, but
   keep them on the same span.
7. Party policy: use ``[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]``
   only when the span has durable retrieval value for the collective party.
   Do not tag every generic ``the group`` / ``the heroes`` sentence; if
   specific PCs are acting separately, tag those PCs instead.
8. Output **only** the full breadcrumb markdown (frontmatter + body) inside
   a single fenced block:

   ```breadcrumb
   ---
   schema: dmb_recap_breadcrumbs_v1
   ...frontmatter...
   ---
   # Session 20 Recap

   ...body...
   ```

   No prose before or after the fenced block.
9. Mandatory self-check before you finalize:
   - Strip all tags mentally from your draft body.
   - Compare the stripped body against the source recap body.
   - If any character-level differences remain (added words, dropped words,
     punctuation rewrites, typo fixes, reordered phrases), discard the draft
     and regenerate.
"""

_CONTINUATION_ADDENDUM = """\

UNDER-TAGGED CONTINUATION CHECK (extra rule for this variant):

After tagging a clause that names a durable subject (a PC, NPC, named
Location, or NewHubCandidate), re-read the immediately following clauses in
the same paragraph. If a follow-on clause contains a pronoun (``she``,
``her``, ``he``, ``him``, ``they``, ``it``) or an unattributed object/effect
(``the drawing``, ``the blueprint``, ``the antidote``, ``the spell``,
``the camp``, ``the storm``) and the clause is still semantically about the
same durable subject — for example because that subject is the one who made
the object, holds the effect, owns the scene, or is being inspected — then
the follow-on clause carries the same durable retrieval value. Append the
subject tag to that follow-on clause, in addition to any tags already
warranted by other hubs (location, PC observer, NewHubCandidate).

Worked sentinel example (do **not** copy verbatim if the source recap
diverges; this is a pattern):

  Source: "She finds Lysandra drawing in the dirt. While the tea is being
  prepared, Caelynn takes a closer look at the drawing. It appears to be a
  top-down blueprint of a tower and is very well done."

  Correct tagging (note the ``captain_lysandra_ironveil`` tag carried into
  the next two clauses because the drawing is Lysandra's):

  ``She finds Lysandra drawing in the dirt. [PC][.../caelynn/]
  [NPC][.../captain_lysandra_ironveil/] While the tea is being prepared,
  Caelynn takes a closer look at the drawing. [PC][.../caelynn/]
  [NPC][.../captain_lysandra_ironveil/] [NewHubCandidate][.../Voices Tower/]
  It appears to be a top-down blueprint of a tower and is very well done.
  [PC][.../caelynn/] [NPC][.../captain_lysandra_ironveil/]
  [NewHubCandidate][.../Voices Tower/]``

This rule MUST NOT spread named-subject tags onto unrelated sentences. If
the next paragraph starts a new scene with a new subject, drop the tag. If
``she`` plausibly refers to a different recently-named character (e.g. a
different PC took over the action), do not carry forward.

BACKWARD-ANAPHORA CHECK (extra guard for shelter/inside-style clauses):

Before finalizing a paragraph, also re-read the immediately PRECEDING clause
of each named-subject sentence you tagged. If the preceding clause contains
scene-anchor wording that is semantically about the same subject but names only
an observer or indirect setup (for example: "Caelynn approaches the makeshift
shelter and hears mumbling from inside." right before "She finds Lysandra
drawing in the dirt."), then add that subject tag to the preceding clause too.

Apply this only when all are true:
1) the preceding clause is in the same paragraph and directly adjacent in the
   local narrative flow,
2) the following clause clearly resolves the subject identity,
3) there is no strong evidence that the preceding clause belongs to a different
   subject/scene.

If uncertain, leave the clause unchanged.
"""

_PRONOUN_RESOLUTION_ADDENDUM = """\

PRONOUN-RESOLVED BREADCRUMBS (extra rule for this variant):

After the first pass of span tagging, audit every sentence-unit that contains a
pronoun or possessive pronoun (``she``, ``her``, ``hers``, ``he``, ``him``,
``his``, ``they``, ``them``, ``their``, ``theirs``, ``it``, ``its``).

If the local paragraph unambiguously resolves that pronoun to a named PC, NPC,
party, Location, or NewHubCandidate already listed in the entity index, append
that subject's breadcrumb tag to the pronoun-led span even if the entity's name
does not appear in the sentence itself. This is a retrieval contract: a later
agent asking about "Lysandra's memory" must be able to find a sentence such as
"She tells Caelynn..." when the paragraph makes clear that "She" is Lysandra.

Use these constraints:

1. Stay local. Resolve within the same paragraph, or the immediately adjacent
   sentence when the paragraph is one continuous dialogue/action beat.
2. Require an unambiguous antecedent. If two plausible referents share the same
   pronoun and the text does not disambiguate, do not add a tag.
3. Preserve roles. If a sentence has multiple pronouns with different referents,
   tag every durable resolved subject that participates in the beat, but do not
   invent roles or rewrite the prose.
4. Do not spread tags across a scene break, paragraph break, or topic switch.
5. Do not tag every pronoun. The normal selectivity rule still applies: only add
   breadcrumbs when the pronoun-led sentence has durable retrieval value.

Positive sentinel pattern:

  "Caelynn relays her request and Sara calls Lysandra. She tells Caelynn that
  all she could hear was mumbling about the forest leaving..."

  Correct: the second sentence should carry tags for Caelynn, Sara, Lysandra,
  and the Migrating Forest when those routes are available, because the local
  communication chain and memory report are durable retrieval evidence.

Negative sentinel pattern:

  "Marla approaches Caelynn... Ephanna quickly intervenes..." followed by a new
  scene or a different actor. Do not carry Marla, Caelynn, or Ephanna into the
  next unrelated pronoun merely because they were nearby in the paragraph.
"""


@dataclass(frozen=True)
class BreadcrumbPrompt:
    variant: str
    system_text: str
    user_text: str


def _build_system_text(*, variant: str) -> str:
    if variant == PROMPT_VARIANT_CONTROL:
        return _SHARED_RULES
    if variant == PROMPT_VARIANT_CONTINUATION:
        return _SHARED_RULES + _CONTINUATION_ADDENDUM
    if variant == PROMPT_VARIANT_PRONOUN_RESOLUTION:
        return _SHARED_RULES + _CONTINUATION_ADDENDUM + _PRONOUN_RESOLUTION_ADDENDUM
    raise ValueError(f"unknown prompt variant: {variant!r}")


def build_breadcrumb_prompt(
    *,
    variant: str,
    recap_body: str,
    frontmatter_yaml: str,
) -> BreadcrumbPrompt:
    """Compose the system + user message pair for a breadcrumb generation call."""
    if variant not in ALLOWED_VARIANTS:
        raise ValueError(
            f"variant must be one of {sorted(ALLOWED_VARIANTS)}; got {variant!r}"
        )

    user_text = (
        "Frontmatter to reuse verbatim (update only the inline-tag counts after "
        "you have finished tagging):\n\n"
        "```yaml\n"
        f"{frontmatter_yaml.strip()}\n"
        "```\n\n"
        "Source recap body (canonical text — every word must appear in your "
        "output in the same order; tags go AFTER spans, never replace text):\n\n"
        "```recap\n"
        f"{recap_body.strip()}\n"
        "```\n\n"
        "Return the full breadcrumb markdown inside a single ```breadcrumb fenced "
        "block.\n"
    )

    return BreadcrumbPrompt(
        variant=variant,
        system_text=_build_system_text(variant=variant),
        user_text=user_text,
    )


_ROUTING_ONLY_SYSTEM_HEADER = """\
You assign inline breadcrumb routes to fixed recap ``units`` (pre-segmented clauses).
Downstream tooling injects ``[TagType][route]`` markers for you — you MUST NOT output
recap prose or markdown.

Structured output (JSON only — no fences, no commentary):
- Emit one object matching ``dmb_breadcrumb_route_assignments_v1``:
  * ``schema``: literal ``dmb_breadcrumb_route_assignments_v1``
  * ``source_recap_path``: exact string from the user message
  * ``assignments``: array of ``{ "unit_id": "...", "tags": [ { "tag_type": "...", "route": "..." } ] }``
- Omit units that need no tags. Each ``route`` must be copied EXACTLY from the
  allowlist JSON (slashes and trailing ``/`` are significant).

Tagging rules (same intent as full inline breadcrumb ingest):
3. Allowed tag types: ``PC``, ``NPC``, ``Location``, ``Party``, ``NewHubCandidate``.
4. Selectivity: tag units with durable retrieval value (table-significant beats,
   discoveries, relationship beats, location-state changes, collective decisions).
   Do not tag every mention.
5. Multi-hub: emit multiple tags in one unit when warranted.
6. Party policy: use ``Party`` only when the beat is durable for the collective,
   not for every generic ``the group`` line.
7. Ground tags in the unit's ``text``; do not invent entities or routes.
"""


def _build_route_system_text(*, variant: str) -> str:
    if variant == PROMPT_VARIANT_CONTROL:
        return _ROUTING_ONLY_SYSTEM_HEADER
    if variant == PROMPT_VARIANT_CONTINUATION:
        return _ROUTING_ONLY_SYSTEM_HEADER + _CONTINUATION_ADDENDUM
    if variant == PROMPT_VARIANT_PRONOUN_RESOLUTION:
        return _ROUTING_ONLY_SYSTEM_HEADER + _CONTINUATION_ADDENDUM + _PRONOUN_RESOLUTION_ADDENDUM
    raise ValueError(f"unknown prompt variant: {variant!r}")


def build_breadcrumb_route_prompt(
    *,
    variant: str,
    source_recap_path: str,
    recap_body: str,
    frontmatter_yaml: str,
    units: list[dict[str, object]],
    allowed_routes: list[str],
) -> BreadcrumbPrompt:
    """Structured routing-only prompt: model returns ``BreadcrumbRouteAssignmentsV1`` JSON."""
    if variant not in ALLOWED_VARIANTS:
        raise ValueError(
            f"variant must be one of {sorted(ALLOWED_VARIANTS)}; got {variant!r}"
        )
    routes_json = json.dumps(allowed_routes, indent=2, ensure_ascii=False)
    units_json = json.dumps(units, indent=2, ensure_ascii=False)
    user_text = (
        f"source_recap_path (repeat verbatim in output JSON): {source_recap_path!r}\n\n"
        "Allowlisted routes (EXACT strings for the ``route`` field):\n```json\n"
        f"{routes_json}\n```\n\n"
        "Recap body (context only — do not echo or paraphrase):\n```recap\n"
        f"{recap_body}\n```\n\n"
        "Units to assign (JSON):\n```json\n"
        f"{units_json}\n```\n\n"
        "Frontmatter entity index (context only):\n```yaml\n"
        f"{frontmatter_yaml.strip()}\n```\n"
    )
    return BreadcrumbPrompt(
        variant=variant,
        system_text=_build_route_system_text(variant=variant),
        user_text=user_text,
    )


_FENCE_RE = re.compile(
    r"```(?:breadcrumb|markdown|md)?\s*\n(.+?)```",
    re.DOTALL,
)


def extract_breadcrumb_markdown(text: str) -> str:
    """Pull the breadcrumb markdown out of a fenced reply.

    Falls back to the full text if no fenced block is present (some models drop
    the fence even when asked).
    """
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip() + "\n"
    return text.strip() + "\n"

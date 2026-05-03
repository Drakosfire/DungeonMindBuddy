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

import re
from dataclasses import dataclass

PROMPT_VARIANT_CONTROL = "control_v1"
PROMPT_VARIANT_CONTINUATION = "under_tagged_continuation_v1"

ALLOWED_VARIANTS = {PROMPT_VARIANT_CONTROL, PROMPT_VARIANT_CONTINUATION}


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
   source recap must appear in your output in the same order.
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

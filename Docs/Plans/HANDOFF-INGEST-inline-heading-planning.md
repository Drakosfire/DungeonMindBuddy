# INGEST: withhold planning headings carrying inline text

Status: ACTIVE implementation under the user’s ingestion-quality goal and
PRIME’s adopted bounded source-format contract. PR2040 merged as
`22a00434c886b5abc57e3725682777e29f21aaf9`; this checkout was re-anchored to that
fetched `origin/main` before activation. No runtime/resource-effects lease.

Base: `1b729d40784fc29c23cf0400c265536734fb23f2`.
PR2042 merged above PR2040 during regression reproduction; the disjoint
hydration change was fast-forwarded before implementing the owner correction.
Branch: `codex/recap-inline-planning-headings`.
Checkout: `/home/drakosfire/Projects/.codex/249d/DungeonMindBuddy`.

Outcome: explicit Markdown planning headings whose normalized title is a
supported planning label followed by a colon must withhold their inline payload
and content at the existing heading depth. Played prose must resume at the
explicit balanced bold/underscore Recap marker containing its colon, including
same-line prose. These entry and exit rules are indivisible for the pinned S6
source: entry-only would incorrectly hide its entire played recap.

Topology: serial after PR2040, then the separately proposed recap edge-guidance
slice. No stacked implementation. Reuse the current checkout on a new codex/
branch from fetched origin/main; record exact base and merge SHA on activation.
PR2041 compact-preview deletion is already in the base. PR2042 hydration
cleanup is disjoint and also in the re-anchored base. Neither changes this
source-format contract. Open PRs/leases checked on activation; no parser/profile
overlap was found.

## Structural contract adopted by PRIME

- Supported planning labels are the existing Looking Ahead, Next Beats,
  Planning Notes and Prep Notes. A Markdown heading with that normalized label
  followed by a colon starts planning even when payload follows the colon.
- Existing peer/parent Markdown heading exit policy is unchanged. Do not infer
  that arbitrary peer headings are planning from payload meaning or source IDs.
- At an unquoted/unfenced block-line start, a matching bold/underscore marker
  enclosing Recap AND its colon may close planning and carry prose after the
  closing marker: `**Recap : **The team arrived.` or `__Recap:__The team arrived.`
- `**Recap**: proposed future scene` keeps the colon outside the marker and is
  not this boundary. Plain `Recap: arbitrary prose` remains non-structural.
- Existing label-only and Markdown Recap exits, split-bold compatibility,
  quotations/lazy quotations, fences and source-row coordinates remain intact.
- Never decide authority by the meaning of the payload, Gold, names or IDs.

## Exclusive expected write set

- src/graph_memory/extraction/recap_source_authority.py
- tests/test_recap_source_authority.py
- tests/test_recap_planning_section_pipeline.py
- Docs/Plans/HANDOFF-INGEST-inline-heading-planning.md
- Docs/Plans/HANDOFF-INGEST-standalone-recap-planning.md, only truthful predecessor
  settlement after its actual merge is known.

No extraction profile, shared predicate catalog, schema, source artifact, Gold,
provider adapter, runtime deployment, database, publication or PRIMARY changes.
No new producer, representation, checker, fallback or source rewrite.

## Validation

Reproduce with neutral heading-payload and Recap-prefix examples before the fix.
Cover all supported planning names and case/whitespace, Markdown depth,
inside-colon vs outside-colon emphasis, quote/lazy quote/fence controls and CR/LF
source coordinates. Use ordinary canonical source spans and fixture output to
prove planning is absent from prompts and returned planning citations are
rejected whole, while played candidates remain.

Replay pinned S6 source SHA
`a6849dbc9bad2045f728d7514deae3fb99fca38495281dfa126806d7087b5bf8`:
both planning payload rows must be withheld and every existing Gold witness row
kept. Preserve original text/canonical span IDs and offsets. Recheck availability
of all 245 retained Gold witnesses across C1S1-10 and report the scope honestly:
provider-free admission proof is not model recall/publication acceptance.

Run owning focused tests and lint; inspect cumulative base-to-head diff, commit,
push and open one reviewable PR for PRIME. Merge/delivery remain PRIME-owned.
Fresh isolated extraction follows coordinated exact runtime/resource qualification;
this source slice does not authorize provider or database effects.

## Implementation evidence

The new source-format regressions reproduced 17 failures before the correction,
including planning payloads appearing in ordinary pass prompts. The correction
uses the existing heading-depth owner and adds only the explicit marked Recap
prefix grammar; it does not infer intent from prose or add another producer.
Focused parser, canonical-span pipeline, source-quote representation and category
extractor checks pass: 132 tests. Ruff and cumulative diff checks pass.

A provider-free replay uses the retained artifact/revision IDs and source bytes
for C1S1–10. Exactly the two S6 planning payload rows become newly withheld; all
245 existing Gold witness groups remain mapped to retained canonical rows. Every
other session retains its previous partition. Inputs and row IDs are unchanged.
Private proof SHA256:
`00e39319aa69db2bc38da6c229088b6bf91f5f062bd4bfe42fb4df06a474f6bd`.
This verifies source admission only, not actual fresh model recall, semantic Gold
completeness, publication or ordinary-answer acceptance.

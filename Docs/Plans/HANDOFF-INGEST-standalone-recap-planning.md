# INGEST: preserve standalone recap planning boundaries

Status: ACTIVE implementation, authorized by the user's ingestion/Gold goal.
PRIME transferred this bounded follow-up to ADVERSARY and confirmed no competing
source-code lease. PRIME owns independent review, merge and runtime delivery.

Base: `origin/main@e3878370db6a8c87e0be4f9bfdc3a465aa1800bd`.
Branch: `codex/recap-standalone-planning`.
Checkout: `/home/drakosfire/Projects/.codex/249d/DungeonMindBuddy`.
Topology: serial, one independently reviewable PR, no unmerged dependency.

## Outcome and boundary

A label-only `Next Beats :` paragraph followed by blank lines must keep its
following preparation paragraphs out of recap provider prompts and played-canon
candidates. The same rule applies to the existing Looking Ahead, Planning Notes
and Prep Notes labels, including balanced bold/underscore forms. An explicit
standalone plain/bold Recap label or Markdown Recap heading resumes played prose.
Label-only sections have no declared heading depth: their detail headings and
blank paragraphs stay planning until that explicit Recap boundary. Existing
Markdown section-depth rules and paragraph-scoped inline notes remain intact.
Quoted markers and markers in fenced code do not switch authority. Mixed spans
and model claims citing a withheld span remain deferred whole; original source
text, canonical IDs, quotes, offsets and captured model output are preserved.

The retained Session 5 observation `f71a13a369aba383ad613e9c19f619083d154810881d78010ba38dcbdf5466ef`
proves the failure at this owner: a standalone label was withheld but a later
paragraph became positive evidence after a blank line reset the inline flag.
The frozen capture and Gold are private evaluator evidence, not fixtures to edit
or reinterpret as a passing fresh run.

## Exclusive expected write set

- `src/graph_memory/extraction/recap_source_authority.py`
- `tests/test_recap_source_authority.py`
- `tests/test_recap_planning_section_pipeline.py`
- This handoff.

The existing pipeline test is the integration owner for prompt withholding and
whole-claim rejection; no source-quote representation test needs modification.
No product schema/profile, provider adapter, event representation or fallback is
added. PRIME's data-restoration lane is disjoint. No provider, PRIMARY, shared
fixture, publication or runtime lease is granted by this implementation handoff.

## Validation and delivery

Reproduce the failure in parser tests and through the ordinary category pipeline
with canonical source spans and a fixture client that tries to return a claim
from the withheld paragraph. Verify that planning text is absent from prompts,
the injected claim is deferred, and played Recap material remains available.
Cover all supported marker forms, multiline sections, fences, quoted/prose
markers, existing inline behavior and the non-recap profile boundary. Recheck
the retained Session 5 source through the pure partition owner without modifying
the original source, Gold, candidate or raw captures. This is a deterministic
owner replay, not new ingestion or publication acceptance.

Implement, run focused checks, inspect the cumulative base-to-head diff, commit,
push and open the PR for PRIME. Merge/runtime adoption and subsequent isolated
ingestion/publication verification remain separate coordinated steps. Session 4
and Session 5 precision, source-handle and representation gaps remain outstanding.

## Implementation evidence

The new regression matrix reproduced 25 failures before the fix, including the
ordinary pipeline prompt-withholding test. Focused parser, planning pipeline,
source-quote representation and category extractor checks passed: 83 tests.
Existing inline-note, fenced/quoted marker and worldbuilding behavior is covered
by those controls.

A provider-free replay of the frozen Session 5 source now withholds the exact
planning paragraph and retains all five played Recap paragraphs. Applying the
existing whole-claim filter to the frozen candidate defers `loc_the_city`,
`group:shephards`, `edge_034` and the single planning excerpt. No original source,
Gold or candidate bytes changed. Private proof SHA256:
`deb585b99aea12522925ee0f02c0c05b6c8b4450b460f359f7fdc169fc45da10`.
This proves the deterministic authority boundary only; fresh inference and
publication quality remain unproven until coordinated post-review verification.

## Independent review correction

PRIME held head `20a26cd71183ca54d792bcf2b9a931be59ffdadb` because a
CommonMark lazy blockquote continuation containing `Next Beats:` could start a
persistent planning section and hide the next played paragraph. A lazy quoted
`Recap:` could also prematurely end real planning. Four new parser cases
reproduced these failures before the correction. The existing pinned
`markdown-it-py` dependency now supplies blockquote line ranges, including lazy
continuations; quoted lines cannot change authority, while existing outer
planning still covers them. No new dependency or Markdown heuristic was added.

Parser controls include plain/bold lazy labels, lazy quoted Recap, and a genuine
standalone planning label after the quote ends. The ordinary canonical-span
pipeline now verifies that the subsequent played paragraph remains in every
provider prompt and its returned location survives. Focused checks: 89 passed.
The retained Session 5 owner replay remains identical to the earlier proof:
all five played paragraphs kept and the same planning claims deferred. Original
private evidence is unchanged. Independent review of the corrected head remains
required before merge/delivery; these checks are not fresh extraction acceptance.

The second independent review held `8b8324776d88a968eef866fe6115b6de9e6cb7eb`:
CommonMark line maps count CR/LF boundaries while existing source rows also count
Python Unicode line separators. With such separators before a lazy quote, the
quote mask missed its label. The correction translates CommonMark boundaries
through original character offsets to the unchanged source-row line basis.
Eight Unicode separator cases reproduced the failure before correction. LF,
CRLF and CR controls and a canonical-span pipeline Unicode case now pass along
with the existing checks: 104 focused tests, Ruff and cumulative diff check.
The pure retained Session 5 proof remains unchanged. No source bytes, row IDs,
quote offsets, frozen candidate or Gold were rewritten. The independently found
heading-with-inline-planning-payload gap is a separate serial successor, not part
of this PR; edge-guidance work follows that evidence-admission correction.

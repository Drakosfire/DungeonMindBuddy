# Build lore drafts from the conversation

Active on `codex/aw10-prior-citation-runtime` under the operator's AW10 goal.
Base for the citation resolver is `df54c12e5`. Main through `a89fee7b1` has
no overlapping Build runtime changes. The independent benchmark definition is
[#4310](https://github.com/Drakosfire/DungeonMindBuddy/pull/4310). Ship the
runtime on [#4312](https://github.com/Drakosfire/DungeonMindBuddy/pull/4312)
after the integrated turn and save pass. The citation resolver by itself
does not qualify the runtime.

## Implementation boundary

- Own the route choice in the existing Build requested-work decision. Bind
  an explicit standalone page destination and distinguish synthesis of prior
  conversation from requested research before source acquisition. Preserve
  historical requested-work proof vocabulary. Brainstorming does not earn
  page authority, and ambiguous titles stay on the existing clarification path.
- For synthesis, freeze the bounded preceding completed turns through the
  APP conversation owner. Bind every offered support to the completed turn,
  its completion digest and citation ordinal, and resolve it against that
  turn's validated execution using the exact retained extent resolver. A
  transcript string or model-authored URL grants no citation authority.
  Require the same World, active conversation, and preceding sequence.
- Carry the prior evidence through one durable admission in the producing
  Build execution, before the writer is authorized. The writer frame and
  retained completion validation must derive their support catalogue from
  that same admission. Use request-local aliases with exact claim and passage
  text. Keep storage addresses and digests outside the provider prompt. Keep
  proposal and uncertainty segments distinct from supported facts.
- The no-retrieval terminal proof must participate in the current exact
  writer selection validation. It must refuse a research-route decision,
  an unresolved target, or any attempt to substitute another conversation.
  Preserve the existing source acquisition path for explicit research.
- Retain the original citation reopening owner. A carried citation resolves
  the same immutable source extent with fresh live World authorization when
  clicked. Do not forge source-read events in the new turn. The existing save
  digest must cover the draft and its citation bindings. Confirmation keeps
  its transaction and repeat-receipt behavior.

Write scope is the Build semantic routing and harness, APP native Build
execution and writer evidence/validation, exact citation readback and lore
confirmation, the corresponding owner tests, and this handoff. The narrow
resolver preparation already shares exact extent checking with the ordinary
citation opener. Keep old rows readable without changing their older proof.

## Verification

Use the frozen 12-turn prefix from the benchmark and disposable APP and Core
state. On the existing ordinary Build harness, assert that Graph/corpus and
related-page readers never run for the named Maelthor synthesis turn, while
both Turn 8 passages remain exact. Prove the displayed draft preserves the
open questions and authored hypotheses, zero writes before confirmation,
one exact save with cited readback, and the same receipt on repeat. Exercise
wrong owner, wrong digest, and intervening conversation/revision changes before
adopting any speed claim. No primary data writes, hosted conversation posts,
or case-specific routing.

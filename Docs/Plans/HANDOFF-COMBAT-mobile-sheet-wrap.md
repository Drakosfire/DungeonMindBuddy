# Combat mobile sheet wrapping

ACTIVE under the user's responsive Combat implementation and passing-merge
assignment. Root owns fc67 on codex/combat-mobile-sheet-wrap, based on
eb048089ff34a18e1692e16d3f1971d5bd0f4ec8. Serial after merged #4282.
Read-only owner #3668 does not overlap.

At a 390-pixel viewport the 20-participant Mireward fixture kept the roster's
scroll inside its table and the document fit. The actual original Karsemine
Markdown overflowed the overlay by 18 pixels, with a long slash-delimited
term overhanging its paragraph and a fixed single-line action header.
Allow the Combat sheet header and original Markdown to wrap inside both
presentation modes. Keep selectors limited to Combat.

Write lease: this handoff and apps/live-control-ui/src/combat/combatRoster.css.
No template, shared Markdown styles, routes, authority or production writes.
Prove the same crowded browser width, statblock content, viewport and panel
widths, turn controls and Escape focus return. Qualify the exact commit and
request independent review. Hosted publication continues under the runbook
after this slice.

# STATBLOCK — coherent manual HP editing

## Merged and live; serial successor active

#1620 merged/live at `a6684f1aedff28b46a32770dc32b08b60bfb5bae` after one
Bugbot approval of `43094bace6289a8a7e4393e800fbcc71cafc6cee`. Real HP16→28 Save,
original/new reopen and protected restart passed;1760 APP rows/native rows/79 product
files/17 frozen components retained. This lease is released; B is ACTIVE under
[exact-version adoption](HANDOFF-COMBAT-exact-version-adoption.md).
Original activation: PRIME activates this live-discovered repair under the operator's existing manual
revision goal. Base `3389249e9cdf07bd9ee89aa01151605eb82d67b5` (#1619), existing
buddy-context-loop checkout, branch `codex/statblock-hp-edit-consistency`.
No competing open implementation edits these paths; one serial PR, no new environment.

#1619 merged after two Bugbot judgments, exact approved head
`7523cecaae3595177a05cbf451cc3d5407add8d5`. API/UI5202 now run its merge with
APP0049/native0017/Core617635c/DMSf95e unchanged. Real ordinary shared-tool UI
proved dirty edit recovery, validation, one immutable armor successor, original
AC13/new AC16 reopen and zero new agent turns. All four encounters and both World
associations remained byte-identical. Protected API restart preserved1759 APP rows,
all native rows,79 product files and17 frozen source components.

Live HP16→28 was refused: the existing editor changes displayed_average without
updating its typed dice formula. The new saved editor also hides the returned
validation issues. Armor-only Save does not close HP-edit acceptance. Fix this
before B adoption; connected Conks/Sheep/J1–J6 acceptance remains open.

## Contract and invariant critique

The shared HP control always means maximum HP, never a raw dice modifier.
For formula HP, preserve dice count/type and explicitly disclose that changing
maximum HP adjusts its modifier to yield the selected average. Compute with the
producer rule floor(count*(die+1)/2)+modifier; update displayed_average only if
present. For fixed HP, update fixed_value and any present displayed_average.
Keep method, absent/null fields, unrelated mechanics, original output and undo
history intact. Do not invent a formula for malformed input or silently convert
between fixed/formula methods. Authoritative producer validation still gates Save.
Show returned validation issue messages and field paths so the GM can act; clear
stale issues on edits/version changes and distinguish validation outages.

Expected writes: this handoff; predecessor HANDOFF-STATBLOCK-manual-revisions.md
and Docs/Roadmaps/ROADMAP-demo.md settlement; UI statblocks/editor/
statblockEditorState.ts, StatblockDefinitionEditor.tsx and their two existing tests;
statblocks/revision/SavedMechanicsRevisionEditor.tsx and its existing test.
No API/schema/producer changes, adoption, scene links or AI calls.

Verify fixed/formula/null-average/odd dice rounding, typed producer coherence,
original immutability and undo; mounted editor maximum-HP meaning/disclosure;
validation issue rendering and clearing; affected workbench tests/typecheck/build.
Independent exact cumulative Bugbot review, PRIME merge, guarded same-schema
API/UI delivery, actual ordinary HP revision Save and old/new reopen/restart.

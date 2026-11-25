# STATBLOCK — WWN reviewed sheet projection

Status: ACTIVE. User authorized sequential WWN Goal 5 and independent BugBot
review. Base fb2822c593083eda23523fe71ad05240029270f6 on Buddy origin/main.
Serial lane codex/wwn-sheet-projection in the isolated
buddy-wwn-sheet.1U8mjPle checkout on Projects. No live ports, databases,
provider calls, or deployment are required.

## Outcome

Buddy's existing StatblockRenderer admits a reviewed WWN sheet as a read-only
projection source. An explicit projection config selects and labels values
that reference reviewed sheet fields. Unknown, ambiguous, blank and template
defaults may be shown as field status. Only confirmed fields supply values.
Each displayed value preserves field evidence or an explicit caller override
with a reason. Rebuild from a corrected sheet while preserving unmodified
fields and applicable explicit overrides. Display WWN terminology.

The existing D&D-only saved/candidate revision contract remains unchanged.
The sheet is the mechanical source. This stage does not propose a second
statblock store, import route, provider workflow, or graph writer.

## Write lease and verification

- This handoff.
- apps/live-control-ui/src/statblocks/render/StatblockRenderer.tsx.
- A WWN projection module and owning renderer tests in the same render directory.

Dependency is the Goal 5 reviewed fixtures under the verified Projects
RulesIngestion run wwn-sheet-fixtures.c3KhSiz3. The overlapping-looking
authored statblocks PR #4441 did not list renderer paths.

Render both official AcroForm and held-out native-text sheet snapshots
through the existing renderer. Confirm visible zero, blank and unknown,
field-level source evidence, and WWN weapon fields. Change a source field
and verify the dependent display updates, while unrelated values and
explicit overrides remain. Verify existing renderer behavior and run the
repository's exact-SHA frontend verifier before review/merge. Keep all
verification output on Projects.

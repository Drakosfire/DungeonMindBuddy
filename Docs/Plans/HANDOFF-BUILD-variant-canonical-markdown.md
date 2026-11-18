# Build Markdown from reviewed statblock mechanics

Stacked above #3902 at aca18d891843d70fccff353befa99c2355ad942e.
Settle #3855, #3864, #3893 and #3902 before this slice. The branch is
codex/build-variant-canonical-markdown in the isolated
aw-conversation-drafts checkout. Keep the primary databases unchanged.

The original turn-five capture could produce different mechanics in the
editable Markdown and the typed review. Use the owner-validated definition
to render the editable Markdown when storing a statblock variant review.
The writer's original reply remains in conversation with its receipts and
citations. Retain the current Markdown behavior for other conversation drafts
and for candidates whose mechanics fail owner validation.

The write set is the draft persistence boundary, its statblock Markdown
projection, and the existing ordinary Build draft tests. Exercise valid and
warning-bearing owner receipts, rejected or missing receipts, and ordinary
Markdown drafts. Confirm that every rule text in the typed review is in the
persisted editable draft. Confirmation continues to bind the reviewed
definition and the exact draft revision.

The renderer does not judge whether new rule wording preserves every source
qualification. The Dust Walker exception and truthful Combat guidance need
separate qualification before the six-turn benchmark passes.

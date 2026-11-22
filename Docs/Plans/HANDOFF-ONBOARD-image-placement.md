# ONBOARD: preserve prose during image placement

Status: ACTIVE. The onboarding goal explicitly authorizes implementation,
Bugbot review, merge and deployment after applicable verification gates. Serial
single slice on `codex/onboard-safe-image-placement`, based on
`origin/main@7092e7bef5bb65d1ea3774bcc1b862c03905da9e`, in the existing
`ci-collection-parity` checkout. The image-move mounted successor #4380 and
its settlement #4387 are merged and its write lease is released; historical
predecessor text marked ACTIVE does not reinstate that completed lane. Open
Build work, including #3824 and #3867, must retain its existing contracts.

## Outcome and boundary

Placing an image through the ordinary Build Image Studio must preserve the
clicked prose and neighboring content and must not report failure after a
partially committed change. The production synthetic-page witness inserted
inside a word and persisted a split paragraph despite an inspection error.
Keep image identity, stale-capture refusal, undo, explicit document ownership,
serialization and layout behavior intact. Do not edit or repair the user's
private World as part of this slice.

Expected exclusive write set: this handoff; Build compose bridge and focused
tests; shared reviewed Markdown insertion helper and its focused tests only if
necessary to ensure an unsuccessful insertion cannot leave a mutation. Any
other file, durable schema, deployment or runtime collision is a stop/split
signal. No source or guest-release changes.

Verify actual mounted Build editor behavior at middle/start/end of paragraphs
and representative layout blocks, stale captures, transaction mismatch,
one Undo/Redo, correct persistence/reopen and unchanged neighboring content.
Run required exact-SHA hosted and discovered diagnostics, inspect cumulative
diff and request independent Bugbot review. A synthetic fixture does not prove
the production World or release is ready.

## Working checkpoint

The Build image receiver now constructs and validates an undispatched insertion
after the clicked root block, rather than splitting the clicked textblock. Plain
pages retain their sidecar-free identity behavior; existing presentation IDs are
preserved and the new image block receives an ID. Focused working-tree tests
cover paragraph start/middle/end, heading/list/table, identity-only and composed
layouts, serialization, Undo/Redo, stale capture and non-image refusal. The
initial regression failed before the change; the affected suites passed after
it. The old drop test now deliberately expects placement after the clicked
block. Frontend build passed. These are working-tree diagnostics; durable Build
Save/cold reopen, exact-SHA verification and final independent review remain.

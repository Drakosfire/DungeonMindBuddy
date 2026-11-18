# Correct exact reviewed variant clauses

Stacked after #3918 at 8de0d8defa0c84444dade95ca5166ef0d6547d0c. Branch
codex/build-bounded-variant-correction. Settle the parent stack in order.
Keep primary data unchanged. Backend write scope is the existing variant
review endpoint, request model, confirmation and draft storage owners,
review projection and mounted tests.

A review correction must name a current unsaved review and revision.
Accept explicit replacements of unique exact text in named rule fields.
Keep all other mechanics, definition fields and the base locator unchanged.
Validate the result with the mechanics owner before staging it. Under the
existing draft/save lock, reject any started save or changed draft. Persist
the canonical Markdown and new review atomically. The previous review stays
inspectable, but only the successor can be newly confirmed.

Verify exact edits, untouched rules, no implicit save, stale rejections
and revision-bound reopen. The frontend and chat producer still need to
expose this API through explicit review. This slice does not automatically
apply a fidelity judgment or alter the original six-turn benchmark result.

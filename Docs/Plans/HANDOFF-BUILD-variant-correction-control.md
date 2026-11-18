# Stage a rule correction from an unsaved conversation review

Stacked above #3925 at 9803ee5f77900faed3f803a9a6bdecdd1dcd914c. Branch
codex/build-variant-correction-control. Settle the parent stack in order.
Keep primary data unchanged.

Write scope is the existing conversation draft editor, its API client and
hosted transport allowlist, plus focused UI tests. A GM can select a rule and
edit its existing rule text, timing or trigger condition. Stage only those
changes against the loaded review and revision. Do not confirm while any
correction is unstaged. After staging, reopen and display the successor
before enabling its separate confirmation action. Keep the previous review
and provider evidence inspectable.

Verify exact request fields, no save when staging, fresh review identity
on confirmation, and an isolated browser rehearsal. This is a manual
review control. It does not invoke the fidelity checker or apply model
suggestions automatically.

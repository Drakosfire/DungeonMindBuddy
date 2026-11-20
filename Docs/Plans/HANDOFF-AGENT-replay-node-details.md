# AGENT — Inspect a replay node in context

Status: ACTIVE under the user's browser comment requesting replay node
inspection in place of the completed native reply evidence summary.
Serial single PR from Buddy main `2e21c18e1` on
`codex/buddy-replay-node-details` in the existing graph timeline checkout.

Scope: completed native reply Details composition, the replay component,
its styles, and owning frontend tests. The inline citations still use their
exact-source readers. Node details use the saved replay only, with no new
reads. Keep recovery and other reply evidence readers available.

Verify node selection and dismissal, inspect the exact cumulative diff,
run the frontend verifier and independently review the changes before merge.

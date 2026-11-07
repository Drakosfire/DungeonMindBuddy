# PROMPTS: human native Graph navigation labels

Status: ACTIVE. PRIME owns the operator-prioritized host-metadata cleanup.
Stacked on PR2197 exact01de478fae624af02588d5a9a7c7e58aabff9138, same existing
checkout and dependencies. Merge/deliver2195,2196,2197,then this slice. Navigation
2194 is already delivered. Re-anchor and retarget after each parent merge.
No runtime lease, provider calls, data changes or new checkout. Held Play and INGEST
stay outside scope; open INGEST2190/2193 do not write these files.

Outcome: native object/assertion/ABOUT navigation labels use human names or local
object aliases instead of host entity IDs. Reuse the exact existing frozen catalog
and indexed selection owner. Consolidate repeated name projection at its current
producer; do not scrub arbitrary source/user strings or parse IDs as names.
Preserve duplicate, conflicting, missing and scoped names without merging identity.
Keep current scope, complete-read and ABOUT witness checks. This is label content,
not a new query wire/authority contract; historical recorded labels remain exact.
No reader fence, alternate retrieval path, new provenance or limit change.

Exclusive expected write set:
- This handoff.
- apps/live_control_server/services/native_graph_reads.py
- tests/test_native_plan_assertions.py (committed2195 parent; successor lease only)
- tests/test_native_plan_statements.py

Verify deterministic duplicate/missing-name aliases, literal user strings, scope,
partial reads and rejected ABOUT witnesses. Exercise actual Core query identities
and current Jev navigation wire without raw entity IDs. Check relationships stay
attached to their actual subject. Review cumulative parent-to-head diff, obtain
independent Bugbot approval, commit/push/open this one PR, satisfy CI and deliver
separately. Do not claim source logical IDs, other prompt roles, writer input,
References acceptance or retrieval performance are settled by this label change.

# BUILD: Gazetteer 1.12 review admission

ACTIVE. PRIME solo; ARCHITECTURE independent review. Base
75951c99a9e1d50861133da3283250781e2a62f4; branch
codex/worldbuilding112-review-admission; checkout /tmp/prime-recap-mention-boundaries.
Serial successor to merged collective-source-fidelity slice (#1246); its code
lease has ended. Disjoint DOGFOOD #1235/#1237 UI and #1244 packaging leases.

The fresh 1.12 candidate completed, but exact-run review rejects v0.2 observations
because two consumer evidence gates still admit only literal 1.11. Admit exact
1.12 beside 1.11 at review and publication evidence validation. Preserve all
source/identity/World validation; no wildcard profile admission or runtime default
change. This is consumer plumbing, not semantic or publication acceptance.

Exclusive write set:
- This handoff
- apps/live_control_server/services/extract_promote.py (two exact admission sets)
- tests/test_worldbuilding_source_observations.py (production to both consumers)
- tests/test_worldbuilding_gazetteer_profile.py (closed registry expected set)

Verify fixture production extraction through exact review and publication preview
for both1.11/1.12, retaining openable evidence and rejecting damaged references.
Inspect cumulative diff; complete one PR and independent review. No serving,
provider, corpus or retained World writes during implementation.

# ONBOARD: retain prepared guest Plan selection

Status: ACTIVE under the owner's delivery, review, merge and deployment authority. Serial fix based on b8a4d2d294b2f918470363df40c18c4c2998b226, branch codex/sizzek-plan-selection-state. Scope is Plan initial-selection state, its focused UI test, and this handoff. No production data or runtime lease. Production smoke of #4750 showed the prepared content but labeled it an unsaved draft because React selection state was not updated along with the selection ref.

Set both states when loading the resolved Plan. Verify guest and existing Plan entry tests, independently review, recheck the serving parent, merge and deploy. Confirm a fresh guest sees the saved Plan before proceeding to Play, Combat and Home.

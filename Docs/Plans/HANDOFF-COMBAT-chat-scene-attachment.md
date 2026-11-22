# Propose a saved encounter attachment in Buddy

Draft at base `89e24746136b6bf7bf04e9f8fc16e1820f45c24b` for the authorized Old Bath House goal. This brief grants no implementation lease. The slice is serial. The host-projected proposal and the user-facing confirmation belong in one PR because neither delivers a usable, reviewable attachment alone.

## Outcome

From a saved Plan scene, ask Buddy to attach a named standalone Combat encounter. Buddy responds with a review card identifying the target scene, source encounter revision, roster, and groups. The review opens the existing Scene encounter panel with the exact source selected. Only Confirm encounter copy applies the attachment. A proposal never starts Play.

## Ownership and boundaries

- Plan owns the saved scene and the committed workspace revision. Use the existing scene context and refuse selection from unsaved content or an unrelated scene. Preserve any prior template when the target is occupied.
- Combat owns the standalone encounter, its revision, and the scene-template copy transaction. Use the existing copy request and recovery key. A newer source revision requires a new preview. A scene or Plan revision change requires a new target. Keep the original standalone encounter and its exact mechanics snapshots.
- Buddy owns ordinary conversation routing and display. Use an explicit typed proposal carrying host-verified source and target. If model-assisted selection is needed, expose encounter names and request-local aliases only. Use host-side resolution and explicit choices for ambiguous names.
- Keep portrait binding and broader creature authoring outside this slice. A portrait-bound snapshot that Combat already stores should copy through the existing owner unchanged.

Likely implementation owners are the native Plan ordinary-turn policy and output, the Plan conversation card, and `PlanSceneEncounter` preselection. Before activation, inspect open #3824 and current Build/Plan/Combat leases, pin the exact base and allowed paths, and resolve overlaps. No new schema is assumed. If the existing completion owner cannot durably retain the proposal, checkpoint the design before widening the write lease.

## Verification

Prove the ordinary signed-in entry point routes to a typed, read-only preview. Test the scope boundary, model input, ambiguity, source and target staleness, an already prepared scene, confirmation, and same-request recovery. At the Combat owner verify the copy preserves exact actor snapshots, stats and groups and does not mutate the source. Reopen the preview after reload. Verify Play captures the prepared version and still requires explicit Start.

The saved Old Bath House standalone encounter and the Edge Meat Mind revision already exist. The real hosted acceptance requires Alan's approved marked scene, approved minion, and an authorized disposable or test Play run. These are acceptance inputs and do not gate provider-free implementation.

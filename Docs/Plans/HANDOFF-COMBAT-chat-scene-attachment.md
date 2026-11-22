# Propose a saved encounter attachment in Buddy

Active for the Combat-owned preview boundary under the authorized Old Bath House goal. Base `89e24746136b6bf7bf04e9f8fc16e1820f45c24b`, branch `codex/combat-chat-attachment-handoff`, existing isolated Combat checkout. The slice is serial. The host-projected proposal and the user-facing confirmation belong in one PR because neither delivers a usable, reviewable attachment alone.

Current write lease is this handoff, `src/application_state/combat_encounters/scene_templates.py`, and `tests/application_state/test_combat_scene_templates_postgres.py`. No competing encounter PR was identified. Native Plan, routing, and UI writes still require an explicit scope amendment after checking their current leases.

UI preview projection amendment at fetched main `8506cf3d3`: add `apps/live-control-ui/src/api/types.ts` and `apps/live-control-ui/src/planSurface/components/SurfaceEvidenceAnswer{,.test}.tsx` for the typed preview card only. The #3824 authorization changes to agent routes and conversation orchestration stay outside this amendment.

## Outcome

From a saved Plan scene, ask Buddy to attach a named standalone Combat encounter. Buddy responds with a review card identifying the target scene, source encounter revision, roster, and groups. The review opens the existing Scene encounter panel with the exact source selected. Only Confirm encounter copy applies the attachment. A proposal never starts Play.

## Ownership and boundaries

- Plan owns the saved scene and the committed workspace revision. Use the existing scene context and refuse selection from unsaved content or an unrelated scene. Preserve any prior template when the target is occupied.
- Combat owns the standalone encounter, its revision, and the scene-template copy transaction. Use the existing copy request and recovery key. A newer source revision requires a new preview. A scene or Plan revision change requires a new target. Keep the original standalone encounter and its exact mechanics snapshots.
- Buddy owns ordinary conversation routing and display. Use an explicit typed proposal carrying host-verified source and target. If model-assisted selection is needed, expose encounter names and request-local aliases only. Use host-side resolution and explicit choices for ambiguous names.
- Keep portrait binding and broader creature authoring outside this slice. A portrait-bound snapshot that Combat already stores should copy through the existing owner unchanged.

Likely integration owners are the native Plan ordinary-turn policy and output, the Plan conversation card, and `PlanSceneEncounter` preselection. Before extending the lease, inspect open #3824 and current Build/Plan/Combat leases and resolve overlaps. No new schema is assumed. If the existing completion owner cannot durably retain the proposal, checkpoint the design before widening the write lease.

## Verification

Prove the ordinary signed-in entry point routes to a typed, read-only preview. Test the scope boundary, model input, ambiguity, source and target staleness, an already prepared scene, confirmation, and same-request recovery. At the Combat owner verify the copy preserves exact actor snapshots, stats and groups and does not mutate the source. Reopen the preview after reload. Verify Play captures the prepared version and still requires explicit Start.

The saved Old Bath House standalone encounter and the Edge Meat Mind revision already exist. The real hosted acceptance requires Alan's approved marked scene, approved minion, and an authorized disposable or test Play run. These are acceptance inputs and do not gate provider-free implementation.

The hosted destination is Session 32 — Old Bath House, scene The welcome. The signed-in statblock workbench created and reopened the Bath House Meatling draft on the reviewed hosted route release. Two candidate-generation operations ended at the downstream provider with an authentication error, so there is no accepted Meatling revision yet.

The Combat preview owner resolves the full title within the verified World, rejects ambiguous matches, and returns the exact copyable source revision after checking the saved target. This remains read-only. The ordinary Buddy turn integration and confirmation entry point are still pending.

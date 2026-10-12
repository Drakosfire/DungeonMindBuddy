# DOGFOOD: remove redundant Plan-row labels

Status: ACTIVE, direct operator authorization 2026-10-11: remove PLAN and Elderwyld from second row, leaving Plan selector and New Plan.
Base: fetched main2286a195af3210827da88ade118d8b81633e078f, merged compact navigation #1080. This consumes that completed predecessor.
Branch/check-out: codex/plan-row-and-world-discovery, /tmp/buddy-automatic-chat-reconciliation.
Topology: serial; one UI cleanup PR. Relevant open World-selector work inspected; no context-row overlap identified.
Write lease: this handoff; apps/live-control-ui/src/planSurface/components/PlanSurfaceContext.tsx/.test.tsx; planSurface/PlanSurfacePage.test.tsx; surfaceInteraction/contextHost/SurfaceContextModule.tsx. Optional module label preserves existing labeled consumers. Public World identity/selection/action contracts and guards remain unchanged.
Runtime: no rollout, server, provider, World registry, corpus, Graph or Plan mutation.

Invariant: omit managed Plan row's redundant surface/world labels, shorten New blank Plan display label to New Plan, retain exact document selection/create callbacks and disabled/recovery behavior. Legacy PREP/session context remains intact.
Verification: app TypeScript passes. Owning Plan context + shared context-host suites:13 passes. Three mounted World Plan recovery/action-guard tests pass (66 unrelated cases not selected). Diff check passes. Live visual evidence remains pending reviewed rollout.

Separate missing-World finding: read-only actual GET/api/live/world-containers and its registry contain only Elderwyld. Dropdown is not filtering out additional records. Preserved private dogfood-one-shots-v3 packets contain Of Conks & Cons (47cards,114units,15entities) and A Wild Sheep Chase (23cards,135units,10entities), with PDF/media/board/reference manifests. They are prototype packets, not registered managed Worlds in this runtime. Read-only SHA/size inventory is at the task visualization .private/world-adoption-candidates/inventory.json; no content was copied or adopted. No Wild Goose Chase packet was found; existing prior Sheep source/title identified explicitly.

Making these usable Worlds requires a separately bounded adoption contract for source-root ownership, original PDF/media/pin preservation, current Plan representation and optional native Graph admission; do not fabricate empty named Worlds, alias Elderwyld Graph, treat prototype board as canonical graph or claim adoption complete. Coordination requested from PRIME on shared registry/data ownership while DOGFOOD retains this user task. The adoption finding is not an implementation in this UI PR.

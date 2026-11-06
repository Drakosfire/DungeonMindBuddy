# BUILD: fullscreen activity space

Status: ACTIVE. PRIME owns this UI-only slice from merged activity d64488c3848aa0a09cbb924b0d1ce8079a7b0f97 on codex/activity-fullscreen-space in buddy-context-loop. Topology: parallel-independent of frozen backend PR2136/f9dadd2e2; no overlapping write paths. The predecessor UI lease is released. Local delivery is serial after the already delivered UI9c21b3497. No live runtime lease yet; an ephemeral localhost5293 preview is owned by PRIME for read-only UI verification and must be stopped afterward.

Observed defect: the fullscreen conversation inherits the resized dock's --conversation-dock-height337px. Expanded activity therefore remains145px tall despite the fullscreen viewport. The complete timeline is present, but only a small part is visible.

Outcome: expanded activity uses the available fullscreen viewport, retains ordinary compact-dock sizing and keeps the composer/recovery controls reachable. Adopt the existing timeline and fullscreen state, with no new inspector or progress authority.

Exclusive write lease: this handoff; Docs/Plans/HANDOFF-BUILD-execution-activity.md for truthful predecessor settlement; apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css. No Python, dependencies, schema, sources, Graph, provider or session changes. The preceding broad Python run kept all Python/test blobs unchanged, printed425 passing tests, then its wrapper ended143 without a completion receipt. Its output is retained without a clean-completion claim.

Validation: production UI build; ordinary control verification in fullscreen and restored dock, including actual body height, complete event coverage, reachable composer, preserved unsent text/preferences and screenshot. No model request or document save. Independent exact cumulative review, bounded PR, preserving UI-only activation and post-delivery verification. Native retrieval observations/dynamic request labels remain a separate open part of the goal, as do context reduction, References acceptance and retrieval performance.

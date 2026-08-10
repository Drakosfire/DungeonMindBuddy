# HANDOFF — Surface Context Layer + Global World Graph Status

**Line of work:** DOGFOOD-POLISH / SURFACE  
**Status:** READY TO BUILD  
**Base:** `main` after PR #548  
**Branch:** `agent/surface-context-layer-foundation`  
**Suggested PR title:** `SURFACE: add global World Graph status and generic context bar`

## Mission

Create the shared UI layer that answers:

1. **What world is loaded?** → application chrome World Graph status in the main nav  
2. **What is loaded into the surface I am using?** → generic `SurfaceContextHost` below nav  

Plan is the first adopter of the context bar, not its architectural reason for existing.

## Governing invariant

```text
AppChrome owns global chrome.
World Graph owns graph state.
Surface Context Host owns context-bar layout.
Each surface owns the meaning and behavior of its context.
Canvas owns its active work object.
```

Do not contaminate `SurfaceInteractionPublication` with React payloads. Context Host is a sibling UI composition seam.

## Scope (this PR)

- Generic `surfaceInteraction/contextHost/` (provider, host, modules, primitives)
- Compact World Graph status in nav on **every** route (popover retains existing lens controls)
- Remove `GRAPH_LENS_NAV_ROUTES` gate; no per-route graph reload
- Plan publishes one `PREP` module (selector + New prep popover); remove `.plan-document-toolbar`
- Sticky stack: nav + context host
- Owning tests per handoff §26

## Explicit non-goals

Build/Play context implementations, Plan→Play handoff, promotion, rename/archive manager, Ask continuity, graph cache redesign, universal document schemas.

## Dogfood acceptance

From Plan: answer “what world?” from nav and “what prep?” from context bar. Navigate to Build: Plan controls disappear; World Graph status stays in the same place.

## Authority

Full product brief: chat handoff (2026-08-10). This file is the implementation pointer.

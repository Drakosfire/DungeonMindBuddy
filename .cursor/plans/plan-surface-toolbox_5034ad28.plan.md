---
name: plan-surface-toolbox
overview: Create an intentional `/plan` surface as the first `SurfaceConfig` over a reusable `SurfaceShell`, composed from independent NavBar, ToolBar, EditBar, and SurfaceCanvas regions, where one projection registry powers both tools and reference-chip navigation. Ships as a parallel branch ladder of defensible, agent-authored PR stories (testing, security, simplicity, composability), kept decoupled from the ontology/taxonomy ladder by an adapter boundary.

todos:
  - id: ladder-delivery
    content: Stand up the `plan-surface` branch ladder (trunk + tracking doc + baseline) and author per-rung agent handoffs (`HANDOFF-pr<N>-<slug>.md`) carrying section 4 allowlist, section 7 verification, and the section 9 defensible rubric (testing, security, simplicity, composability).
    status: completed
  - id: define-plan-route
    content: Define `/plan` as the first intentional `SurfaceConfig` with a Plan context header and tidy top nav.
    status: completed
  - id: plan-toolbar
    content: Build a reusable `SurfaceShell` and config-driven ToolBar projection that loads workflow components into an adaptive drawer/container.
    status: completed
  - id: ingestion-tool
    content: Mount recap ingestion in the Plan toolbar using the existing recap-ingest API operations and terminal fallback copy.
    status: completed
  - id: statblock-tool
    content: Mount statblock generation in the Plan toolbar by reusing the existing working statblock workbench flow.
    status: completed
  - id: shared-resolver
    content: Extract one reference resolver module (shared by static and React) that resolves a chip's kind from the existing corpus indexes; refId is an opaque locator, no surface-owned category enum.
    status: completed
  - id: reference-projection
    content: Project the registered content surface for whatever kind the resolver returns, through the same registry and container as tools, with one edit toggle (lock model plus two-phase writer).
    status: completed
  - id: derived-views-adapter
    content: Build the derived-views adapter speaking the ladder vocabulary (source artifact -> source anchor -> source unit) so chips resolve over corpus-on-disk today and can later consume the ladder's shadow-retrieval read path via an adapter swap, with graceful degradation.
    status: completed
  - id: surface-theming
    content: Anchor surface styling on the existing Tiptap spike tokens via one SurfaceConfig theme (canvas inherits); no second theme layer until a second surface proves the need.
    status: completed
  - id: verify-plan-surface
    content: Add focused UI tests and run build plus relevant backend tests.
    status: completed
isProject: false
---

# Historical Plan toolbox implementation

All ten checklist entries above are completed. The former body is preserved in
[exact Git history](https://github.com/Drakosfire/DungeonMindBuddy/blob/cc0ca06bb197c64724fded178d7ec545654b06ec/.cursor/plans/plan-surface-toolbox_5034ad28.plan.md).
Its full historical file is 26,732 bytes, SHA256
`f1228fe58aeb5aefea79b69ddfeb61458ae93afd622094e47418ada2333e8cdf`.

This is implementation history, not current dispatch or bar-ownership authority.
The historical SurfaceShell ownership claims were already superseded. Consult
[the surface interaction architecture](../../Docs/Design/ARCHITECTURE-surface-interaction-layer.md)
and [the Plan toolbox architecture](../../Docs/Design/ARCHITECTURE-plan-surface-toolbox.md)
for the current contracts. The completed checklist metadata is unchanged.

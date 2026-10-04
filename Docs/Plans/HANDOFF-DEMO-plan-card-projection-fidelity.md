---
title: Preserve authored semantic content in Plan Cards
document_class: implementation_handoff
status: ACTIVE
created_at: "2026-10-04"
workstream: DEMO
pr_topology: serial
implementation_branch: codex/demo-plan-card-projection-fidelity
---

# HANDOFF — Plan Cards semantic projection fidelity

## PRIME authority and lane

PRIME activates one bounded UI repair from fresh Buddy main `e8c727b133286ba76e17a191ea921b8082e94bf0`, pinned by this publication commit. DEMO's proposal was reviewed against `slicePlayableBodies` and the existing `MarkdownEditorCore` semantic extension set. The #913 card-edit lease is SETTLED. PRIME checked all eleven open PR file sets; none overlaps §3. DEMO is the sole writer; PRIME independently reviews exact cumulative diff and owning evidence before merge. Reuse a clean isolated DEMO checkout on the named branch from the publication commit; no local main checkout. Finish implement→verify→commit→push→one PR. No additional PR/capability without PRIME sequencing.

This independent UI lane can proceed alongside Graph contract/owner work. Graph-backed conversation remains the next primary capability; this repair neither activates nor blocks that lane. DOGFOOD owns the separate running 5202/8000 preparation, and prototype PR #887 owns its own files. No runtime, database, provider, credentials, private corpus processing or prototype write lease is granted.

## PRIME inert-rendering amendment — 2026-10-04

The initial default read-only editor mechanism is superseded by the schema-only static mechanism in §2. ARCHITECTURE and DEMO identified that editable=false does not remove NodeViews or structural plugins. PRIME inspected the installed schema serializer and pins the inert mechanism with this publication commit. Exact write paths, scope and topology are unchanged; DEMO may continue additive slicer tests while consuming this amendment before renderer changes.

## 1. User outcome and invariant

Cards must retain the authored material users can already see in Document: Graph/Runbook reference labels and exact identities, paragraph separation, nested lists, inline marks and supported semantic blocks. Observed Session29 examples are missing Mirathorn/Thrin/Ironveil Warehouse/Lysandra labels and concatenated prose/lists. The durable comparison is `prototypes/plan-play-cards/CARDS-COMPARISON.md` at prototype head `7214ec393b172165447a7899176e7b561729886e`; it is evidence, not production implementation authority.

Keep one mounted Plan draft and existing card identities, hierarchy, boundary validation, basis, Ask/edit targeting, explicit Apply/Save and navigation controls. Projection is read-only and cannot create editor transactions on the authoritative Plan, Save, fetch Graph knowledge, or change stored Markdown. Existing native Runbook consumers must retain byte-for-byte current `bodyText` behavior; additive structural fields supply the Plan presentation only.

## 2. Bounded implementation

Extend existing authored slices with lossless inline title and body JSON content while preserving old text fields. Preserve exact existing v1/v2 marker boundaries, ordinary root H1/H2 exclusion, sibling separation and marked Option item boundaries. Ordinary headings expose authored inline title; v2 Option first paragraph remains its presented title, with remaining blocks as displayed body. Do not modify what counts as a card or reinterpret range/ownership rules.

Render structural slices through the existing semantic extension **schema only**, using Tiptap core `generateHTML` (or `getSchema` plus ProseMirror DOMSerializer) on JSONContent. Inspected installed core resolves the schema, builds Node.fromJSON and serializes its content; it does not create EditorState/EditorView or install plugins/NodeViews. Do not mount MarkdownEditorCore, useEditor or any Editor for these projections. Its editable=false mode still mounts Graph/Runbook React NodeViews and structural plugins, which is outside this inert display contract.

Keep the schema serializer/helper local to the leased WorldPlanCardProjection component; no shared core/extension edits or new renderer API. Reuse existing schema attributes/renderHTML for supported semantic nodes. Locally extend the Graph reference renderHTML to a noninteractive span retaining escaped label and exact identity rather than an actionable-looking button; Runbook references retain static span identity/label. No NodeView/runtime provider/event binding. Unknown or unsupported node shapes must show a visible unavailable state rather than silently dropping content or falling back to flattened text. Only schema-produced escaped DOM/HTML may be inserted; never trust source HTML strings or concatenate unescaped labels/attributes.

Do not round-trip through Markdown or flatten structural content. Memoize by World/document/card and exact semantic content (or equivalent generation) so same-card draft edits and document replacement update the DOM. Avoid regenerating all content on unrelated UI state changes. Expected read-only Editor instance count is zero. Report observed rendering cost for a representative multi-card synthetic document; keep this bounded to the existing hierarchy without a new virtualization/state subsystem. Limit CSS to faithful content structure/spacing and reference readability. Stop and return any unsupported content or required shared renderer path rather than adding a new grammar, extension or renderer authority.

## 3. Exclusive expected write set

- apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts
- apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts
- apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.css
- apps/live-control-ui/src/planSurface/WorldPlanCardProjection.model.test.ts
- apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx
- Docs/Plans/HANDOFF-DEMO-plan-card-projection-fidelity.md — truthful contract/settlement only
- Docs/Roadmaps/ROADMAP-demo.md — truthful lane/settlement only

No directory-wide lease. `PlanSurfacePage`, Markdown editor core/extensions, Agent/server/API, persistence, packages/lockfiles and other tests are excluded. Return an exact amendment request if evidence proves another path necessary.

## 4. Owning acceptance

1. v1/v2 model and slicer tests preserve title/body nodes, marks, separate paragraphs, nested lists and exact Graph/Runbook IDs/labels. Prove no adjacent card or ordinary root instruction leakage. Keep existing text fields and native Runbook results unchanged.
2. Mounted Plan Cards show semantic content/labels through shared schema serialization, including references inside titles and bodies. Prove zero display Editor/NodeView instances and no ambient Graph hover/select/glance/mechanics requests on render or reference click/hover. Static content cannot accept edits, normalize source nodes, mutate the authoritative editor, trigger save/API/provider work, or lose draft data on Document/Cards switching. Test markup-like labels are displayed as escaped text, never executed source HTML.
3. Update a same-identity card's draft content through ordinary editor mechanics and replace the document; Cards reflects the current content without stale structural props. Keep exact Plan basis and existing Ask/edit selection/identity/edge tests passing. Do not substitute display text for request authority.
4. Review synthetic screenshots at desktop and narrow widths for readable paragraph/list/reference structure. Use synthetic examples matching observed defects; do not upload new private corpus screenshots. This is fidelity acceptance, not focused scene/lens or aesthetic prototype adoption.
5. Run focused native Runbook projection, Plan Card model and mounted integration suites; broaden only for a concrete affected shared invariant. Inspect exact cumulative diff, `git diff --check`, and report inherited TypeScript failures distinctly. Existing dependency runtimes may be reused without upgrades; logs under /tmp. Send PRIME PR URL, exact head, base, write set, evidence and holds. No autonomous merge.

## 5. Exclusions and stop conditions

No full prototype visual redesign, focused scene/lens workflow, chronological/session routing, Run decisions/rolls/notes, card editing changes, Graph grounding/media, ingestion, auth, migration or server rollout. The eventual common prepare/run interface is evaluated across both Conks prototypes, Sheep and personal campaign sessions; this repair supplies faithful content for that adoption. A new capability, path collision, loss of atom identity or changed Runbook text behavior requires PRIME to split/revise scope.

## Implementation status — PR #914 (2026-10-04)

The six-path implementation is published from `codex/demo-plan-card-projection-fidelity` in draft [PR #914](https://github.com/Drakosfire/DungeonMindBuddy/pull/914). Code commit `93d7d0c7` is based on the pinned amendment `47fcb50b1a392be89b19eb51032adac705f9c13b`. Focused Runbook slicer, Plan Card model and mounted integration suites pass 63/63; the production Vite build passes. A synthetic 20-card mount took 228.7 ms in jsdom. `tsc -b --pretty false` retains the unchanged main error at `ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`.

The required synthetic desktop and narrow screenshot review is still an acceptance hold. The available browser surface rejected the local preview URL and disallowed alternate browser routes, so no screenshot or visual acceptance is claimed. Keep this handoff ACTIVE and the PR draft until the visual gate is reviewed through an approved preview environment. No merge is authorized here.

# AGENT: observe generated objects taking shape on the page

Status: ACTIVE bounded UI implementation. Operator instruction on 2026-10-25: generated writing, tables, media and editable plan/checklist objects belong on the author’s Surface; clarifying questions remain inline in conversation. This supersedes earlier plan-in-conversation destination guidance. Discussion and concise acknowledgments/activity remain in conversation. The current implementation slice extends actual streamed page construction from tables to ordinary Markdown blocks; it does not claim that interactive work-plan placement is implemented.

Base81db52ec92b574207016eda913bcab4b2e12a366, branch codex/surface-construction-prose, existing buddy-context-loop checkout. Parallel-independent of parked #1764: that PR owns backend capability scoping and is held from merge/deployment; this slice has no dependency on it or overlapping runtime paths. Citation/table controls already exist on main. No new checkout, environment, port, source, database or provider request is required for implementation.

## Owning invariant and failure cases

Generated material is observed at its intended page position, outside chat. Existing Build proposal provider deltas already project complete replacement_markdown lines through the operation-local construction stream. SurfaceConstructionPreview currently filters its canonical AST to tables, hiding actual prose, headings and lists. Extend this shared observation owner rather than introduce simulated typing, a second generation, a workflow engine or a chat-only renderer. Render content received so far as inert, safely escaped Markdown. Do not fetch links/media, execute HTML, or expose live task controls from unvalidated deltas. Mixed prose/tables retain their order. The existing identity/attempt/sequence and editor/conversation fences stay authoritative; an observer disconnect does not resend the command.

The preview is incomplete until final producer admission. It cannot be edited, executed or saved. After final validation, the existing editable colored Surface proposal replaces it and retains one Save, discard, placement, stale-work refusal and recovery. Invalid/interrupted construction must not masquerade as a saved result. Showing a partial block does not prove the final writer or routing succeeded. Final preview visibility must not steal focus or lose newer composer text.

## Expected write lease

- This handoff.
- apps/live-control-ui/src/surface/SurfaceConstructionPreview.tsx and SurfaceConstructionPreview.test.tsx.
- apps/live-control-ui/src/surface/SurfacePageProposal.css, only construction typography/layout.
- apps/live-control-ui/src/surface/SurfacePageProposal.tsx and apps/live-control-ui/src/buildSurface/BuildConstructionPreview.tsx, solely let inert construction reveal without taking keyboard focus; editable proposals retain existing focus behavior.
- apps/live-control-ui/src/buildSurface/BuildConstructionPreview.test.tsx, only actual bridge lifecycle/preview integration.
- Docs/Plans/HANDOFF-AGENT-intentional-build-response.md, amend the generated-object destination and settle completed proof scope; do not activate runtime routing.
- Docs/Plans/HANDOFF-AGENT-proposal-placement-recovery.md and Docs/Roadmaps/ROADMAP-demo.md, solely settle already-delivered #1760 and name the current object-placement priority.

One implementation PR, exact cumulative independent Bugbot, PRIME merge and protected UI-only delivery on5202 with API8000 retained. Re-anchor actual runtime lease/PIDs and state before rollout; do not assume the historical checkpoint is current. Focused tests cover mixed block order, safe text, no link/media loading or interactive checkboxes, no invented completion, and existing stale view retirement. Typecheck/build and ordinary synthetic live real-generation proof are required. Private story/trace evidence stays local. Operator acceptance and free-form writing fidelity remain open.

## Next object contract: plans/checklists on the Surface

Use the existing saved-work-plan owner for edited step text, selection/defer state, explicit dispatch identity and results. Surface placement must refer to that same World/conversation/source-turn plan identity; a Markdown list or copied checkbox is not a second plan or execution authority. Clarifying questions remain in the conversation object. Page placement requires the current Surface’s admitted editable target and retains its location through reload; missing capability must preserve the request and explain the obstacle. Checking a step selects it; explicit continuation executes it. Checkbox changes never silently publish Graph relationships, create a related page or mark execution complete.

Before activating that implementation, inspect and pin the exact saved object/reference representation, existing proposal/placement and plan admission owners, Save ownership and construction-to-editable transition. The design must cover undo/movement, discard versus plan-history retention, cross-tab changes, navigation/reload and exact result citations without duplicated plain text. Keep citation UI reusable across Build/Plan/Play even where older files still live under planSurface. No runtime lease for this new object representation is granted by this construction slice. Do not replace this requirement with a link from the old chat checklist and call it complete.

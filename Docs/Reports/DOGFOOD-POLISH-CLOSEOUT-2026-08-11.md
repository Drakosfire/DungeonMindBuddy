# DOGFOOD-POLISH closeout — 2026-08-11

**Status:** CLOSED as a workstream  
**Final implementation PR:** #560 — `DOGFOOD-POLISH: rename Build sources without breaking Canvas CAS`  
**Final implementation head reviewed:** `333418809c4f29823e004c295caee2420a9851ce`  
**Code-review disposition:** Review Cycle 2 — PASS (`4911968176`)  
**Merged to main:** `85a2bbf048d92afed1911031ca7b6a311115873c`  
**Doc-sync rule:** this report and the accompanying backlog/README edits are documentation-only closeout after the merged implementation.

## What this workstream established

DOGFOOD-POLISH is complete as the focused Plan/Build authoring-polish line. It established a stable surface/document model rather than trying to finish every remaining DungeonBuddy product issue.

The resulting product contract is:

> **World Graph tells DungeonBuddy what world is available. Surface Context tells each surface what the operator has loaded into it. Canvas tells us what work object is being edited.**

More concretely:

- workspace `documentId` is the opaque server-issued identity of a Plan or Build work object;
- `target_session` is Plan affinity metadata, not document identity or storage ownership;
- `SurfaceContextHost` owns generic context layout while each surface owns the meaning and behavior of its context;
- `MarkdownCanvasSession` remains the authority for admitted document record, current revision, body, content digest, dirty draft, reconciliation, and Markdown-save CAS;
- World Graph lens state is application context and must not be reloaded merely because document metadata or active work-object context changes;
- agents consume the accepted surface/document context; they are not a second document or graph authority.

## Completed slices

### Semantic prep authoring

- PR #535 — CommonMark/GFM-backed Markdown admission boundary (`2fb059c3`).
- PR #529 — semantic prep authoring on that boundary: nested prep, Decision/Consequence, semantic paste, serializer/safety, app-owned prep styling (`95a2fbc`).

### Plan document workflow

- PR #541 — exact existing prep selection by opaque `documentId` (`9219cce`).
- PR #543 — generalized intentional workspace-document creation; Plan `Create New Prep` is consumer #1 (`b8e4dd2`).
- PR #546 — Plan session affinity decoupled from durable storage; multiple same-session prep documents get distinct server-owned workspace paths (`32a3268`).
- PR #548 — Create New Prep interaction/layout stabilization (`c914c48`).

### Shared surface context

- PR #551 — persistent World Graph status in AppChrome plus generic `SurfaceContextHost`; Plan PREP first adopter (`721bf32`).

### Build document workflow

- PR #556 — Build DOCUMENT context, intentional exact load/switch/create, no bare-entry auto-create (`7cbf9e5`).
- PR #558 — corrective campaign-authority derivation and single-lane Canvas admission (`53424b6`).
- PR #560 — revision-safe Build source rename. Rename PATCHes the Canvas session's live revision, rebases the returned metadata revision into the same live Canvas, preserves body/SHA/dirty/editor identity, serializes against Save, and leaves World Graph projection intact. Final implementation head `3334188…` received CODE REVIEW: PASS and merged as `85a2bbf…`.

## What is no longer an open DOGFOOD-POLISH item

The following should not be redispatched under this workstream:

- Plan exact prep selection;
- Plan intentional prep creation;
- multiple Plan preps for the same session;
- Plan session-affinity/storage decoupling;
- generic Surface Context Host / global World Graph status;
- Build bare-entry auto-create removal;
- Build exact source selection / switching / creation;
- Build campaign-authority / single-admission repair;
- Build exact World Graph reference insertion into Canvas — this capability already exists in current Build composition;
- Build document rename;
- a literal Plan-style Build heading bar. Current ownership is DOCUMENT Surface Context for title/status, shared Edit Host for Save, and Canvas for the work object.

## Residual product work — survives outside this workstream

Closing DOGFOOD-POLISH does **not** mean the product is finished. These are independent READY/future tracks and should be scheduled on their own product pull:

1. **Plan Ask continuity across prep-document switches.** Canvas `documentId` and Agent/Hermes conversation continuity are different authorities. Switching prep documents should update the active document context without accidentally defining a new conversation unless the operator explicitly starts one.
2. **Shared Threat projection / Statblock tool parity.** Build already has graph-reference insertion and chip runtime; the remaining gap is that the same Threat should resolve to the same campaign-facing Threat/Statblock projection on Plan and Build, with Workbench remaining a separate authoring tool in the shared Tool Host.
3. **Build document lifecycle/recovery UX.** Ready-state Reload / Discard-local-changes placement can be designed through shared Edit ownership. Durable source discard/archive/restore is a separate destructive lifecycle problem and must not be conflated with local draft recovery.
4. **Play Surface Context / Plan→Play handoff.** This is the next surface-composition problem, not unfinished Plan/Build polish.
5. **MAGIC-D3 / Hermes performance and presentation.** Threat glance quality, graph-load retention, hydration latency, and honest Hermes progress are performance/presentation work, not document-context work.
6. **Worldbuilding elevation / authority promotion.** `draft → reviewed → canonical` remains a governed graph-authority design problem. Rename/light metadata does not authorize casual promotion controls.

## Closeout rule for future agents

Historical DOGFOOD-POLISH handoffs are dispatch records, not current sequencing authority. When a handoff's old `Status:` line conflicts with this report plus the current repository, treat the repository and this closeout as newer authority.

Do not reopen DOGFOOD-POLISH merely because one of the residual items above becomes important. Give that work its own invariant, owner, and workstream.

# Design note — Authoring blank shell must precede document resolution

**Created:** 2026-08-28  
**Audience:** PLAY-SURFACE designing agent  
**Branch:** `agent/play-surface-runbook-authoring-gateway`  
**Related handoff:** `Docs/Plans/HANDOFF-PLAY-SURFACE-runbook-authoring-gateway.md`  
**Status:** HISTORICAL — resolved by PLAN-BLANK-SHELL / PR #661

Resolved at accepted head `ffa0b18d6212a6780d6be90f91a25626bf15b464`, merge
`770f79cca4aa3c12aa8a35db2db77ce376f2ff9e`, 4 review cycles. BF4A no longer owns
blank-shell semantics and must leave that machinery alone.

This is a product/design correction discovered while trying to make BF4A genuinely dogfoodable. Do not treat it as an implementation detail and do not hide it behind fixtures or exact-URL operator knowledge.

## Foundational UI flaw

We made authoring chrome conditional on successful document resolution instead of making a ready blank document the default surface state.

Plan currently treats “no resolved planning document” as “no surface inventory.” The shell publishes no surface until a document is ready:

```tsx
// apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx
useEffect(() => {
  if (documentLoadStatus !== "ready" || !publicationRef.current) {
    return publishProjectionSurface(null);
  }
  return publishProjectionSurface(publicationRef.current);
}, [documentLoadStatus, publicationInstanceKey, publishProjectionSurface]);
```

Then the shared hosts hide themselves when that publication has no matching inventory. Edit Host returns `null` without matching commands/panels:

```tsx
// apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.tsx
const matchingCommands: SurfaceInteractionEditCommandContribution[] = workObject
  ? (publication?.editCommands ?? []).filter((command) =>
    targetsMatch(command.target, workObject))
  : [];
const matchingPanels = workObject
  ? legacyPanels.filter((panel) => targetsMatch(panel.target, workObject))
  : [];
const hasInventory = matchingCommands.length > 0 || matchingPanels.length > 0;
```

```tsx
if (!hasInventory) {
  return null;
}
```

Tool Host does the same for tools:

```tsx
// apps/live-control-ui/src/surfaceInteraction/toolHost/ToolHost.tsx
const tools = surfaceInteractionPublication?.tools ?? [];
const identity = surfaceInteractionPublication?.identity ?? null;

const [isOpen, setIsOpen] = useState(false);
```

```tsx
if (tools.length === 0) {
  return null;
}
```

That creates the bad operator state: on wide `/plan`, if document resolution is empty/error — or if the admitted document is exact-ID but not present in the plan selector list — the surface can collapse to top nav plus agent chrome. The controls needed to recover, create, open, unlock, or understand save state are the very controls hidden by the missing document.

## Design correction

Entering an authoring surface must always load a **ready blank document/draft shell**.

“Blank” is a first-class local WorkObject with explicit local identity and truthful save gating, not the absence of a document.

Chrome is surface-owned and always mounted on authoring surfaces; individual commands may be disabled with reasons, but Edit/Tools hosts must not disappear.

Keep authority gates separate from visibility gates:

- Locked/unlocked remains an Edit capability.
- Save remains gated by document rules: BF4A allows native Runbook save with `target_relpath=null`; Plan still requires a durable path.
- Empty/error document resolution changes canvas body and command availability, not host existence.
- Exact `documentId` admission keeps chrome even when the Plan selector lists only `kind=plan`.
- First save promotes the local blank draft to an exact workspace `documentId` and updates the URL without discarding editor state.

## Acceptance for the correction slice

The corrected authoring contract must prove all of these ordinary product states:

```text
bare /plan
/plan?documentId=<runbook>
selector-empty
document-load-error
```

In every case:

- Edit chrome remains visible.
- Tools chrome remains visible.
- The Edit host exposes an obvious **Unlock editing** path.
- Disabled commands remain visible with truthful reasons when they cannot execute.
- The Agent bar is never the only visible surface chrome.
- A missing/unresolved document never removes the controls required to create, recover, open, unlock, or understand save state.

For the blank-draft path specifically:

```text
enter authoring surface
→ ready local blank draft shell exists
→ authoring chrome already present
→ edit locally without requiring a persisted document
→ first Save creates/promotes exact workspace WorkObject identity
→ browser URL adopts exact documentId
→ editor state is preserved across promotion
```

The first-save promotion must not imply that every document is automatically saveable. Existing authority rules still apply:

```text
Runbook
  target_relpath may be null
  ordinary APP-STATE WorkRevision Save is valid

Plan
  durable-path requirement remains unless separately redesigned
```

## Relationship to BF4A

This is **not a BF4A regression**. BF4A exposed a pre-existing authoring-surface contract problem by making APP-STATE-native, pathless Runbooks reachable through normal Play.

The designing agent must explicitly decide one of these before implementation continues:

1. **Amend BF4A** if the blank-shell/chrome correction can remain one coherent independently useful authoring-gateway slice with a bounded write lease; or
2. **Split a predecessor authoring-shell slice** if fixing surface-owned always-present chrome and local blank identity materially exceeds BF4A’s current lease/mission.

Do not proceed by treating `?documentId=<uuid>` + paste as sufficient dogfood. Do not add ad hoc visibility exceptions to EditHost/ToolHost without resolving the surface ownership contract.

## Why this matters

We are repeatedly running into assumptions that were never tested against the zero-material first-use state:

```text
"a document will already exist"
"the operator can somehow reach its UUID"
"surface chrome only matters after content resolves"
"dogfood can begin from a fixture"
```

Those assumptions are now producing false-positive implementation readiness.

The design standard going forward should be:

> **Every new authoring capability must prove the first experience with no loaded material, not only the happy path with a previously admitted document.**

That means dogfood acceptance should start from the actual product entry state whenever practical, including empty collections, unresolved identity, first local draft, first Save, and reload/re-entry.

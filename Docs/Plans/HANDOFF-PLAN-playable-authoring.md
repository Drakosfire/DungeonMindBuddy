# Plan-owned Scene and Beat authoring

Status: ACTIVE. PRIME design/implementation under the active Build→Plan→Play dogfood goal. Existing buddy-context-loop checkout; branch codex/plan-playable-authoring; base005a2e86fd15ba5eaf74bbf48ab6c0d1667b21c0. Serial one PR; independent ARCHITECTURE exact-head review before merge/delivery5202. No concurrent Plan code owner identified in current open PRs; historical1188 remains open but current slice does not alter blank welcome/default text/lock policy.

Observed blocker: ordinary authored headings saved and linked Mirathorn source correctly but Start Run rejected them as lacking a Scene/opening Beat. Manual canonical marker paste proved saved revision→Run continuity, not ordinary authoring UX. Architectural recommendation adopted: explicit Plan-owned structure actions, never heading inference/conversion.

Product decision: an explicit Add Beat action establishes v2 Beat-first structure in an unmarked Plan. Existing valid v1 remains Scene-first; existing v2 remains Beat-first. No automatic conversion or version mixing. Scene/Beat insertion only; Choice/Option authoring is outside this slice. Ordinary headings stay ordinary.

Actions: v2/unmarked Add Beat appends a new root Beat; Add Scene to this Beat inserts at the end of the current legal Beat, before the next root heading. v1 Add Scene appends a root Scene; Add Beat to this Scene inserts at the current Scene end. Current legal parent comes from the actual current editor selection/root hierarchy, not a stale captured caret or title. Disabled reasons explain missing parents or blocked structure. No dialog or async target capture. A current document/selection generation fence prevents stale toolbar actions from mutating a different target. Rename uses normal selected heading text. Each successful insertion creates one fresh canonical kind-prefixed UUID and one transaction. No automatic Save, source admission, provider call, publication or Run mutation.

Safety: current editability and destroyed checks, current Plan/epoch/save/conflict/protection guards; complete existing/resulting identity index and semantic roundtrip validation before apply. Invalid/mixed/duplicate/nested identity blocks. Preserve all other authored nodes, links/images/frontmatter/IDs and existing Run pins. Empty blank root placeholder may be replaced only when it is the entire empty document. Do not silently remove spacers elsewhere.

Exclusive write lease:
- This handoff.
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/planPlayableAuthoring.ts
- apps/live-control-ui/src/planSurface/planPlayableAuthoring.test.ts
- apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx

Verification: real editor command v1/v2/blank/parent matrices, semantic identity persistence and rename/undo/redo, readonly silent toggles, invalid/mixed/duplicates/nested identities, immutable neighboring authored content, stale scope/selection and no-op failures. Mounted Plan-owned toolbar→real editor→ordinary mocked Save/reopen, existing exact Start Run revision tests. Typecheck/build/cumulative diff. Then rendered explicit toolbar→Save→Play→Run→reload on disposable Plan only; existing Run stays pinned after later Plan save. Existing5202output/dependencies reused, no new server/worktree/provider or database migration. Do not modify/recover/save operator Edge/Mirathorn source.

Implementation checks:73 tests across real insertion commands, both identity indexes, edge conformance and exact Start Run binding pass; mounted Plan-owned toolbar through explicit mocked prepare/commit/reopen passes (69 unrelated cases not selected). TypeScript and Vite production build pass (inherited large-chunk advisory). The first command test exposed canonical v1 attrs use null version rather than literal v1; corrected. The mounted boundary exposed benign editor-state hydration changes object identity without authored/selection change; guard now compares semantic doc+selection plus Plan draft/selection generation fences, preserving ABA rejection. No live or provider call by this slice; full rendered acceptance pending independent review/delivery. User separately authorized DOGFOOD's savedSession29 providerverification; no Plan/Build runtime collision.

Review cycle1 HOLD exposed inherited Plan onUpdate dropping stripped leading YAML. Repaired the owned export boundary with the existing preserveLeadingYamlFrontmatter helper; source envelope retained byte-for-byte for every local export. Mounted toolbar/Save/reopen witness now includes CRLF YAML envelope and asserts exact prefix. No new backend contract or metadata editing. Distinct-head rereview required.

---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J2
  - Direction: STEWARD → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DEMO-plan-agent-reviewed-edit-v1.md
  - PR topology: serial within DEMO; #782 is merged

  ## Review contract
  An Agent turn must be able to propose prose and an existing registered
  Markdown component for the exact selected Plan target, have the GM review and
  apply that proposal to the mounted editor, then revise it in a later turn.
  No model response may mutate durable storage or overwrite a changed draft.
---

# HANDOFF — DEMO: reviewed Agent edits on the Plan canvas

**Created:** 2026-09-27
**Status:** ACTIVE — DEMO-J2 first Agent-to-Plan authoring capability
**Conversation/workstream:** LOCAL DEMO ACCEPTED / DEMO-J2
**Flow / owner:** DEMO / Buddy Plan and Agent interaction
**Direction:** STEWARD → CODE → REVIEW
**Design/activation base:** Buddy `main@20a301a4b7edeca6ac71cf46e321836a156909a8`, after #782 merge `9d31fef89e74a4e8b1f6fd9a5d4f9ed98f283437` and the guarded J2 dogfood record
**PR topology:** serial; open exactly one implementation PR titled `DEMO: apply reviewed Agent edits to Plan`
**Runtime/state ownership:** use fixtures for tests, then the isolated `of-conks-j1-fresh-rehearsal` World and its dedicated Buddy/APP-STATE databases on the existing local demo ports; never C1/C2
**Concurrent-lane check:** open #781 leases only its semantic-action projection pair and handoff; open #780 leases v6.5 evidence-preservation documentation/test paths. Neither leases the expected Plan edit files or isolated Of Conks runtime. Recheck at dispatch.

## §1 Mission and merge-ready invariant

The GM selects a destination in the mounted editable Plan, asks DungeonBuddy
to compose or revise it, reviews a concrete proposed change, and applies it to
that same Plan draft. A later Agent turn can revise the applied content. The
accepted content includes ordinary prose and at least two existing registered
Markdown component shapes: a callout (`READ-ALOUD` or `GM-NOTE`) and a
Decision/Consequence block. The user can then save, reload, and still edit the
result using the existing Plan authoring path.

The Agent proposes; the GM applies. A model response cannot write to APP-STATE,
the filesystem, or DungeonMind. Applying the proposal must use the mounted
TipTap editor so its local dirty draft, undo history, Markdown round-trip, and
revision-safe save contract remain authoritative. An old proposal must not
apply to a different document, World, revision, selection, or editor body.

This is one independently useful capability: **reviewed Agent-to-Plan editing**.
It does not claim all registered component types, graph publication, source-
verified grounding, or the full DEMO journey. The roadmap retains those gates.

## §2 Evidence and current authority

The exact #782 live Of Conks Plan at document
`23263744-03f3-4074-984c-b31f5d4704e4` opened Hempholm and answered a
World question. Two subsequent real Hermes turns asked for an opening scene to
be written into that Plan. The first produced prose in chat and offered to
write it later; the explicit follow-up said it lacked direct document editing
access and asked the GM to copy/paste. The canvas did not change. The test
used a runtime-only `gpt-4.1-mini` override, not a model-policy edit.

Current seams:

- `PlanAgentInteractionBar` calls `/api/live/query`; it receives document
  metadata through `AgentSurfaceContext`, not the current mounted editor body
  and not an edit command. Its ordinary Ask remains a read-only answer path.
- `PlanSurfaceCanvas` owns `useWorkspaceDocumentAuthoring` and the mounted
  `MarkdownEditorCore`. Local unsaved content can differ from the server
  snapshot. `saveMarkdown()` already checks Markdown safety and uses the
  existing prepare/commit revision contract.
- The editor already registers callout and Decision/Consequence nodes and the
  Markdown importer/serializer. Reuse those, including their diagnostics; do
  not introduce a second component representation.
- The accepted selected-World and Plan-read path binds the Plan document to
  the managed World with explicit world scope and a blank nested campaign.
  This slice may consume that context, but must not relax its validation.
- Buddy #783 tracks the separate published-source typed-locator defect. Do
  not represent unsupported source anchors as verified citations here.

OpenAI's [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
supports a strict JSON-schema response for
an inert proposal, with separate refusal/incomplete handling. It does not
make the returned content semantically safe; Buddy must still validate the
fragment and require human review. Use the existing Buddy/GenerationEngine
structured-generation pattern and current `structured_generation` model role.
Do not add a hard-coded model, second model policy, or a new generic agent
framework. The exact model actually used and its timing/usage must be reported
from execution, not inferred from the manifest.

## §3 Contract and user sequence

1. Ordinary Ask remains read-only. It must no longer imply that another Ask
   turn alone can write directly to Plan. A visible Compose/Revise-in-Plan
   action belongs in the existing Plan Agent chrome, not a second drawer.
2. The GM chooses the destination in the actual Plan editor: a selected block
   or range for replacement, or an explicit caret position for insertion.
   Capture and show the exact target before model execution. No invisible
   model-selected document target. The observed `Opening frame` placeholder
   must be reachable by ordinary click/selection, with no console or manual ID.
3. Capture the exact current editor body, selected target, local draft
   generation/fingerprint, document ID, loaded base revision/content digest,
   selected World ID, and current Agent-thread history. The server resolves
   and verifies document/World/session ownership; client-supplied draft bytes
   and thread history are untrusted proposal context, never source or durable
   authority. Bound payload sizes and history; reject a foreign/inactive
   document or mismatched base. This slice may describe World-supported
   context, but must not upgrade #783's unreadable anchors into source-verified
   citations.
4. One explicit Compose/Revise request produces a typed, inert proposal. The
   model returns a Markdown fragment, a brief change summary, and explicit
   assumptions/proposed invention; it does **not** choose paths, durable IDs,
   graph identities, target coordinates, or write effects. A refusal, empty
   answer, malformed output, or unsupported marker yields no apply action.
   Record the request and proposal outcome in the existing Plan Agent thread
   so the later revision turn can see what was proposed/applied; do not create
   a second conversation store or pretend the proposal was an ordinary
   graph-grounded Ask answer.
5. Parse the proposed fragment with the existing semantic Markdown importer.
   Reject lossy or unsupported syntax, raw HTML, fabricated graph-reference
   IDs, and content outside the registered Plan grammar. Prove serialize →
   import preserves prose, callout kind/body, and Decision/Consequence panes.
   The proposal preview shows the exact target and before/after content;
   `Discard` leaves the editor untouched.
6. `Apply to draft` rechecks the mounted editor and all captured bindings.
   A changed selection/body, local edit, save/reload, document switch, or World
   switch invalidates the proposal. If still exact, apply **one editor
   transaction**; the existing onUpdate/local-draft path marks it dirty and
   supports undo. Applying does not silently durable-save.
7. The GM saves through the existing Markdown save action. A later Agent turn
   sees the current editor body, can revise the previously applied content,
   and follows the same preview/apply/save sequence. On reload, the saved
   prose and component nodes remain editable and semantically identical.

The proposal service may be a Plan-specific route, but it must not be a second
durable document writer. Do not turn ordinary Ask's free-text answer into a
blind edit command. If the existing generation adapter cannot emit a bounded
structured proposal without changing Hermes or GenerationEngine's public
contract, stop and rebrief rather than parse conversational prose by regex.

## §4 Files in scope — ACTIVE write lease

| Action | Path | Boundary |
| --- | --- | --- |
| Add | `apps/live_control_server/models/plan_document_edit_proposal.py` | Typed inert request/result |
| Add | `apps/live_control_server/services/plan_document_edit_proposal.py` | Verified Plan binding, bounded structured generation, no mutation |
| Modify | `apps/live_control_server/routes/live.py` | One Plan-specific proposal route; ordinary Ask unchanged |
| Add | `tests/test_plan_document_edit_proposal.py` | Route/service adversarial proof with injected model |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Typed proposal request |
| Modify | `apps/live-control-ui/src/api/types.ts` | Proposal wire types |
| Add | `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts` | Exact target/proposal admission and Markdown validation |
| Add | `apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts` | Deterministic stale/grammar/round-trip cases |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx` | Local Plan canvas ↔ Agent controller bridge; no global store |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Capture/apply in the mounted editor only |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Compose/revise and review UI inside existing Agent chrome |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` and `agentInteractionHistory.test.ts` | Existing thread continuity for proposal turns |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Bounded proposal review presentation |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` and `components/PlanAgentInteractionBar.test.tsx` | Owning-boundary integration proofs |
| Add | `apps/live-control-ui/src/planSurface/PlanAgentReviewedEdit.integration.test.tsx` | Mounted editor apply/save/reload witness |

The #782 completion and first J2 witness are already synchronized in the
roadmap and mirror at the design base; no predecessor state edit is owed by
this PR. Bounded discovery: if the existing Agent public re-export or shared
thread test must change, add only
`apps/live-control-ui/src/agentInteraction/agentInteractionStorage.ts` and its
focused test to the lease in this PR with a written reason. No other shared
Agent contract, model policy, lockfile, DungeonMind, WorldKeeper, or corpus
path is leased. Stop for steward transfer if another active lane owns a needed
path.

## §5 Failure matrix

| Condition | Required outcome |
| --- | --- |
| No explicit editor target / editing locked | No model write; explain how to select/unlock |
| Foreign World/document/session or inactive Plan | Reject before model call |
| Unsaved local draft | Proposal sees that exact draft; no forced save or discard |
| Model refusal/invalid schema/incomplete output | No proposal apply affordance |
| Unsupported or lossy Markdown component | Show validation failure; editor unchanged |
| Model invents graph ID/path/HTML/unknown component | Reject, no coercion |
| Local editor changes after proposal | Stale; no partial mutation |
| Document/World/revision changes after proposal | Stale; no cross-target mutation |
| User discards proposal | No mutation or save |
| Apply succeeds but durable save conflicts | Local draft retained; existing conflict UX, no silent overwrite |
| Model or API failure | Retryable error; no local or durable mutation |

## §6 Evidence required to merge

- Exact base/head, cumulative diff, lease check, Ruff, focused TypeScript tests,
  scoped Python tests, UI typecheck with inherited failures distinguished,
  and `git diff --check`.
- Server route test: verified managed-World/Plan binding and observed model
  invocation; foreign World, wrong document/session, stale base, malformed
  response and model failure result in zero mutations.
- Controller/editor integration tests: unsaved local draft preserved; chosen
  target captured; prose plus `READ-ALOUD`/`GM-NOTE` and Decision/Consequence
  apply as registered nodes; proposal discard, stale body, stale selection,
  locked editor, navigation, save conflict, undo, save/reload all behave as
  stated. A helper-only parser test is not the editor witness.
- Two real model turns in the isolated Of Conks browser: compose a short
  Hempholm opening at the selected Plan target, review/apply/save; then ask
  for a revision across turns, review/apply/save; reload and inspect the
  actual editable nodes. Record actual model, calls, usage/cost if provided,
  model latency and wall time. Do not count text sitting only in chat. If the
  existing Plan has an unsaved local draft, preserve it and create a fresh
  test Plan through ordinary controls rather than discarding or overwriting it.
- Verify ordinary Ask still reads the exact managed World and campaign-scope
  regression tests remain strict. The current #783 source-open limitation is
  disclosed, not called a J2 failure or silently fixed in this PR.

## §7 Handback and acceptance rubric

Hand back the exact head, commit story, affected paths, tests, real browser
receipt, model/cost/latency receipt, observed limitations, and any necessary
successor. Do not claim J2 or LOCAL DEMO ACCEPTED from this slice alone.

The slice passes only when the GM can see the proposed edit land as editable
Plan content, revise it in a later Agent turn, and save/reload it without
losing an existing local draft or silently changing a different document.
If the only result is a good chat answer or manual copy/paste, HOLD.

**Stop/rebrief:** a new generic Agent tool registry, a new durable writer,
DungeonMind/WorldKeeper schema work, parser syntax expansion, arbitrary
unreviewed edits, or a second independently useful product workflow.

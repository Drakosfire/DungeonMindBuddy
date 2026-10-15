# DOGFOOD: complete Build shared workspace integration

Status BLOCKED for implementation pending ARCHITECTURE source-binding design
review; operator explicitly authorizes design and one coherent implementation PR.
Design base d92a916220fe1d800936cfffe25288f9f770aad4; branchcodex/build-shared-workspace;
non-serving checkout /home/drakosfire/.codex/worktrees/editor-mount-cleanliness/DungeonMindBuddy.
Topology serial one PR. Designing steward DOGFOOD; PRIME coordinates cross-owner
contracts and merge; ARCHITECTURE reviews. No provider/serving/state lease yet.

## Intended invariant
Shared workspace navbar/Edit/Tools/Buddy remain in consistent places; active
surface supplies context/capabilities underneath. Build uses shared Markdown
formatting, node-reference presentation, outline/navigation and editing; worldbuilding
adds source/extraction/review capabilities, not a second chat or editor system.
Complete one end-to-end Build consumer of the shared contracts in one PR.

## Proposed UX
- One shared Edit launcher at the left document edge; shared Tools on right and
  shared conversation launcher/dock. Normalize their placement through sharedhosts.
- Remove Build's separate Read/Edit buttons. Shared Edit host exposes source
  editing mode/document actions plus an outline usable while reading.
- Extract heading/anchor generation from BuildSourceReader into shared Markdown
  outline presentation, preserving exact duplicate anchors/source line positions.
- Shared Markdown node-reference rendering follows the existing graph mention
  capability and projection navigation. Preserve original source bytes; never
  infer node IDs from unverified text or invent graph links.
- Existing compact Extraction navbar menu remains intact.
- One persistent World conversation across Plan/Play/Build; same composer,
  evidence/debug/pending-recovery behavior. No Build-only conversation store.

## Authoritative Build-source contract (proposed for review)
Use existing surface-neutral /agent/turn, owner_scope verified managed World,
surface_id=build and primary_work.kind=build. Client supplies document ID,
expected saved revision and expected SHA256, never Markdown/path/authority.
Server reads registry-backed snapshot from managed World root, verifies active
worldbuilding_source kind, exact World ownership, committed status, revision/hash
and original source bytes. Missing/stale/foreign/uncommitted fail before runtime.
Unsaved edits are declared and excluded from saved-source context, never auto-saved.
No Plan-only WorkRevision/revision_n fabricated for a Build registry source.
Resolved source context carries title/document/revision/hash and exact saved text
as explicitly labelled source material (not instruction/canon/played-event truth).
Source domain/class/authority/visibility retained; source text cannot override tools.
Shared Graph request/receipt/evidence path reused; no bypass of World/nativebinding
or GM/player rules. No automatic source admission/extraction/publication.
Durable conversation turn records exact Build basis and never falls back to lastPlan.
Retry must not silently rebind to later saved bytes. If current append-only registry
cannot reopen that exact basis, fail closed with truthful terminal/recovery state;
no blind redispatch. Reuse existing history/idempotency/trace APIs, no new DB schema.
Source-aware answers must be demonstrably based on this saved source in owning
fake-runtime tests; displaying context labels is not proof. Build source write
commands remain limited to explicitly admitted shared document commands; no
provider-direct Save or Graph mutation. Any proposed Agent edit application must
reuse an existing verified preview/confirmation contract or return to stewardship.

## Concrete source transport and historical basis amendment

The registry document ID is the existing artifact identity; the registry has no
separate artifact ID. Do not invent one. The internal resolved-work carrier gains
a Build-specific saved-source basis with exact UTF-8 bytes and verified metadata.
It is separate from plan_markdown and Plan WorkRevision fields. Turn service wraps
invocation.message as JSON data containing user_question and saved_source (identity,
World owner, registry revision, digest, title, domain/class/authority/visibility,
and exact content). Persist the original user question separately. Both existing
adapters consume invocation.message; no adapter/assembler write is required.
The bounded descriptive surface-context renderer never carries source content.

Proposed durable codec uses existing typed provenance fields, without schema change:
- primary_work: resolution resolved, kind build, object_id document ID,
  revision canonical positive decimal registry revision, content_sha256 exact hash;
  object_revision/work_revision_id/revision_n remain null.
- World owner: TurnProvenance.world_id, checked against request and registry owner.
- supporting_work: exactly one reserved dmb_build_source_visibility_v1 reference,
  object_id internal or player_safe, revision 1; all digest/Plan pins null.
Strict encode/decode rejects duplicate, malformed, foreign and mismatched references.
This codec is proposed for ARCH/APP review, not silently activated by this document.

Registry revision binds metadata as well as content: update_workspace_document
applies title/class/authority/visibility changes with revision=existing.revision+1
under registry CAS (workspace_document_registry.py). source_domain is fixed by
worldbuilding_source creation. Implementation must prove each supported metadata
change increments revision and invalidates the prior basis, including same-body
changes, using the real registry mutation API; otherwise activation returns to
stewardship for explicit lossless metadata freezing. Document ID is the registry
source identity, never a native SourceArtifact identity or admission claim.

The registry does not retain immutable historical source bodies. Retry can reopen
only a current snapshot matching every frozen identity/revision/digest/privacy pin;
changed or missing source fails closed, before dispatch. Never substitute later
bytes. Preserve durable completed history and uncertain-dispatch recovery without
reposting. Build source Ask and its transcript are GM-only; prove history/recovery
cannot expose previous GM source content to Player or another World.

Request model permits required Build saved hash with registry revision and forbids
Plan revision_n on Build. Resolve only active committed worldbuilding_source under
managed root with containment/symlink checks, valid metadata, verified byte hash.
Reject missing/stale/foreign/oversize source before turn claim/runtime. Maximum
canonical saved-source UTF-8 size is 131072 bytes (128 KiB); reject larger sources
with 413 before claim, never silently clip text. Hash precisely the registry snapshot
Markdown after its existing CRLF/CR-to-LF normalization and verify its reported SHA.
Do not alter file bytes or claim raw-byte identity.
Source Ask is read-only: no proposal/apply capability is claimed in this slice.
Existing conversation_only_v1 or world_graph_read_v1 capability policy is enforced
at runtime/tool admission; no edit/source-save/graph-write tool is added. Prove the
actual policy on Build invocations and rejection of unauthorized tool attempts;
quoting source data is explanatory defense, not a permission boundary.
Existing /agent/turn, World history, trace and command/recovery routes authenticate
GM before storage/runtime reads. Tests cover each reachable transcript/trace/recovery
read against Player and mismatched World, not only initial submission. Browser
pending request stores identities/question only, no source body; shared state is
keyed by selected World and clears on World change. No visibility marker is an
access grant. No bypass through prior Plan context or stale source registration.
Unsaved document editing remains the shared user-operated Edit host capability.
Test actual invocation bytes using fake runtime, injection-shaped source as data,
strict codec round-trip, historical change rejection and no duplicate dispatch.

## Cross-owner validator amendment
PRIME explicitly authorizes inclusion of the APP-owned SubmittedPrimaryWorkIntentV1
validator hunk and focused owning tests in this single coherent PR, contingent on
APP confirming collision-free transfer and ARCH reviewing this exact amendment.
Only the Build digest/registry-revision branch changes: required saved SHA, no Plan
revision_n. Plan/run/combat validation and historical fingerprint compatibility
remain unchanged. No schema/store semantics change or other APP type edits.
APP confirmed no overlapping edits and exclusively transferred this exact validator
and new test path to DOGFOOD. ARCH activation remains outstanding; no code lease yet.

## Proposed exact write set (not leased until activation)
Docs/Plans/HANDOFF-DOGFOOD-build-shared-workspace.md
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx
apps/live-control-ui/src/agentInteraction/AgentInteractionChrome.tsx
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.test.tsx
apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.tsx
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/chrome/AppChrome.tsx
apps/live-control-ui/src/styles.css
apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.tsx
apps/live-control-ui/src/surfaceInteraction/editHost/EditHost.test.tsx
apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
apps/live-control-ui/src/buildSurface/BuildSourceReader.tsx
apps/live-control-ui/src/buildSurface/BuildSourceReader.test.tsx
apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx
apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx
apps/live-control-ui/src/buildSurface/buildSurface.css
apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.tsx
apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.test.tsx
apps/live-control-ui/src/markdownReader/MarkdownDocumentOutline.tsx (new)
apps/live-control-ui/src/markdownReader/MarkdownDocumentOutline.test.tsx (new)
apps/live_control_server/routes/agent.py
apps/live_control_server/models/agent_turn.py
apps/live_control_server/services/agent_surface_context.py
apps/live_control_server/services/agent_turn_service.py
tests/test_agent_build_surface_context.py (new)
tests/test_agent_build_submitted_intent.py (new)
src/application_state/agent_conversation/types.py (SubmittedPrimaryWorkIntentV1 validator only)
tests/test_agent_turn_service.py

PRIME reserved files NOT in lease: agent_context_assembler.py,
selected_subject_initial_sources.py, hermes_graph_agent.py,
pydantic_ai_agent_runtime.py, graph_memory/interaction/session.py,
agent_graph_policy.py. Any needed shared hunk must be serialized explicitly.
No dependency/lockfile/schema/ingestion/corpus/nativeGraph edits.

## Verification and gate critique
Test actual owning source resolution + turn dispatch, forged/stale/foreign/noncommit
rejection, saved_dirty excludeslocal, document/Worldswitch clearsoldcontext,
exact historicalbasis/retry/no duplicate dispatch, onepersistent conversation,
Plan/Play regression and trace/evidence compatibility. Source-aware UI must not
claim mutation capability that was not admitted. No public source content leakage.
Test UI sharedhost composition, no duplicate modecontrol, outlineanchors and node
reference behavior, editclean/CAS retention, extraction unchanged. Actual390/647
Build/Plan/Play controls and source reopen; saved Mirathorn rev2/SHA70444f40…
unchanged. Review cumulative exact main→head, tests/types/build, code review,
then bounded owned5202 acceptance. Open assigned PR; PRIME merges separately.

Current runtime remains reviewedbaad/Core33db on5202; no source/model/Graph writes.

Baseline verification before implementation: shared MarkdownDocumentReader and
BuildSourceReader suites pass; combined three-suite run has 46 passed / 2 failed.
The inherited Plan/Play integration failures concern uncertain Play recovery after
switching to Plan and reopening a frozen Play request (composer disabled expectation).
Do not report a clean baseline or hide these during final integration verification.
Snapshot text/digests follow existing registry normalized-newline semantics; do not
claim a distinct raw-file-byte hash or change the source normalization contract.

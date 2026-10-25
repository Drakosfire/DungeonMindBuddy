# BUILD — real on-page table construction

IMPLEMENTATION DELIVERED through1719–1721; original lease below is historical.
Combined ordinary recovery proof continues with the shared-composer successor.
Independent exact-head design critique APPROVED
f0bf0e727f94c13ca805306c63fdf40782c663d2; activation2026-10-24 after
GE27 merge and consumer ownership inspection. Serial topology: one Buddy implementation PR, after
OverMind PR55 (guarded authoring stream contract) and GE PR27 merged.
Base40b7f395bfdfad04b3ca0d6de3076c6ae6bfeb1f; branch
codex/build-table-construction-stream, existing buddy-context-loop checkout.
GE dependency3e085168c11bdee0de580b8cfa0f00cee157c157. No overlapping
writer/transport/Surface lease found among open PRs at2026-10-24 re-anchor.

## Rendered-proof correction — initial reveal

PR1719 merged3ce378df81b113af354587f797fc89aa215450a6 and protected API/UI
adoption preserved2581 APP rows, native state,27 frozen components and89 product
files. Ordinary synthetic proposal/edit/Save/reload passed. Edge real progress
was observed at5/13/19 rows before final admission, but its first screenshot
proved the preview was below the viewport after conversation collapsed.
PRIME authorizes one serial correction PR from this merge: use the existing shared
SurfacePageProposal reveal contract once when the first actual table is present.
Exclusive correction writes: BuildConstructionPreview.tsx, its owning test, and
this handoff only. No row-follow scrolling, document edit, new Surface contract or
other capability. Independent exact-head review and protected UI delivery remain
required; ordinary visible growth and disconnect/reload gates remain open.

## Rendered-proof correction — recovered proposal refresh

PR1720 merged656783705258fc31cbae040f757d78b5f0d2cab6; protected UI adoption
preserved2601 APP rows and unchanged API. Bog Blossom's first actual row appeared
at6.052s inside the viewport (top383/bottom551 in655px). Ordinary reload at that
point retired delivery; the exact turn completed once on attempt1 with unchanged
source revision112/hash. Recovery settled the turn but left the proposal list at
its earlier in-progress snapshot until another reload.
PRIME authorizes one serial correction PR from656783705: refresh Build proposals
only when validated exact pending-turn recovery settles unchanged/absent envelope
bytes. Exclusive writes: WorldPlanAgentConversation.tsx, its existing mounted
planPlay integration test, this handoff. No new execution, routing or persistence
contract; no unrelated draft-storage change. Independent review and protected UI
adoption plus ordinary reload proof are required. Newer unsent composer text is
currently memory-only and was lost across reload; that distinct recovery gap
remains open for its own bounded storage contract.

## Capability and ownership

A requested Build table visibly grows at its captured page placement from actual
writer output. After GE structural conformance and existing Buddy domain admission,
the existing editable proposal replaces this inert preview. Author-owned Save,
placement, recovery and draft handling remain unchanged. Discussion and Play/Plan
writers are outside this slice. Prose-only proposals may use the same streaming
execution, but do not gain a new authored-content preview mode.

The actual proposal owner is _proposal → compose_with_writer → _compose. Its
BuildGeneratedProposal contains replacement_markdown as one JSON string. GE owns
schema conformance and exact-byte dispatch; Buddy owns operation/turn/attempt
reconciliation and publication; shared Surface owns safe on-page presentation.

## Transport and lifecycle

Use the existing authenticated POST /agent/turn with explicit Accept:text/event-stream
for Build only. All other surface requests keep their current API. This is one
submitted command and one durable execution, not a subscribe request plus a second
generation. Authenticate before returning a streaming response; the existing durable
route owner still verifies request, World and turn authority inside its worker.

Run that existing synchronous execution once in an owned worker task. Carry an
operation-local progress sink via contextvars into its existing asyncio.run writer.
Hold the task until actual terminal; a browser disconnect retires delivery without
cancelling/reissuing inference. No global progress/history cache, poll endpoint,
reconnect generation or database migration. An application-local strong task set
exists only for resource lifetime and releases completed tasks. Shutdown and
protected delivery still respect active durable turns.

A coalescing mailbox holds only the latest progress snapshot plus a distinct final
result; no unbounded queue of deltas. Observation is fail-open: a preview-sink or
parser error cannot corrupt durable authoring or authorize another call. The final
response is the existing route JSON response inside a terminal SSE envelope. Route
HTTP errors retain status/detail in a terminal error envelope; unexpected errors
use a safe generic error. EOF without a terminal remains uncertain and enters the
existing saved-request reconciliation; no automatic resend. Auth failures before
stream headers use ordinary HTTP errors. No invented stage/timer events.

## Progress identity and parser

Each snapshot has an explicit ephemeral schema, complete frozen Build basis,
action/conversation IDs, origin client/durable turn IDs, turn attempt, selected
broker operation, acknowledged provider attempt, reservation fingerprint and
monotonically increasing operation-local sequence. The browser compares the exact
request capability/basis/conversation/client turn, then freezes the first full
operation/attempt identity and ignores stale, foreign, duplicate or reordered data.
It retires the observer on final response, page/conversation/navigation change or
unmount; nothing writes to a different page or newer request. Final normal response
validation remains in the existing caller. The payload is not an APP stored event.

A single-pass lexical decoder tracks root JSON keys, escapes, Unicode/surrogate
pairs and string state across arbitrary delta boundaries. It exposes only complete
decoded Markdown lines from the still-open replacement_markdown string; other
fields stay out. No full-buffer JSON reparse per token and no guessed row from a
chunk boundary. Hold partial lines/escapes until complete. Duplicate target fields
or malformed lexical output invalidate preview; GE and Buddy still validate the
complete object, including existing duplicate-field rejection.

Preserve exact final raw evidence through GE's exported public TextProvider seam:
a product-owned observer delegates to the existing guarded OpenAI provider, awaits
APP acknowledgment of TextCompleted.final_text, then yields that unchanged event
to GenerationClient for local conformance. This replaces the existing
on_attempt_completed evidence callback, not GE's conformance or lifecycle owner.
It never turns TextFailed into success, changes a terminal, or substitutes joined
deltas for final_text. Provider-declared failure exposes no invented final raw
body. Observer failure fails execution without retry; retain the original uncertain
APP state if acknowledgment could not commit. Delegate aclose and explicitly close
the inner async iterator on every exit, including outer cancellation/close. No
private SDK/GE fields, library callback extension, second provider or repair path.
Capture final normalized observation separately after GE returns its terminal.
Prove a provider final text different from earlier deltas is retained exactly,
including on schema rejection, and that failed evidence acknowledgment cannot
produce a ready proposal. Retain the jointly acknowledged producing attempt.

Use the existing canonical Markdown AST parser in shared Surface to recognize
complete GFM tables from completed lines, including escaped pipes. Render inert
React text/structure, never raw HTML, links, tools or code. Do not install another
Markdown grammar or stream a changed output schema. Only actual complete table
structure/rows trigger visible preview; at most one render per completed snapshot.
The captured SurfacePageProposal widget remains outside page JSON/undo. Restore
through the existing bridge and retire placement if the author edits its basis.
Do not lock ordinary editing/scrolling/Save. The growing preview has no editable
or Save/Keep controls. Failure marks it incomplete; a validated durable record is
required before existing live proposal editing/Save becomes available.

## Expected exclusive write lease

- pyproject.toml, uv.lock (exact GE pin only)
- apps/live_control_server/routes/agent.py (Build stream wrapper only)
- apps/live_control_server/services/build_construction_stream.py (new transport/sink/decoder)
- apps/live_control_server/services/build_document_proposal.py
- apps/live_control_server/services/build_jev_harness.py (exact stream request projection)
- apps/live-control-ui/src/api/liveApi.ts (Build stream opt-in only)
- apps/live-control-ui/src/api/buildConstructionStream.ts (new safe stream reader)
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx
- apps/live-control-ui/src/surface/SurfaceConstructionPreview.tsx (new shared rendering)
- apps/live-control-ui/src/buildSurface/BuildConstructionPreview.tsx (new bridge placement)
- apps/live-control-ui/src/surface/SurfacePageProposal.css (preview presentation only)
- owning tests: tests/test_build_construction_stream.py (new),
  tests/test_build_document_proposal.py, tests/test_build_proposal_shared_writer.py,
  tests/test_build_insertion_tool.py, tests/test_agent_build_jev_ordinary_harness.py,
  tests/test_agent_turn_route.py; adjacent owning fixture files only when explicitly
  named by PRIME after inspection (no blind broad test rewriting)
- apps/live-control-ui/src/api/buildConstructionStream.test.ts (new),
  apps/live-control-ui/src/surface/SurfaceConstructionPreview.test.tsx (new),
  apps/live-control-ui/src/buildSurface/BuildConstructionPreview.test.tsx (new),
  apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx,
  apps/live-control-ui/src/planSurface/components/BuildComposeProposal.test.tsx,
  apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx
  (PRIME adds mounted post-send session-retirement recovery witness; no contract change)
- this handoff, Docs/Roadmaps/ROADMAP-demo.md,
  Docs/Plans/HANDOFF-BUILD-draft-writer-status-domain.md (truthful PR1709 settlement)

## Verification and delivery

Before implementation: independently critique identity fences, disconnect lifetime,
malformed partial output, terminal/error envelopes and author draft preservation.
Then implement one bounded capability; extra durable/public contracts or migration
require a contract revision. No hidden fallback generation, new arbitrary limits,
provider/model defaults or routing-taxonomy change.

Prove decoder partitions including escaped quotes/backslashes/newlines, Unicode
pairs, nested other fields, duplicate fields and incomplete rows. Real installed
SDK/mock SSE + APP boundary proves one jointly authorized request, progress before
terminal, final structural/domain rejection, raw evidence and no duplicate action
on replay/retry. HTTP stream tests cover auth, one execution, errors, coalescing,
disconnect and retained durable completion. UI tests cover identity/sequence fences,
stream EOF/error recovery, navigation, safe table rendering and no page JSON edits.
Run required focused/full owning gates, exact cumulative-diff Bugbot, PRIME merge.

Protected API/UI delivery owns ports8000/5202, APP/native/frozen state, existing
runtime dependencies and drafts. Do not restart until live runtime ownership,
active-turn and retained-state checks pass; no extra operator restart permission
is required. Ordinary synthetic table then Edge/Bog Blossom dogfood must show rows
before terminal and final editable proposal, failure after rows, retry without
duplicate turn/insertion, reload recovery, page placement, scrolling and preserved
newer author draft. Measure first structure/row, final render/validation and
separate decision/read/writer timing with labeled host memory proxy. Technical
checks/deployment are not this rendered proof or full-goal completion.

PR1709 predecessor settlement: merged40b7f395, 54 tests/independent review, protected
API delivery and ordinary current-page follow-up9.083s/reload proof; revision12
and source hash unchanged. UI remains506162b0 until this slice is delivered. GE27
is merged and gated by353 provider-free tests, independent exact-head review and
Python3.11/3.13 CI. Exact GE3e085168 was adopted with API3ce378df.

PRIME owns runtime/artifact cleanup. Reuse checkout and existing dependencies.
The necessary locked-SDK verification environment under Projects/.codex/
guarded-schema-stream is retained for this adoption; settle it after checking
actual process/dependency references. Preserve private captured prompts locally.


## Current settlement

1719 approved020e10e89,109 backend/190 UI tests, merge/API3ce378df;1720 approved
b3cf552da,27 UI tests, merge656783705;1721 approvedde88ddb13,138 mounted tests,
merge/UI5829c6e8f. Protected adoptions preserved retained state; latest2610 APP rows,
27 frozen components,89 product files and native authority. API3ce378df remains
healthy. Synthetic direct edit/Save/reload and visible real Bog Blossom growth
passed. Recovery proposal-refresh proof is combined with the active successor
HANDOFF-MIND-shared-composer-reload-drafts.md, which owns the newly discovered
unsent-text persistence gap. No failure-after-rows/provider-failure or full-goal
acceptance claim. Operator speed assessment changes priority to writing continuity;
latency measurement is a regression guard. Preserve all remaining broad gates.

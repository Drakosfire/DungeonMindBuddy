# BUILD: Discuss continuation captures context without page placement

ACTIVE after independent design clearance. PRIME activates one serial slice from
origin/main d84b7336c195c3d75674e82ada173a44c539bb92 in the existing Buddy checkout,
branch codex/reviewed-discuss-read-context. #1764 remains parked. No other active
runtime implementation PR overlaps this lane. No new worktree or environment.

Observed boundary: ordinary synthetic Continue for a saved Discuss step called
bridge.capture against a plan NodeSelection, yielding the insertion-target error.
The saved request resumed after an explicit text caret. Discuss already has an
immutable selected task and a read-only draft snapshot. APP admits it without a
write capability; existing policy/selection records already allow a null capability
and answer-only operations. Do not invent a caret or offer unnecessary write access.

Carry the exact reviewed step kind from both existing plan hosts through the
in-memory Surface request queue. Refuse missing/inconsistent kind metadata and
include it in duplicate-request equality. Use context-only preparation for Discuss;
keep insertion preparation for insertion steps. The server still resolves the
reviewed dispatch and owns operation authority: a forged UI hint cannot authorize
an insertion without placement. Keep full working-draft, page, pointer and request
identity fences and preserve newer composer text. Preserve readback/retry and
source-citation authority. No new durable schema or compatibility path.

Expected exclusive writes after activation: this handoff;
Docs/Plans/HANDOFF-BUILD-reviewed-step-task-scope.md (settle completed predecessor);
apps/live-control-ui/src/buildSurface/BuildWorkPlanHost.tsx and its test;
apps/live-control-ui/src/agentInteraction/surfaceConversationRequests.ts and test;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx;
apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx;
tests/test_reviewed_action_binding.py. Existing BuildComposeProposal tests may be
extended if needed, without changing the capture/placement owner implementation.
No runtime backend changes are initially leased; return to stewardship if its
existing no-capability path fails the owning SDK/APP proof.

Prove no-placement Discuss with an actual plan NodeSelection/throwing insertion
capture, full snapshot and newer composer retained; correct host/queue kind and
identity; insertion still requires placement. Exercise the real SDK/APP with no
write capability, plain and selected Graph references, final scope validation,
inline questions, and insertion/no-capability rejection before provider send.
Inspect cumulative diff, independent exact-head Bugbot review, PRIME merge,
protected UI-only delivery and ordinary Continue without touching page text.

Separate follow-up: ProposedStep has only text/kind; workPlanCapture hardcodes
selected:true. The generated acknowledgment that step2 is deferred cannot be
represented by the current plan object. Add explicit selected/deferred proposal
state in a separately bounded contract slice; no text parsing or kind heuristic.
Mallow destination and full creative/operator acceptance remain open.

# BUILD: preserve proposed step selection through author review

ACTIVE. PRIME adopts the independently critiqued design at fetched main
6d772e2aab29e6c51364217457f715001a203bcf, existing Buddy checkout,
branch codex/plan-proposal-selection. Serial topology; #1764 remains parked.
No new executor, worktree, environment or work-plan storage version.

Observed failure: the author requested step2 deferred; Buddy acknowledged that
choice but ProposedStep has no selection field and both UI capture paths set all
rows selected:true. This slice makes that decision representable and preserves it.

New plan proposals require a strict selected boolean on each step. Freeze a new
pre-writer plan-output contract with the exact new nested schema digest; require
its new finite writer format, including connected-origin overlays. For V2 contracts the unique operation selection may be ordinary
BuildJevActionSelectionV1 or reviewed selection (RequestedWorkResolution is a
subclass); retained V1 validation keeps its original event domain. Nonimage
profiles with a write capability are not admitted by the current normal budget;
do not manufacture that runtime path for profile coverage. New calls may
not fall back to a historical plan schema or reprepare an old contract. Keep old
captured packets, schemas, completions and exact completed replay readable without
rewriting or adding fields to them. Existing saved author review selections win.
Retained historical proposal presentation may keep its existing initial checkbox
behavior; it must never be presented as newly captured provider selection.

Use versioned proposal/completion/event vocabulary. Extend agent.turn completion
and lifecycle SQL checks additively, preserving current branches; admit new rows
only with the new contract and exact nested plan/step keys and boolean type. The shared V3 draft completion wrapper requires connected-page and relationship
policies only for those corresponding object kinds; plans, questions and null
retain draft/related/collaboration checks. Prior SQL branches stay unchanged. No
work_plan payload rewrite or new work-plan migration: selected already exists in
that owner. Downgrade refuses retained new contract/completion. Drain the exact
old API and verify no active claims before migration; repair forward once new
schema or candidate reader is active. Preserve all retained rows except the schema
marker, native state, frozen inputs, product files and newer local drafts.

Carry true/false through real streamed complete rows, strict UI decoding, editable
page staging, Save/reload, placement retry/recovery and existing explicit Continue.
Partial or malformed rows remain inert observation. No inferred checkbox state
from prose, step kind, order or a keyword heuristic. Writer instructions honor
explicit defer/include choices and distinguish proposal selection from permission
to execute. Genuine questions remain in conversation. No automatic step execution.

Exclusive writes: this handoff and HANDOFF-BUILD-reviewed-discuss-read-context.md;
src/application_state/agent_conversation/{collaboration.py,relationship_review.py,
plan_objective.py,build_draft_answer.py,build_intentional_response.py,types.py,
source_writer_output.py,work_plan.py}; new migration
src/application_state/migrations/versions/20261026_0075_plan_proposal_selection.py;
apps/live_control_server/models/agent_turn.py (response union for new completion);
apps/live_control_server/services/{agent_turn_service.py,build_jev_writer.py,
build_jev_driver.py,build_jev_harness.py,build_plan_construction.py};
apps/live-control-ui/src/{api/types.ts,api/buildConstructionStream.ts,
shared/sourcePassageProtocol.ts,planSurface/components/WorldPlanAgentConversation.tsx,
surface/workPlans/workPlanCapture.ts,surface/workPlans/StagedWorkPlan.tsx,
surface/SurfacePlanConstructionPreview.tsx}; their owning tests and existing
plan-output SDK/APP/profile test fixtures. Return to stewardship before expanding.

Gates: strict missing/nonboolean selection rejection; actual SDK prepared schema
and APP final reconstruction; tampered completion/scope/format refusal; all admitted
plan writer families and citation/origin overlays; historical byte-stable replay;
real complete-row stream true/false and malformed/partial rows; UI staging and
saved-review precedence including recovery; additive migration/no-row-rewrite,
wrong contract and malformed selected SQL refusal, downgrade guard. Then exact
cumulative independent Bugbot review, PRIME merge, protected paired delivery and
ordinary explicit-defer dogfood through Save/reload/one selected continuation.

Mallow private replay permission remains pending. Current routing already has a
separate review_connected_page intent; do not replace its unresolved reproduction
with speculative routing edits or synthetic creative acceptance. Broader goal and
operator acceptance remain open.

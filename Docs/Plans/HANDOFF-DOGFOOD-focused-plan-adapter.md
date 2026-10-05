# DOGFOOD — focused Plan adapter exploration

Status: ACTIVE exploratory implementation under direct operator authorization, 2026-10-04. Not permanent adoption or merge authority.

Base: origin/main 938fa4ecb9ef83bb6e287a5299f5831ec738ced6.
Branch: codex/dogfood-focused-plan-adapter.
Checkout: /tmp/dmb-focused-plan-adapter.
Topology: parallel-independent exploratory UI; production unchanged. Potential future adoption overlaps DEMO's card projection and interaction chrome and must be coordinated.

Expected write lease: this handoff; apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx; components/WorldPlanCardProjection.tsx, FocusedPlanAdapter.ts, FocusedPlanPrototype.tsx, FocusedPlanPrototype.css; planSurface/FocusedPlanAdapter.test.ts; agentInteraction/AgentInteractionChrome.tsx. WorldPlanAgentConversation.tsx is included for opt-in presentation and draft typing. No provider, conversation service or database schema changes.

Runtime: existing prototype UI5203 (Vite, strict port) → unchanged Buddy API8000/DMS7860. Operator UI5202 stays available. Same real operator Plan persistence: ordinary Apply/Save can write real data; exploration does not mean a disposable backend. No actual Plan writes or provider calls performed during verification.

## Experiment

Opt in with prototype=focused and view=cards on the existing Plan URL. The adapter consumes Buddy's verified Playable projection and mounted Tiptap document, preserving identities and original blocks rather than copying a fixture. It presents one scene, an optional outline, authored reading lenses, nearby choice disclosures and Previous/Next. Scene/view URL parameters preserve navigation on refresh. Document remains the ordinary mounted editor.

The visible scene selects the existing exact Ask target automatically. The shared dragon launcher opens the conversation; separate scene chat buttons are removed. Lenses are presentation subdivisions, not new editable identities. Review, Apply, Save, revision validation and late-answer attribution remain owned by Buddy.

Conversation is a side pane beneath navigation. Its separator supports pointer dragging and keyboard Left/Right; the Plan width adjusts. On narrow viewports conversation uses an overlay. No synthetic history or inferred send-mode classifier is added.

Original paragraphs/lists/quotes, basic text marks, tables and graph atom labels/IDs are preserved in the experimental renderer. This is not a complete generic rich-content renderer. Native node dossier/Graph navigation still requires wiring the appropriate projection host; retaining the label and calling the existing chip runtime does not prove a working inspector. Unmarked introductory/global prose remains in Document. Only supported verified scenes are presented; malformed structure stays under existing blocked behavior.

## Verification and limits

27 focused adapter, card integration and World history tests passed. These include mounted draft → Cards → ordinary Save → fresh reopen using test mocks. Browser verification against actual Session29:19 scenes, scene flip/back, lens switching, outline collapse, original labels/lists/paragraphs, scene Ask attribution and conversation width420→444 via accessible separator. Read-only inspection, no real Save or provider Send.

Full typecheck on clean938fa4ec and this branch reports inherited ThreatPublicationPanel.tsx:553 Cannot find namespace JSX. No additional type errors remain in the prototype files.

Instructions and target metadata are collapsed in the opt-in presentation. Unavailable history no longer reserves blank transcript space. Draft typing works while authorization is unavailable; Send retains existing readiness guards. Outline buttons wrap to content height.

The established release launcher was restarted without interrupting prototype UI5203. UI5202/API8000/DMS7860 health checks passed. Authenticated World history returned200, unauthorized returned401 graph_auth_required. The operator must enter the existing private credential through Settings in this tab. Managed Graph projection separately returned409 managed_world_unverified; no Graph or binding mutation was performed.

Candidate adoption slice: focused Plan scene/lens presentation and shared conversation chrome, preserving existing review/apply/save and attribution contracts. This is a proposal, not formal adoption authority.

Refinement: prototype conversation owns vertical scrolling, with composer immediately after header in DOM order, ahead of settings/context/history. Browser overflow witness: client height560px, content1131px, overflow-y auto; lower refresh control reachable by keyboard. Existing authorization and send guards unchanged.

## Operator-authorized Context composer extension

The operator authorized Message only / Selected scene / Whole Plan with inspectable construction on 2026-10-04. Additional exclusive prototype write paths: apps/live-control-ui/src/api/liveApi.ts and types.ts; apps/live_control_server/models/agent_turn.py; routes/agent.py; services/agent_turn_service.py and agent_plan_context.py; src/application_state/agent_conversation/types.py; tests/test_agent_plan_context.py; apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx. Existing branch/base retained, serial within PR917. Default whole_plan preserves legacy fingerprints. Nondefault modes require graphless pinned Plan, never alter future Graph policy. Preview is authenticated and read-only, never claims a turn or calls provider. Preview covers constructed Plan message, not hidden runtime history/system/tool instructions. Context mode is submitted intent, exact revision unchanged. Current8k transport budget remains; oversized context fails before UI Send. Per-turn context receipt display is deferred: existing client and durable turn IDs do not have a verified UI correlation. Preview remains inspectable; no new durable correlation API or database migration. Proposals remain unchanged.

Context verification:12 targeted tests passed, including exact preview→runtime message equality for Message only and Selected scene, auth-first preview, no turn/provider preview dispatch, bounded extraction, full Plan over-budget guard and legacy/default fingerprint parity with/without card focus. Existing service coverage passed alongside context tests;17 conversation UI tests passed, including stale-preview invalidation and over-budget Send gating. Full route suite is not counted as verified: both this branch and exact base938fa4ec pass16 tests before disposable PostgreSQL setup fails with psycopg OperationalError. Both bounded full runs also stall at test_full_application_http_route_and_legacy_route_cardinality, line1675, with identical asyncio/AnyIO waiting stacks and exit124 after40s. These are reproduced base environment limitations. Live authenticated read-only preview was verified separately. Typecheck retains inherited ThreatPublicationPanel JSX error.

Operator refinement 2026-10-04: Edit must start closed. Focused World Plan uses the existing overlay Edit host (closed by default) rather than the always-open dock. Chat remains independently launched and scrollable; the message field precedes context controls and explanatory context copy is collapsed. Browser verified close/reopen Buddy leaves Edit closed, the left blank dock is gone, and the full card remains visible alongside chat. Screenshot: /tmp/focused-agent-layout-fixed.png. No authentication or provider behavior changed.

## Operator override — production priority, 2026-10-04

The operator explicitly directed: “Prototype should not block DEMO period.” PRIME withdraws PR917 exclusive reservation over production Buddy UI/API/model/service/conversation paths. All earlier expected leases describe this isolated experiment only; they do not reserve production files or gate DEMO implementation/adoption. DEMO may work on fresh main in its own checkout immediately. DOGFOOD owns later prototype reconciliation and must never request DEMO wait for prototype settlement.

Runtime priority for approved5202/API8000/DMS7860 transfers to DEMO. Independent5203 may remain only without shared API/process ownership collision; suspend incompatible prototype portions rather than blocking DEMO. Whole-launcher transfer must preserve drafts and an exact rollback; never kill API alone. Do not stop services before a concrete transfer is ready. No merge/native adoption authority follows. Existing Sheep PR887 slice is separate and noncolliding.

Observed host process ownership before transfer: independent5203 Vite PID1866226 uses this checkout. UI5202 Vite PID1977394 also uses this checkout; API8000 PID1977475 executable uses `/tmp/dmb-dogfood-release-938fa4ec/.venv`, while host `/proc` inspection confirms the API working directory is `/tmp/dmb-focused-plan-adapter` and the shared `bash ./run` launcher PID1977297 also runs from that checkout. The virtual-environment executable path does not establish the loaded source revision. DMS child PID1977348 runs DungeonMindServer dev_server.py. These are observational facts, not durable live identifiers or evidence of transfer completion. Exact rollback checkout `/tmp/dmb-dogfood-release-938fa4ec`; previous prototype head `9128685d28709b70ada92334e6b4e305205af71b`. No server was stopped and no browser was refreshed by this authority update.

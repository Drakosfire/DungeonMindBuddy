# DOGFOOD — focused Plan adapter exploration

Status: ACTIVE exploratory implementation under direct operator authorization, 2026-10-04. Not permanent adoption or merge authority.

Base: origin/main 938fa4ecb9ef83bb6e287a5299f5831ec738ced6.
Branch: codex/dogfood-focused-plan-adapter.
Checkout: /tmp/dmb-focused-plan-adapter.
Topology: parallel-independent exploratory UI; production unchanged. Potential future adoption overlaps DEMO's card projection and interaction chrome and must be coordinated.

Expected write lease: this handoff; apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx; components/WorldPlanCardProjection.tsx, FocusedPlanAdapter.ts, FocusedPlanPrototype.tsx, FocusedPlanPrototype.css; planSurface/FocusedPlanAdapter.test.ts; agentInteraction/AgentInteractionChrome.tsx. No provider, conversation service, database schema or WorldPlanAgentConversation changes.

Runtime: existing prototype UI5203 (Vite, strict port) → unchanged Buddy API8000/DMS7860. Operator UI5202 stays available. Same real operator Plan persistence: ordinary Apply/Save can write real data; exploration does not mean a disposable backend. No actual Plan writes or provider calls performed during verification.

## Experiment

Opt in with prototype=focused and view=cards on the existing Plan URL. The adapter consumes Buddy's verified Playable projection and mounted Tiptap document, preserving identities and original blocks rather than copying a fixture. It presents one scene, an optional outline, authored reading lenses, nearby choice disclosures and Previous/Next. Scene/view URL parameters preserve navigation on refresh. Document remains the ordinary mounted editor.

Discuss scene / Revise scene use existing exact scene targets and open Buddy's real conversation pane. Lenses are presentation subdivisions, not new editable identities. Review, Apply, Save, revision validation and late-answer attribution remain owned by Buddy.

Conversation is a side pane beneath navigation. Its separator supports pointer dragging and keyboard Left/Right; the Plan width adjusts. On narrow viewports conversation uses an overlay. No synthetic history or inferred send-mode classifier is added.

Original paragraphs/lists/quotes, basic text marks, tables and graph atom labels/IDs are preserved in the experimental renderer. This is not a complete generic rich-content renderer. Native node dossier/Graph navigation still requires wiring the appropriate projection host; retaining the label and calling the existing chip runtime does not prove a working inspector. Unmarked introductory/global prose remains in Document. Only supported verified scenes are presented; malformed structure stays under existing blocked behavior.

## Verification and limits

25 focused adapter + existing card model/integration tests passed. These include mounted draft → Cards → ordinary Save → fresh reopen using test mocks. Browser verification against actual Session29:19 scenes, scene flip/back, lens switching, outline collapse, original labels/lists/paragraphs, scene Ask attribution and conversation width420→444 via accessible separator. Read-only inspection, no real Save or provider Send.

Full typecheck on clean938fa4ec and this branch reports inherited ThreatPublicationPanel.tsx:553 Cannot find namespace JSX. No additional type errors remain in the prototype files.

Actual conversation remains blocked by local Graph auth environment until coordinated runtime restart. SERVER configured private environment, but existing ./run supervises all children and tears down UI/DMS if API exits. Restart remains pending preservation of operator drafts and separate lifecycle clearance. Exploration does not remove this launch blocker.

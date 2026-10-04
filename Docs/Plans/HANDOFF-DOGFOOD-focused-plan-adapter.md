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

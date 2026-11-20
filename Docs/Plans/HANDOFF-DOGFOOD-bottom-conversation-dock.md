# DOGFOOD — reusable bottom conversation dock

Status: ACTIVE under the operator's direct UX/design authority and PRIME's explicit path/fixture-port clearance. This is one reusable presentation primitive; production adoption is a separate successor.

## Outcome and invariant

The operator wants document reading above a minimal bottom conversation, with resizing, collapsed writing access, inspectable context and reusable styling. The current Plan pane prioritizes configuration and target metadata over conversation. A layout primitive should give callers separate reader, messages, composer and optional context slots without owning provider or campaign behavior.

Reader and composer remain mounted through collapse; draft inputs survive. Message scroll position is restored. Context details scroll within a bounded region rather than displacing the full transcript. The reader retains an allocation when conversation height changes. Long human-readable context labels fit the header. Pointer/keyboard resizing is bounded and cleans up on cancellation/lost capture. Paint is local through CSS variables, not global token or application selector edits.

Failure cases: child slots with oversized forms, small/keyboard-reduced containers, wrapped header actions, long labels, selected scope lost during hiding, native scroll settling, pointer capture loss and differently colored themes. A unit test cannot prove rendered clipping. Height-owning parent and compact composer are caller contracts; consumer adapters must verify actual document/context/capability semantics.

## Lane and exclusive expected write set

- Base: fetched `origin/main` at `a869c27a7b4b3d6e77048bbb80a55984d709e705` when the branch was created; record exact head in the PR packet.
- Branch: `codex/dogfood-bottom-conversation-dock`.
- Checkout: `/home/drakosfire/.codex/worktrees/dogfood-ux-design-kit/DungeonMindBuddy`.
- NEW `apps/live-control-ui/src/ui/ConversationDock.tsx`.
- NEW `apps/live-control-ui/src/ui/ConversationDock.css`.
- NEW `apps/live-control-ui/src/ui/ConversationDock.test.tsx`.
- NEW `apps/live-control-ui/src/ui/ConversationDock.stories.tsx`.
- This handoff, `Docs/Plans/HANDOFF-DOGFOOD-bottom-conversation-dock.md`.
- NEW owned screenshot evidence only: `Docs/Plans/evidence/dogfood-conversation-dock/**`.

No edits to #979's WorldPlanAgentConversation/controller tests, #970's Plan/reader/reference paths, global CSS, tokens, registries, API, schema, runtime or campaign files. The dirty original DOGFOOD recap checkout remains untouched. The saved six-page native design collection is a reference outside this code lease, not production behavior.

Topology: serial. One implementation PR for this primitive. An adoption successor is not activated here. Independent review is required for this DOGFOOD-authored code; author tests/screens are not independent acceptance. No merge authority is granted to DOGFOOD by this handoff.

## Runtime and verification

PRIME cleared the existing prototype port 5203 if free. Host socket and HTTP probes found no owner; do not replace a listener. Use isolated Ladle fixtures only, with no provider/Graph/API/data/publication actions. Production 5202/8000/7860 and their files/processes are out of scope. Stop the owned fixture server after evidence capture.

Owning checks: slot/draft identity through collapse, context state, message scroll restoration, pointer/keyboard bounds/cancellation, container resize and absent optional context. Rendered checks at1280×720 and390×844: reader allocation, full composer controls, meaningful messages with context closed/open, selected scope retention, collapse/reopen and resizing. Review exact cumulative diff, commit intended paths, push, open the PR and send exact head/evidence/limitations to PRIME.

## Reference basis and limits

Mobbin's Sana bottom composer: https://mobbin.com/screens/9098947d-d197-4f05-a54d-de310aa638be . Copilot document/conversation: https://mobbin.com/screens/8b77f912-1c9c-4efc-813c-aad036488111 . They inform hierarchy, not executable resize or safety proof. DungeonMind's public character/statblock/navigation surfaces and the operator-accepted DOGFOOD card prototype provide visual-language references. Reference screenshots remain in the task-owned collection; no third-party images are published in this primitive PR.

The primitive is not yet mounted in the product. It does not establish Graph-context readiness, durable conversation, Run context, save receipts or complete prototype fidelity. Operator-led design iteration continues alongside independent source review.

## Author verification packet

- Ten owning interaction tests pass, including caller-labelled reading landmarks, mounted draft identity, context scope, message scroll restoration, pointer ownership/cancel, keyboard bounds, container resize/observer cleanup and unavailable-context transitions.
- The five isolated Ladle states build successfully: Compact, Expanded, Paper, Failed turn and Touch target. No application/provider decorators are loaded; the author server uses only this story glob on5203.
- Full UI typecheck remains red at `ThreatPublicationPanel.tsx:553` (`TS2503: Cannot find namespace JSX`). Exact-base source with the same dependencies reproduces the same error. An initially incomplete baseline archive also missed a fixture JSON; including that base fixture removed the setup error. No new dock type errors were reported.
- At1280×720 and390×844, full44px composer/31px Send visible. After the touch-target correction, normal expanded messages195.83px/context-open158.23px; touch treatment163.83px/context-open126.23px. Native pointer opening leaves outer page at0; semantic helper actions that center fields can move the oversized Ladle wrapper, so those offsets are not counted as component behavior. Initial host allocation clipped the composer and was fixed before final screenshots.
- Actual message scroll148px desktop/246px mobile survives collapse/reopen. Draft and selected scope retain identity. Keyboard and pointer height340→364→394px leave composer reachable and reader allocated.
- Paint tested in dark and paper variants. The failed-turn fixture remains explicitly failed when collapsed; technical/recovery details fold without deletion or replay. These are design states, not a live Graph answer.
- Owned before/after evidence is included in the declared evidence directory. Full author measurements are task-local `dogfood-2026-10-06/conversation-dock-author-metrics.json`. Ordinary virtual viewport/pointer/keyboard checks do not prove hardware touch, IME on every platform, streaming behavior or arbitrary oversized caller slots.

Caller requirements: supply compact composer and header actions, preserve captured source attribution and real outcome in messages/collapsedPreview, and own conversation namespaces/drafts/provider/persistence. A consumer adapter must independently verify its actual content and authority; putting an entire legacy control form into the composer slot does not gain a readability pass.

## Incremental independent-review response

Independent review held head5353e04 on the10.4px resize target. The correction guarantees at least24px normally and44px under coarse-pointer media, while retaining a2.875px visible grip. Both hit and header-control sizes are paintable variables with pixel minima that survive smaller root-font scaling. The Touch target fixture applies the same44px treatment explicitly for rendered inspection; virtual viewport tests reported coarse=false, so this is not a claim of real hardware touch/media emulation. Pointer drags starting in the surrounding hit area resize340→368px at both treatments, with full composer controls. Refreshed owned screenshots/metrics replace changed-geometry after evidence; independent incremental review is still required.

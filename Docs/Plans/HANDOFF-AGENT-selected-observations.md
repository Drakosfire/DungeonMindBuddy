# AGENT — Select reviewed observations before anchor admission

Status ACTIVE, PRIME solo; base `b285e4fd1ab61139b66b461730ee7b058a909994`.
Lane `/tmp/prime-recap-mention-boundaries`, branch `codex/agent-selected-observations`.
Topology serial; source-observation producer #1232 is merged. DOGFOOD UI work is
separate. ARCHITECTURE owns independent exact-head review.

Outcome: a governed Build Agent can follow a reviewed search pointer by requesting
its assertion ID with the subject object. Select observations at the frozen native
revision before the existing total anchor bound is applied. Preserve every selected
observation's required refs, exact source pins, ordinary claim/source validation,
canonical object data and truthful partial coverage. No broad limit increase, dropped
refs, historical assertion rewriting or invented species identities.

Expected write lease:
- apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
- apps/live_control_server/services/agent_turn_service.py
- apps/live_control_server/services/hermes_graph_interaction_tools.py
- apps/live_control_server/services/agent_graph_policy.py
- src/graph_memory/interaction/expansion_executor.py
- tests/test_agent_selected_observations.py (new)
- tests/test_agent_build_governed_graph.py (owning parent broker propagation proof)
- Docs/Plans/HANDOFF-AGENT-selected-observations.md
- Docs/Plans/HANDOFF-BUILD-source-observations.md (completed predecessor sync)

The optional model-visible observationIds selector is object-only, distinct nonblank
IDs. It is supported only by the governed Build parent broker; other execution paths
reject it explicitly. It is not a source handle, World selector or revision override.
Missing/wrong-subject IDs fail closed at the native read. Search pointers remain
non-claim discovery records. Selecting some observations reports unselected coverage;
an oversized selected record remains omitted with the existing bound diagnostic.

Verify schema/tool wiring, parent propagation, pinned native selection before bounds,
complete supporting anchors and pins, unknown/wrong-subject/duplicate/blank/other-
operation rejection, unchanged unfiltered behavior, and result continuation argument
integrity. Focused tests must exercise actual native publication/readback where feasible.
No provider, retained Graph/APP/source writes, serving changes or migrations authorized
by this implementation lease. Unique disposable tests only. Actual fresh Mirathorn
publication, ordinary live Agent and operator acceptance remain later gates.

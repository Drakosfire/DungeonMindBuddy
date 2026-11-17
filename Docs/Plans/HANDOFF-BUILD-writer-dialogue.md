# BUILD writer conversation continuity

ACTIVE. Authorized by the brainstorming goal and its requirement to carry forward decisions and source references.

Stacked on PR #3855, exact parent 025346dfa478e18e3a90b8653050646d7ca62fcb. Branch codex/build-writer-dialogue uses the existing aw-conversation-drafts checkout. Merge #3855 first, then this slice. The predecessor continues to own only manual-rule normalization.

Write set consists of apps/live_control_server/services/build_jev_harness.py, apps/live_control_server/services/plan_jev_writer.py, tests/test_plan_jev_response_assembly.py, and this handoff. No primary database or serving runtime writes. Local rehearsal uses the existing isolated evaluator and loopback mechanics owner, with artifacts retained on Projects.

The Build controller receives frozen ordinary dialogue, but the shared native writer omitted it. Pass that same dialogue to the writer as ordinary user and assistant messages before current task and evidence frames. Prior dialogue supplies user intent and decisions; existing source citation and publication checks remain authoritative.

Verify the final SDK request contains the actual prior user premises and selected decisions, preserves ordering and current evidence, and retains native structured output. Run owning writer and assembly contracts and the ordinary isolated rehearsal. Record the candidate outcome before any approved save. Gold remains local. Review and deliver this bounded change independently.

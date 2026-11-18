# Working with Buddy Agent context and runtimes

This is a navigation guide for contributors. The linked decisions, policy and
code own their respective contracts. Re-anchor on current `main` and the
applicable handoff before changing a boundary; source on `main` does not by
itself establish what is deployed.

## Follow a turn

1. Start with Buddy's [Agent runtime port](../../apps/live_control_server/services/agent_runtime.py),
   which defines the invocation, capability policy, runtime descriptor and result.
2. For context and scope, read the [context compilation decision](../Design/DECISION-agent-context-compilation.md)
   and [assembler](../../apps/live_control_server/services/agent_context_assembler.py).
   The [turn service](../../apps/live_control_server/services/agent_turn_service.py)
   calls the assembler and selects an execution path.
3. Selection depends on the turn: an injected runtime or factory can take
   precedence; Build, Plan and Play have conditional Jev paths; Hermes is a
   fallback. Read the current selection code and its tests for the surface being
   changed instead of assuming one universal runtime.
4. [World architecture](../Design/ARCHITECTURE-campaign-supergraph.md) describes
   the ownership boundary: Buddy owns product interaction and context policy;
   DungeonMind owns durable World identity, evidence and governed publication;
   WorldKeeper coordinates supported World changes. The
   [source-to-World contract](../Design/DESIGN-source-to-world-authoring-interaction-contract.md)
   distinguishes the accepted design from bounded implemented paths.
5. Before changing model-visible data, follow the prompt-context boundary in
   [AGENTS.md](../../AGENTS.md#model-prompt-context-boundary). Audit the final
   serialized request and host-side checks at the affected boundary.

## Find the owning tests

- [Runtime contract tests](../../tests/test_agent_runtime.py) cover the port and
  descriptor behavior, including an injected non-Hermes runtime.
- [Context assembler tests](../../tests/test_agent_context_assembler.py) cover
  scope and assembly. The conversation-only case checks that no World scope or
  retrieval session is attached and that the trace summary omits input and
  history content.
- [Hermes adapter tests](../../tests/test_hermes_agent_runtime.py) and
  [Pydantic AI adapter tests](../../tests/test_pydantic_ai_agent_runtime.py)
  cover adapter-specific behavior.

Choose tests for the invariant and surface actually changed; a filename alone
is not evidence that a path is covered. The repository's
[review and verification standard](../../AGENTS.md#review-and-verification)
applies in addition to focused tests.

# Retire classic Threat hydration in Hermes

Active serial slice on Buddy main 4e22cd3f9487b84f449d84e673cc8fb257fedb3c.
MIND owns delivery with operator authorization for implementation, review
and merge. PR #4251 is the merged predecessor.

Hermes and PydanticAI inject classic graph coordinates for this tool.
The fresh native turn does not supply it with an authenticated managed
binding. Keep the legacy tool request and response vocabulary available
for existing callers, but return explicit unavailability without graph or
mechanics I/O. Preserve trusted argument injection and distinct mounted
managed hydration and direct saved mechanics reads.

Scope: hermes_graph_interaction_tools.py and existing owning tests in
test_pydantic_ai_agent_runtime.py and test_hermes_dungeonbuddy_plugin.py.
No relevant open overlap was found. Verify deterministic typed refusal,
injection ownership, zero hydration dispatch and unchanged adjacent tool
contracts using synthetic tests. Independently review before merge.

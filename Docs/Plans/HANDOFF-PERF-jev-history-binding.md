# PERF · Validate retained native context once during turn reconstruction

ACTIVE under the hosted Build Send-to-Jev optimization goal. Serial after #4164.
Base e25edf9017aeb6716eb84c1f97d966cfc2307378, branch codex/jev-history-binding.
The isolated Projects checkout owns this brief and the native_completion.py
and native_execution.py files under src/application_state/agent_conversation.

The retained hosted profile recorded two context-binding validations per historical
turn. Reuse the binding that the structural join already checked. The standalone
completion validator must still validate its independent inputs. Keep completion,
citation, producer, and replay checks in force. The Plan append owner validates
its exclusively owned prospective execution before invoking the structural join.

Verify the exact diff, the local query-and-answer contract against a disposable
database, and independent review. Measure opening and continued turns after
deployment under the existing hosted goal. No schema or primary content edits.

# RETRIEVAL: reuse the frozen query catalog during checkpoint validation

Status: ACTIVE for the user-authorized native Plan checkpoint goal. Serial Buddy
slice on codex/plan-checkpoint-record-catalog from 2894eb763a3330bdb777630be4844cbd47770a8b.
Core remains pinned to 855f23bd8b20c3b91c27d0d065c3a3cfb0fef917.
No unmerged dependency. Exclusive expected paths are this handoff,
src/application_state/agent_conversation/native_record_execution.py and
tests/test_native_object_retrieval.py.

Build one lazy object catalog per record-validation invocation. Every historical
selection, grant, observation and subsequent provider still crosses the same
predicates. No catalog survives its invocation. Leave write transactions and
claim, recovery, source integrity and checkpoint ordering unchanged. Verify the
owner's positive and negative cases, build count, existing checkpoint durability
contracts, and frozen 15-question evidence and citations. Candidate timing must
be labelled separately from offline validation. Use disposable databases only,
no writer, and reuse the retained baseline without rerunning it.

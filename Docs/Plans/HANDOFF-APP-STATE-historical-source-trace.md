# APP-STATE: historical source trace references

Status: COMPLETED; #1125 merged accepted head `190bed5402538360602e2950ac78999fb1756928` as `cc0d95c6ba7ba186575675b7233a080be1a263b4`. Base `origin/main@5d11ba51e583d230b8a7023d83fd9dfa6ce8d536`; branch `codex/app-state-historical-source-trace`; isolated checkout `/tmp/app-state-conversation-owner`. One implementation PR, parallel-independent of DOGFOOD #1120's producer/UI lane. Existing #1122 is merged at `6f54b152c506bc8cd356ad3e4cdb66a2c46babac`; accepted storage head `8aaa27d37b72d0833662e9510bbaaaa125d4e4ef`.

## Contract

Restored context may contain exact source bytes captured in an earlier turn. The before snapshot must distinguish this historical memory from current-turn source reads and route handles after compaction.

- Add optional `historical_source_reads` to source model-context material. Each nested `dmb_trace_historical_source_ref_v1` identifies original World/conversation/turn/attempt/trace/source-read-event/read ID/content SHA. Current `source_read_event_id` + `source_reads` and historical references are mutually exclusive; neither carries inline source text. Empty historical fields are omitted during serialization, preserving old material payloads and size accounting.
- At APP's existing fenced append boundary, resolve every historical reference to its exact stored passage in the same World/conversation and a strictly earlier turn sequence. Match the whole trace identity, event, read ID, digest, and any supplied route scope. Store the reference without copying passages or adding any current Graph execution event, citation/read authority, or provider operation.
- The producer computes the digest from the actual historical bytes being observed and supplies it in the reference. APP verifies that digest against the captured passage. When the original provenance tuple is unavailable, use `mark_context_trace_incomplete(..., failure_code="historical_source_unavailable")`; do not invent a source reference or put unverifiable source prose in the trace.
- An unverified reference causes explicit `historical_source_unavailable` capture status and preserves prior observations without recording the invalid snapshot. A prior exact passage can be used as provenance even if its enclosing trace is incomplete: exact per-passage capture is the required proof.
- This failure is observational: APP does not rewrite, suppress, or redispatch already-existing restored runtime history. DOGFOOD decides how to represent or safely omit historical bytes at its consumer boundary. A **new read** with failed passage capture remains different: its source bytes must be withheld before new model inclusion, the trace marked incomplete, and the same validated receipt retried without passage. Neither optional failure changes core turn authority or starts another Ask.
- Reuse the 1 MiB cap, reserved marker/terminal capacity, current-attempt claim fences, trace-only revision behavior, terminal atomic closure, and all-attempt history. No migration, generic history adapter, prompt/system text, hidden reasoning, live DB, runtime, or provider changes.

## Write lease and proof

- `src/application_state/agent_conversation/context_trace.py`
- `src/application_state/agent_conversation/context_trace_store.py` (existing repository/service boundary)
- `tests/application_state/test_agent_conversation_historical_trace_postgres.py`
- `tests/test_agent_context_trace_types.py`
- this handoff and predecessor status settlement

Inspect cumulative base→head diff. Prove exact historical readback without copied text or current read authority using real disposable PostgreSQL; reject wrong ownership, turn order, attempt, trace, event, read ID/digest, and route pins with explicit incomplete status and unchanged core turn. Reuse focused cap/current-source/attempt-fence cases; no unchanged broad suites. Use owned pgvector PostgreSQL with 512 MiB tmpfs, random loopback port, env-only password, synthetic fixtures, and unconditional teardown.

Report exact base/head/PR and evidence ONLY to PRIME. The previous outbound DOGFOOD message was rejected by automatic approval review; PRIME owns consumer coordination. Source omission/no-redispatch remains DOGFOOD's integration gate. No independent shared migration is authorized.

Predecessor finding/repair proof remains in #1122 and the local exact packet `/tmp/arch_trace_1122_original.py`; terminal-cap/fabricated-source regressions are checked in under `tests/application_state/test_agent_conversation_context_trace_postgres.py`.

Focused proof: 14 new real-PG historical cases, 6 reused real-PG cap/current-source cases, and 4 type cases passed using the owned 512 MiB tmpfs runner `/tmp/app_historical_trace_runner.py`. Ruff and cumulative diff whitespace check passed. This is storage-boundary evidence; DOGFOOD's consumer integration remains separately owned.

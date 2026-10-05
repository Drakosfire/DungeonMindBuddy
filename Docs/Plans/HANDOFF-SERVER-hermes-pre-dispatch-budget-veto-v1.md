# HANDOFF — SERVER: Hermes pre-dispatch budget veto v1

**Status:** ACTIVE — exact upstream, patch, and generated-tree evidence will be recorded in this handoff before PR readiness. No provider call, private corpus transmission, live rollout, upstream contact, or public fork is authorized.

**Owner:** DungeonMindBuddy SERVER. PRIME owns exact-head independent review and adoption approval.

**Base:** Buddy `main@e671784dc53e698a33a5125f08d76953faa34a19`.

**Topology:** serial prerequisite before the separate Plan World Graph context integration. This PR must be independently reviewed at exact head before product/runtime adoption. APP-STATE receipt remains the precise later integration dependency.

## Mission

Deliver a typed, terminal, fail-closed pre-dispatch request-budget veto at Hermes' final provider boundary, using a narrowly patched, reproducibly prepared Hermes dependency. The guard must evaluate the resolved provider/model/API mode and the final provider request after request middleware and immediately before SDK dispatch. Unknown request types, mode, model accounting, or unsupported serialization fail closed. A veto cannot be swallowed, retried, rerouted to a fallback, converted to streaming/non-streaming alternate execution, or followed by an SDK inference/tool call.

Keep Hermes' generic observational hooks fail-open and preserve normal provider failure/retry behavior. Preserve accepted-turn durable failure/replay lifecycle; this slice does not change receipt persistence or product failure projection unless existing error handling cannot preserve terminal-veto truth. The 8,000-character public question bound and the assembled full-Plan context budget are separate controls. Do not change the public question limit or add the full-Plan context guard here.

## Pinned upstream and patch distribution

- Upstream repository: `https://github.com/NousResearch/hermes-agent.git`.
- Exact source commit: `861d69c7bba8d2ea6a1cd170e989c901c74d32d1` (Hermes 0.18.2).
- Checked-in patch: `patches/hermes-agent/0001-pre-dispatch-budget-veto.patch`.
- Preparation script: `scripts/prepare_patched_hermes.py`.
- Generated local source is ignored under `out/hermes-agent`; a fresh checkout must prepare it explicitly before `uv sync --locked`. The script must verify upstream HEAD, clean source, patch SHA-256, and resulting Git tree identity; it must fail clearly if the source cannot be prepared. It must never patch site-packages or use a mutable/unpinned remote branch.
- Before PR readiness, record exact patch SHA-256, generated source tree SHA, install/lock source evidence, and the isolated fresh-clone prepare + `uv sync --locked` result below. If the pinned patch cannot be installed reproducibly through the repository's supported setup, stop and return the concrete packaging decision to PRIME.

## Exact write allowlist

- `Docs/Plans/HANDOFF-SERVER-hermes-pre-dispatch-budget-veto-v1.md` — this lease and exact evidence.
- `patches/hermes-agent/0001-pre-dispatch-budget-veto.patch` — the narrow patch against the exact upstream source.
- `scripts/prepare_patched_hermes.py` — verify/prepare ignored source reproducibly; no package installation side effect.
- `pyproject.toml`, `uv.lock` — make standard locked installation consume the prepared local patched distribution, with a clear missing-preparation error.
- `README.md` — only the actual setup commands needed for prepare followed by `uv sync --locked`.
- `apps/live_control_server/services/hermes_graph_agent_contract.py` — strict bounded request-budget IPC policy if needed by the guard.
- `apps/live_control_server/services/hermes_graph_agent.py` — bind the turn budget policy to the Hermes agent; map typed terminal veto only if the existing result path cannot already preserve it.
- `tests/test_hermes_graph_agent.py`.
- `tests/test_hermes_graph_agent_contract.py`.
- `tests/test_patched_hermes_dependency.py`.
- `tests/hermes_patch/test_pre_dispatch_budget_veto.py` — isolated owning-boundary tests against the patched pinned Hermes source.

`apps/live_control_server/services/agent_turn_service.py` and `tests/test_agent_turn_service.py` are conditionally reserved only for narrow typed veto translation, and remain read-only until APP-STATE confirms path coordination. Reuse current failure handling if sufficient. No other path is authorized. If inspected behavior requires any additional path, stop and amend this lease before editing it.

## Contract and safety requirements

1. The budget view is derived from the actual resolved provider, model and API mode and the final request after all request middleware/preflight shaping. It distinguishes input upper bound, output reserve, model input/context cap, estimator identity/version, and canonical payload digest. Do not label byte accounting as exact token accounting.
2. Use only a sound conservative full-input/output bound for an explicitly supported serializer/mode. Unknown values, schemas, mode, model capability, post-guard transformations, or accounting fail closed before SDK invocation. Synthetic fixtures must prove the serializer assumptions and bound; no remote input-token count or private data transmission is authorized.
3. Enforce at the last common point before provider SDK invocation and cover streaming and non-streaming paths. Test that request mutation after earlier middleware is reflected in the view.
4. The veto is a typed terminal control outcome, not an ordinary provider exception. Prove it bypasses generic observer exception swallowing, request retry logic, malformed-response fallback, configured provider fallback, streaming fallback, and any execution middleware retry/fallback. After veto, SDK inference call count and Hermes tool-call count are zero.
5. Existing observational hooks remain fail-open. Normal allowed requests and ordinary provider errors retain existing behavior.
6. Durable turn admission/replay behavior remains unchanged. If terminal veto requires changes to `agent_turn_service.py` or its tests, do not edit until APP-STATE path coordination is acknowledged; then amend this handoff's allowlist with the exact narrow change.
7. Dependency installation is explicit and reproducible: fresh clone preparation plus `uv sync --locked` installs the patched distribution; direct `uv sync --locked` without preparation fails with an actionable message. Verify subprocess-host/import behavior sees the patched code, not an unpatched cached or global distribution.

## Required evidence

- Patch applies cleanly to exactly the pinned upstream commit; patch digest and generated tree hash recorded above.
- Fresh disposable clone: prepare script succeeds, verification reports exact source/patch/tree identity, and `uv sync --locked` installs patched Hermes. A second preparation is idempotent. Missing or drifted output fails safely and clearly. Subprocess host imports the patched distribution.
- Hermes boundary tests cover allow, over-budget veto with zero mocked SDK calls, final payload after middleware, malformed/unknown mode and budget fields fail closed, and observational-hook exceptions remain fail-open.
- Exercise all retry/fallback/streaming modes from synthetic fixtures. Veto occurs before any SDK call and remains terminal even if retries, fallbacks, and streaming are configured. No tools dispatch.
- Buddy focused tests for request contract and adapter; relevant Ruff/type/full test gates from current workflow. No live provider, remote count endpoint, real Graph, database, private corpus, or operator service.
- Inspect exact cumulative base→head diff; only allowlisted paths; no site-packages edits, vendored wholesale source dump, unrelated lock churn, or changes to public question bounds/full-Plan guard.
- PRIME obtains independent exact-head review before any product/runtime adoption. This PR itself does not authorize rollout or merge.

## Evidence to fill before PR readiness

- **Base:** `e671784dc53e698a33a5125f08d76953faa34a19`
- **Implementation head:** pending
- **Upstream source SHA:** `861d69c7bba8d2ea6a1cd170e989c901c74d32d1`
- **Patch SHA-256:** pending
- **Prepared source tree SHA:** pending
- **Install/lock source:** pending
- **Tests and gates:** pending
- **Deviation / remaining risk:** pending
- **Terminal-veto acceptance:** pending

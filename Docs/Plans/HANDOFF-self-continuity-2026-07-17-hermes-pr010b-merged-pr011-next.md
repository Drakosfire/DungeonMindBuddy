# Self-continuity handoff — Hermes PR010B merged, PR011 next

**Date:** 2026-07-17
**Written by:** outgoing session, for a fresh agent with no chat history
**Scope:** Hermes graph-agent workstream (Campaign Supergraph Phase 7 → 8)

Read this file first. It replaces the chat history you don't have. Then read
the three canonical sources it points to before touching code.

## 0. One-paragraph state

`PR010B` (Hermes graph-retrieval dogfood, Rungs 1–7) is **DONE**. The branch
`agent/pr010b5-plan-hermes-thread-continuity` merged into `main` as
**`129a4c40`** (GitHub PR **#356**) on 2026-07-17. `PR011` (Agent Context +
governed tool runtime) is now **READY** and is the next infrastructure slice.
No code work is currently in flight on this workstream; the last thing this
session did was an atomic doc-sync to make the tracker/roadmap/reanchor docs
match the merge (they had said "not yet merged" while three extra
critique-hardening commits landed on the branch after the docs were last
written).

## 1. Verify this before doing anything else

```bash
git fetch origin main
git rev-parse HEAD          # should equal:
git rev-parse origin/main   # 129a4c40137d4a4b2ec483f28825dd53981cdcda (or later)
```

If `HEAD` is **behind** that hash, someone hasn't pulled — pull `main` first.
If `HEAD` is **ahead** with unfamiliar commits, someone did more work after
this handoff — read `git log origin/main..main` before trusting this
document's "current state" claims (temporal-claim re-verification, per
`.cursor/rules/anchor.mdc`).

There is one pre-existing **untracked** file that is not part of this
workstream's deliverables and was not created by doc-sync work:
`evals/c2_live_prep/live/session_22/hermes_thread_pointers.json` — a runtime
Hermes session-pointer store written by a live-control server dogfood
session. Sibling files in that directory (`current_state.json`,
`live_packet.json`, etc.) are already tracked, so this is probably meant to
be tracked too, but that decision was left to the user/next agent rather than
committed unilaterally.

## 2. Canonical sources, in read order

1. [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md) — sole active sequencing authority. `PR010B: DONE`, `PR011: READY`.
2. [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md) — architecture/authority model (graph-first retrieval boundary, narrow registry-admitted `latest-recap` exception).
3. [`Docs/Plans/REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md`](REANCHOR-hermes-campaign-authoring-foundation-2026-07-15.md) — product-direction re-anchor; §"Next gate" now points at PR011 / Phase 2 creative primitives, not Rung 7.
4. [`Docs/Reports/HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md`](../Reports/HERMES-RUNG7-CUMULATIVE-DOGFOOD-2026-07-16.md) — has a **Merge addendum (2026-07-17)** section listing exactly which critique-fix commits landed and why the verdict changed from `DOING` to `PASS`.
5. [`Docs/Design/ANCHOR-hermes-campaign-sensemaking-goal.md`](../Design/ANCHOR-hermes-campaign-sensemaking-goal.md) — why Hermes exists (sensemaking/authoring partner, not a retrieval report generator).

All five were edited in this session's doc-sync. If you find them
contradicting each other or contradicting `main`, stop and fix the sources
before doing the next task (re-anchor discipline).

## 3. How PR010B actually closed (compressed history)

Rungs 1–4C shipped across PRs #350–#355. Rungs 5 (same-thread continuity via
bounded prose replay) and 6 (durable server-authoritative Hermes session
pointer + reload/process lifecycle) were dogfood-accepted 2026-07-16. Rung 7
(cumulative acceptance + Plan Hermes-only demolition — Live removed from
Plan, retained for `/surface` ChatModule) followed a plan-then-implement
cycle, then went through **three rounds of external critique review** before
merge. Each round produced a commit on the same branch:

| Commit | What it closed |
|---|---|
| `2db5da67` | Claim-authority escape hatches: no implicit trust for zero-tool turns, no missing-provenance→GM-canon default (now `"unknown"`), no cross-revision claim support. |
| `293fdf43` | Model's natural prose is the frontstage answer again (was being replaced by deterministic bullets); labeled honestly as `answer_authority: graph_context_synthesis`; deterministic bullets moved to `support_claim_ledger_text`; explicit `declare_conversation_context` always wins. |
| `09898467` | `ExpansionOperation` reduced to `object`/`neighborhood`/`search`/`support` (dropped unimplemented `compare`/`path`/`timeline`/`coverage` aliases); path-scoped shared lock for `HermesSessionPointerStore`; `GraphClaim.model_validate` round-trip fidelity in hydration; authority-model doc reconciliation (graph-first + narrow `latest-recap` registry exception). |
| `6db1e18a` | `ExpandTarget.kind` restricted to `node`; `relationFamilies`/`claimPredicates`/`bounds` removed from the model-visible schema (executor never implemented them); hydration made fail-closed (rejects malformed claims instead of inventing `revision_id`/`claim_kind`/`authority_class`); pointer-store concurrency documented as same-process-only. |
| `c92e5a02` | Targetless `neighborhood` now fails closed (`ambiguous_target`) instead of silently running `search`; per-operation target cardinality enforced (`object`/`support` exactly one, `neighborhood` 1–8, `search` 0–8); operation trace records `effective_targets` alongside the raw request so the trace can't claim a different operation than what ran. |

**The throughline of all three critique rounds:** the model-visible tool
schema and the Hermes answer-authority labeling must never claim more than
what the executor/validator actually does. If you touch
`expansion_executor.py`, `answer_validator.py`, `session_hydrate.py`, or
`hermes_session_store.py` again, preserve that invariant — it's the thing
three rounds of review converged on.

## 4. What is proven vs. still open

**Proven (deterministic tests + live dogfood, both re-run and passing as of
merge):**

- Same-thread "it" resolution via bounded prose replay; fresh graph retrieval
  is always the factual authority (Rung 5).
- Server-issued opaque `hptr-*` session pointer: thread-scoped binding,
  accepted/rejected/recovered lifecycle, worker-restart telemetry, durable
  across reload (Rung 6).
- Hermes is the only Plan Agent Interaction backend; legacy `activeBackend:
  "live"` Plan threads migrate to Hermes on load; `/surface` ChatModule keeps
  Live explicitly (Rung 7).
- Coverage-gap abstention (graph miss → abstain, never silently falls back to
  Live or Markdown/manifest/corpus search) — proven by contract tests, not a
  required live dogfood turn (tracker gate was explicitly amended for this).
- Expand-tool schema, claim hydration, and pointer-store concurrency now
  match their actual implementations (no overpromised operations, no
  silent-fallback mislabeling, no metadata-inventing hydration).

**Explicitly still open (tracked, not Rung 5/6/7 blockers):**

- Real `AIAgent` wire-start environment failure
  (`test_host_executes_real_aiagent_tool_turn_through_wire` →
  `hermes_worker_start_failed`) — environment/runtime availability issue, not
  a contract failure.
- Source-anchor readability / `unreadable_source_anchors` — separate
  backlog item (`Backlog.md`: "Separate graph continuity from
  source-anchor readability in Hermes acceptance").
- No CI status checks are attached to PRs in this repo. Verification
  provenance is local/manual `pytest`/`vitest` runs. This is a standing,
  accepted limitation, documented explicitly rather than silently assumed.
- Hermes prompt/voice tuning — Hermes over-narrates thread-isolation /
  system-meta details unprompted; parked on `Backlog.md` as two items
  ("Steer Hermes away from thread-isolation / system-meta narration",
  "Hermes prompt tuning + agent configuration deep dive"), not yet started.

## 5. Backlog items relevant to this workstream (read `Backlog.md` in full before starting work — this is a filtered subset)

- `[IDEA]` Steer Hermes away from thread-isolation / system-meta narration
- `[IDEA]` Hermes prompt tuning + agent configuration deep dive
- `[IDEA]` Benchmark Node ingestion with GPT-5.6 for cost comparison
- `[IDEA]` Audit prompt caching across the LLM pipeline
- `[IDEA]` Revision-aware evidence deduplication across graph turns
- `[IDEA]` Separate graph continuity from source-anchor readability in Hermes acceptance
- `[READY]` Hermes backend = in-process agent LLM (not CLI oneshot) — already true post-Rung-4A; verify this entry is stale/completable-as-DONE before starting new work on it.

## 6. Next gate — PR011

**Purpose:** Productionize the graph-grounded Hermes runtime; implement the
full typed capability model from PR005B (`read_only`, `draft_only`,
`preview_write`, `confirm_commit`, `admin_diagnostic` registry;
proposal-bound/revision-bound preview + explicit GM confirmation for durable
writes; cross-thread/current-head invalidation; escalation to Graph
Review/Kernel for corrections).

Full deliverables/success criteria/non-goals are in
`Docs/Plans/PR-TRACKER-campaign-supergraph.md` § "PR011 — Agent Context +
Tool Runtime". Do not start PR011 without re-reading that section plus the
graph-first authority model in the roadmap — PR011 is exactly where a
privileged-writer or fallback-authority regression would first show up.

**Alternative next thread (product, not infra):** Phase 2 creative
primitives — the S2 statblock proving domain
(`CreativeOperationSession`/`GenerationPacket`/`DraftArtifact`/
`PromotionPlan`/`CommitReceipt`) per the REANCHOR record §"Proving sequence".
This is independent of PR011 and can run in parallel.

## 7. Anti-patterns already rejected in this workstream (don't reintroduce)

- Don't let `expand_graph_retrieval`'s model-visible schema advertise a field
  or operation the executor doesn't implement — three critique rounds fixed
  exactly this class of bug repeatedly.
- Don't let missing provenance default to GM-authored canon (`authority_class
  = "unknown"` is correct for ambiguous attributes).
- Don't let zero graph-tool-calls silently authorize model prose as
  graph-grounded — abstain unless `declare_conversation_context` was called
  explicitly.
- Don't invent/rebind `revision_id`/`claim_kind`/`authority_class` during
  IPC hydration — fail closed on malformed claims.
- Don't let Live silently backstop Hermes failures or graph misses on the
  Plan surface — Live is ChatModule-only now.

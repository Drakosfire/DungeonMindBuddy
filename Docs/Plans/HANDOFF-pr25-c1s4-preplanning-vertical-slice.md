---
pr_body_template: |
  ## Summary
  Scaffold the C1S4 preplanning vertical slice as a bounded integration proof: build a C1S1-C1S3-only knowledge-base manifest, prove C1S4 is held out, run deterministic retrieval/context-bundle checks, and leave the live planner/oracle grader for the next PR.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — PR #25 C1S4 preplanning vertical slice scaffold

**Created:** 2026-05-14 (UTC).  
**Status:** READY — dispatch after any active session-memory canonicalization PR is reconciled, or adapt imports to the current mainline shape.  
**Parent agent:** Cursor / planning agent. Dispatcher is responsible for post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`demo_scope.sessions: [1, 2, 3]`, held-out oracle target: Campaign 1 Session 4). This handoff advances M4 by proving the demo boundary before live agent generation.

---

## §1 Mission

Create the first deterministic scaffold for the C1S4 synthetic-preplanning vertical slice.

The slice must prove this boundary:

> Given only Longmont Campaign 1 Sessions 1-3 session-memory records, DungeonMindBuddy can build a single auditable knowledge-base manifest and retrieval/context-bundle surface for C1S4 preplanning while preventing any Session 4 oracle content from entering the planner-visible corpus.

This PR is **not** the live planner run. It is the deterministic foundation that makes the later planner run safe and gradable.

## §2 Why this slice

The repo already has the ingredients:

- C1S1-C1S3 are blessed pilot session-memory records via `PILOT_BLESSED_SESSIONS`.
- Session-memory materialization can verify those records byte-stably.
- Route-equivalence ranking is now the promoted cohort baseline, with conservative query-text-gated aliases.
- Existing vertical slices prove useful patterns: Lysandra proves autonomous agent trace/output grading; recap-ingest proves isolated pre-state corpora, allowlisted reads, sidecar artifacts, and cohort reports.

The missing artifact is the product-loop demo:

```text
C1S1-C1S3 campaign memory
  -> single bounded KB
  -> retrieval/context bundle
  -> synthetic C1S4 preplanning ask
  -> later live planner output
  -> grade against actual C1S4 recap as held-out oracle
```

The actual C1S4 recap exists and is valuable as an oracle, but it must be excluded from planner-visible tools. The first scaffold should therefore prove exclusion before any live LLM run.

## §3 Authoritative inputs

Read these before coding:

1. `AGENTS.md` — token-efficient repo navigation and PR-loop discipline.
2. `.cursor/rules/external-agent-pr-loop.mdc` — §4 allowlist / §5 denylist / §7 verification contract.
3. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — canonical super-plan.
4. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — operational tracker.
5. `Docs/CONVENTION-Session-Recap-Normalization.md` — normalized recap authority and intentional omission of pre-recap chrome.
6. `src/corpus/session_recap_paths.py` — blessed sessions and recap derivative path helpers.
7. `scripts/materialize_session_memory.py` — current materialization/check model.
8. `src/agent/session_memory_query.py` — deterministic retrieval over session-memory records.
9. `evals/lysandra_vertical_slice/README.md` and `GATES.md` — agent-loop benchmark pattern.
10. `evals/session_recap_ingest_vertical_slice/README.md` — isolated corpus / tool-trace / sidecar pattern.
11. Actual held-out oracle path: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md`.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/c1s4_preplanning_vertical_slice/README.md` | Human overview, scope, commands, and phase split. |
| Create | `evals/c1s4_preplanning_vertical_slice/GATES.md` | Gate ledger for deterministic scaffold and later live planner/oracle phases. |
| Create | `evals/c1s4_preplanning_vertical_slice/gold/kb_policy.json` | Defines included C1S1-C1S3 session-memory paths and forbidden C1S4 oracle paths. |
| Create | `evals/c1s4_preplanning_vertical_slice/gold/preplanning_task.json` | Natural synthetic C1S4 preplanning ask and allowed tool/context policy. |
| Create | `evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py` | Build/load the C1S1-C1S3-only KB manifest and assert Session 4 exclusion. |
| Create | `evals/c1s4_preplanning_vertical_slice/step1_retrieval_context.py` | Deterministic retrieval smoke over the combined KB and context-bundle skeleton. |
| Create | `evals/c1s4_preplanning_vertical_slice/preplanning_context_bundle.py` | Bounded conversion from retrieved anchors/routes to planner-visible context snippets/source references. |
| Create | `evals/c1s4_preplanning_vertical_slice/__init__.py` | Package marker / exported helper names if useful. |
| Create | `tests/test_c1s4_preplanning_vertical_slice.py` | Unit tests for KB boundary, C1S4 exclusion, retrieval smoke, and bundle schema. |

If PR #24 lands first and moves session-memory implementation into `src/session_memory/`, use the canonical `src` package. If it has not landed, use existing mainline imports but keep the new slice isolated so imports are easy to update.

## §5 Files explicitly out of scope (denylist)

Do **not** touch these in this PR:

| Path | Why out of scope |
|---|---|
| `src/agent/session_memory_query.py` | This slice should not tune retrieval. It should prove the KB/oracle boundary first. |
| `evals/sentence_routing_retrieval_falsification/**/*.json` | Existing retrieval gold/baselines are not part of the C1S4 scaffold. |
| `corpus/eldyrwild-markdown/**` | Do not edit corpus content or materialized session-memory records in this scaffold. |
| `*.canvas.tsx` | Presentation comes after the scaffold produces real artifacts. |
| `src/prompts/**` | No prompt work until the deterministic boundary is green. |
| Actual C1S4 recap | Oracle source only; never rewrite it in this slice. |

## §6 Implementation contract

### 6.1 KB policy

`gold/kb_policy.json` should declare:

```json
{
  "schema": "dmb_c1s4_preplanning_kb_policy_v1",
  "campaign_id": "longmont-c1",
  "kb_id": "longmont-c1-sessions-01-03-preplanning-kb-v1",
  "included_sessions": [1, 2, 3],
  "heldout_sessions": [4],
  "included_session_memory_relpaths": [],
  "forbidden_oracle_relpaths": [],
  "oracle_source_relpath": "Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md"
}
```

Populate the relpath arrays using corpus-relative POSIX paths. Forbidden paths should include any known Session 4 source/derivative surfaces if present or derivable:

- original C1S4 recap,
- normalized C1S4 recap if present,
- breadcrumbed C1S4 artifact if present,
- session-memory C1S4 records/meta if present.

The policy may include absent forbidden paths as strings; the test should enforce that no loaded KB source path starts with or equals any forbidden path that exists or is named.

### 6.2 Step 0 KB materialization

`step0_kb_materialize.py` should:

- load `gold/kb_policy.json`,
- resolve included C1S1-C1S3 session-memory JSONL paths under `corpus/eldyrwild-markdown`,
- load records with the existing session-memory loader,
- emit a deterministic summary object with:
  - schema,
  - campaign_id,
  - included_sessions,
  - heldout_sessions,
  - source paths,
  - record_count,
  - records_by_session,
  - records_with_routes,
  - forbidden_path_hits,
  - source_hashes or content hashes where easy,
- fail if any record path/source path references Session 4 or forbidden oracle relpaths.

CLI should print JSON or a compact human-readable summary and exit nonzero on boundary violation.

### 6.3 Step 1 retrieval/context bundle smoke

`step1_retrieval_context.py` should:

- call Step 0 to load the combined C1S1-C1S3 records,
- run a small deterministic set of preplanning-oriented queries from `gold/preplanning_task.json`,
- use existing `query_session_memory_candidate` defaults or explicitly documented parameters,
- build a bounded context bundle using `preplanning_context_bundle.py`,
- prove that bundle sources are restricted to C1S1-C1S3.

Do not optimize pass/fail for answer quality yet. This is a boundary and plumbing smoke.

### 6.4 Context bundle schema

The bundle should be planner-visible but oracle-safe:

```json
{
  "schema": "dmb_preplanning_context_bundle_v1",
  "kb_id": "longmont-c1-sessions-01-03-preplanning-kb-v1",
  "campaign_id": "longmont-c1",
  "allowed_sessions": [1, 2, 3],
  "heldout_sessions": [4],
  "query": "...",
  "retrieved_anchor_count": 0,
  "items": [
    {
      "unit_id": "...",
      "session_number": 1,
      "source_recap_path": "...",
      "line_start": 0,
      "line_end": 0,
      "routes": [],
      "why_matched": [],
      "snippet": "bounded snippet or lexical_plain excerpt"
    }
  ],
  "oracle_leakage_check": {
    "forbidden_path_hits": [],
    "forbidden_session_hits": []
  }
}
```

Keep snippets short. The point is to prove safe enrichment, not maximize context volume.

### 6.5 Tests

`tests/test_c1s4_preplanning_vertical_slice.py` should cover:

- policy loads and references C1S1-C1S3 as included sessions,
- C1S4 original recap is listed as oracle/forbidden,
- Step 0 loads records and reports only sessions 1-3,
- Step 0 rejects injected Session 4 source paths or records,
- Step 1 retrieval smoke returns a bundle with allowed sessions only,
- bundle schema contains `allowed_sessions`, `heldout_sessions`, `items`, and leakage check fields.

## §7 Verification commands

The worker must run every command and paste output into the PR body.

```bash
uv run pytest tests/test_c1s4_preplanning_vertical_slice.py -q
uv run python evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py
uv run python evals/c1s4_preplanning_vertical_slice/step1_retrieval_context.py
uv run python scripts/materialize_session_memory.py --all-blessed --check
```

If PR #24 has landed and adds canonical-session-memory tests, also run the canonical-location test suite named by that PR. If it has not landed, do not invent extra scope.

## §8 Reporting contract

In the PR body, include:

1. `git diff --stat` for §4 paths only.
2. Verbatim §7 command outputs.
3. A short statement confirming C1S4 was used only as an oracle path in policy and was not loaded into the KB or context bundle.
4. A short statement confirming this PR does not run a live planner and does not grade prep quality yet.

## §9 Acceptance rubric

The PR is acceptable only if:

- [ ] There is a new `evals/c1s4_preplanning_vertical_slice/` scaffold with README, gates, policy, deterministic Step 0, deterministic Step 1, and tests.
- [ ] C1S1-C1S3 are the only loaded sessions in the KB.
- [ ] C1S4 is explicitly identified as held-out oracle / forbidden planner context.
- [ ] A context bundle can be built from retrieval results without leaking C1S4.
- [ ] No retrieval tuning, corpus mutation, baseline regeneration, canvas edit, or prompt edit is included.
- [ ] All §7 commands pass.

## §10 Future PRs after this scaffold

After this scaffold lands, sequence the live demo in separate slices:

1. **Oracle target authoring:** derive `c1s4_oracle_targets.json` from the actual C1S4 recap, with forecastability labels (`should_surface_from_prior_context`, `plausible_pressure`, `oracle_only_event`, `must_not_predict`).
2. **Live planner trace:** add `step2_preplanning_planner_trace.py` using the same trace/output discipline as the Lysandra vertical slice.
3. **Oracle grader:** add `step3_grade_against_c1s4_oracle.py`, grading prep coverage, grounding, uncertainty hygiene, and oracle leakage.
4. **Cohort/cost wrapper:** optional N-run cohort summary once the single live run is stable.

Do not collapse these into the scaffold PR.

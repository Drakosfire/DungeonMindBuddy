---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: E5 Buddy GenerationEngine migration
  - Flow: E5F
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-E5F-buddy-wiki-prose-generationengine.md
  - Branch / PR: cursor/e5f-wiki-prose-generationengine-990f / #743
  - PR topology: serial

  ## Verification pointer
  - Recovery authority base: Buddy 80162f3b244e8e13dd9368ae636823a377389e47
  - Implementation base: bcc3780811bdfdbb3b2b2b68ee55dc7fe94a7c9b
  - Assigned head at activation: 4e27dcbe0c1b71a6050e8cdce52732069c9532be
  - Verification: HANDOFF §7
---

# HANDOFF — E5F wiki prose generation through GenerationEngine

**Created:** 2026-09-23  
**Status:** MERGED — Buddy PR #743 at `a9495fa0f14a31461de8aa60ed7fc0ad85697a40`
**Canonical handoff path:** `Docs/Plans/HANDOFF-E5F-buddy-wiki-prose-generationengine.md`  
**Conversation/workstream:** `E5 Buddy GenerationEngine migration`  
**Flow / owner:** `E5F / DungeonMindBuddy`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority:** DungeonOverMind handoff commit `637e2461aff0b62fcb582c2baf052181a32cd27b` and roadmap commit `c6b5e5f9b9a8637454f29bb8cb8f43939bbf4981`  
**Design authority base:** `80162f3b244e8e13dd9368ae636823a377389e47`  
**Recovery authority base:** Buddy `80162f3b244e8e13dd9368ae636823a377389e47`  
**Activation gate:** satisfied — E5E merged; PR #742 merged; current `main` has no changes to the E5F lease since implementation base; PR #745 is disjoint; WorldKeeper publication work is not a dependency  
**PR topology:** `serial`  
**PR authorization:** review/update existing PR #743 only; no successor, repair, or cleanup PR is authorized  
**PR title:** `E5F: migrate wiki prose generation through GenerationEngine`

**Completion record:** implementation head `eabc25f8cd9a3ad78078d47e689a63f77b289bec`; merge commit `a9495fa0f14a31461de8aa60ed7fc0ad85697a40`; five formal review cycles; accepted evidence included 39 E5F-focused tests plus an exact-head adjacent E5C–E5E regression union of 169 passed / 36 deselected. The E5F write lease is released.

This is a truthful lifecycle recovery. Implementation PR #743 was opened before
the current ACTIVE/topology handoff law was adopted. This document does not
pretend it preceded that dispatch; it makes the existing lane reviewable under
current authority and records the exact historical base and head.

## §1 Mission and merge-ready invariant

**Mission:** Migrate only `compile_entity_page` from direct OpenAI chat
completion execution to GenerationEngine ordinary text generation.

**Merge-ready invariant:** Buddy continues to own entity selection, projected
fact formatting, both prompts, provider/model resolution and overrides,
`temperature=0.35`, thread-pool concurrency, incremental behavior, empty-output
validation, and wiki persistence; each page operation constructs and awaits its
own GenerationEngine execution context through `run_awaitable_sync`, with no
shared provider or `GenerationClient` across workers.

### Pre-dispatch critique and recovery disposition

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. The slice changes one provider-execution boundary and preserves all product semantics around it. |
| Most likely adversarial sequence | multiple wiki pages compile concurrently → one shared async/provider client crosses worker loops → intermittent loop/thread failure or serialized behavior |
| Will §7 detect that failure? | Yes. Owning-boundary concurrency witnesses record per-page client construction and overlapping worker execution. |
| Easiest owning boundary to under-test | `compile_wiki`, because a helper-only request assertion would not prove thread-pool behavior or persistence. |
| Why serial topology? | One E5 implementation PR exists. No dependent E5 PR may open before #743 merges, state sync completes, and the steward re-anchors. |
| Fact that forces stop/split | Any required change outside the three leased paths, any prompt/model/persistence redesign, or any successor consumer migration. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | DungeonOverMind E5F handoff `637e2461…` and ecosystem roadmap `c6b5e5f9…` |
| Design-time Buddy base | `8afb91687c32b7ba397b9d46b641937cc5420466` |
| Implementation branch base | `bcc3780811bdfdbb3b2b2b68ee55dc7fe94a7c9b` |
| Assigned PR/head at activation | Buddy PR #743 / `4e27dcbe0c1b71a6050e8cdce52732069c9532be` |
| Predecessor contract | E5E Buddy PR #739 merge `1b9f368f644b33733e1930b7ee682318f9e8503e`; GenerationEngine pin `80288d7b467ac3c3586f4e3c964385cefe69f931` |
| Exact input consumed | existing `projection_entity`, entity metadata, Buddy prompts, and Buddy-resolved explicit model |
| Named successor | another explicitly designed E5 inference consumer migration; not selected here |
| What remains false | synthesis, live-query, planners, extractors, graph inference, Batch, repair, and other direct-provider debt remain unmigrated |
| Explicit non-goals | no prompt tuning, model-policy/catalog change, structured output, wiki schema/manifest change, CLI cleanup, WorldKeeper integration, or observation persistence |
| PR topology | `serial` |
| Authorized PR action | review/update existing PR #743 only; no additional PR |
| Open E5 implementation PRs | PR #743 only |
| Stack parent / order | not applicable |
| Branch / checkout | `cursor/e5f-wiki-prose-generationengine-990f` / `DungeonMindBuddy-wt-e5f-wiki-prose-generationengine` |
| Concurrent lanes checked | PR #745 documentation/authority paths are disjoint; WorldKeeper/DungeonMind publication work owns a different repository and contract |
| Runtime/state ownership | tests use injected recorders and temporary/local stores; no shared live provider smoke or external state |
| State-authority sync set after merge | this Buddy handoff completion record; DungeonOverMind E5F handoff status; DungeonOverMind ecosystem roadmap E5F row/prose with PR, merge SHA, review-cycle count, and accepted evidence |

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| one page success | direct shared OpenAI chat completion | explicit `TextRequest` through GE, then unchanged strip/empty validation | Yes | `compile_entity_page` |
| explicit/env/policy model | Buddy resolves model | exact resolved string passes to GE unchanged | Yes | request witness |
| concurrent wiki compile | shared synchronous OpenAI client across workers | no shared provider/GE client; per-operation awaited construction | Yes | `compile_wiki` |
| GE failure/refusal | provider exception | propagates; no placeholder prose or Buddy retry | Yes | page + workflow failure tests |
| incremental skip | unchanged pages skipped | unchanged | Yes | `compile_wiki` store assertions |
| successful persistence | page + manifest written | unchanged; GE observation is not added to manifest | Yes | `compile_wiki` store assertions |
| CLI list/key ordering | current CLI behavior | unchanged | Yes | existing CLI behavior/no diff |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| worker A constructs GE → worker B constructs GE → both overlap | distinct per-page clients/execution contexts; bounded parallelism remains | wiki compiler concurrency tests |
| one worker fails while others run | compile fails truthfully; no partial manifest commit loop is introduced | workflow failure/store assertions |
| caller supplies explicit model while policy differs | explicit model reaches GE unchanged | request recorder test |
| GE returns whitespace | `RuntimeError("Empty wiki article for <entity_id>")` | empty-output regression |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/compiler/wiki_compiler.py` | migrate exactly wiki page text execution to GE and eliminate shared provider client |
| Modify | `tests/test_wiki_compiler.py` | prove request, prompt, model, output, failure, persistence, and concurrency invariants |
| Modify | `tests/test_e5a_boundary_fitness.py` | move exactly this consumer from direct-provider debt to GE consumer inventory |

**Bounded discovery exception:** Not applicable — the candidate PR already has
exactly these three changed paths. Any additional path is a stop report.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `MODEL_POLICY.json` | Buddy policy remains authoritative and unchanged |
| `pyproject.toml`, `uv.lock` | accepted GE dependency pin is unchanged |
| `src/llm/generation_sync.py` | mechanics-only bridge was proved by E5D/E5E; no change required |
| `src/cli.py`, `tests/test_cli.py` | preserve existing API-key and `--list` ordering; no cleanup |
| `src/agent/**`, `src/live_play/**`, extractor/Batch/repair paths | separate E5 consumers and successor capabilities |
| wiki schemas, manifest formats, persistence modules | E5F does not create or revise a durable product contract |
| WorldKeeper/DungeonMind publication paths | governed write/publication work is orthogonal to local wiki prose generation |
| PR #745 authority/design files | concurrent lane is disjoint and owns its own documents |

## §6 Implementation contract

```text
Input:
  entity ID + metadata + projected entity facts + optional explicit model

Output:
  stripped non-empty wiki article string; existing compile_wiki persistence

Invariant:
  Buddy chooses and persists; GE executes exactly Buddy's text request; no
  provider/GE client is shared across ThreadPoolExecutor workers.

Failure behavior:
  missing CLI/API credential behavior remains unchanged
  GE failure/refusal → propagate, no fallback and no Buddy retry
  blank provider text → existing entity-specific RuntimeError

Replay / idempotency:
  unchanged fact fingerprint → existing incremental skip
  changed facts or forced/full selection → existing recompilation behavior
  partial worker failure → no new recovery or manifest semantics

Trust boundary:
  Buddy verifies and owns prompts, selection, model, product output, and storage.
  GE owns provider execution, retries/deadline, normalized failures, and observation.
  Buddy does not persist GE observation as wiki product data.
```

Required GE request fields:

```text
system_prompt = WIKI_SYSTEM_PROMPT
user_prompt = unchanged entity-page prompt
provider = "openai"
model = Buddy-resolved explicit model
profile = None
temperature = 0.35
```

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| exact request and model pass-through | page compiler | contract/regression | focused wiki tests | system/user prompts, provider/model/profile/temperature exact | any drift |
| no shared client across workers | full wiki workflow | adversarial concurrency | focused wiki tests | per-page construction in worker awaited contexts; overlap retained | shared client or helper-only proof |
| failures/blank output remain truthful | page/workflow | failure injection | focused wiki tests | propagated GE failure and entity-specific empty error | fallback/retry/opaque success |
| incremental persistence unchanged | full wiki workflow/store | regression | focused wiki tests | same skip, pages, manifest fields; no observation data | durable contract drift |
| debt inventory moves one consumer | architecture fitness | fitness | E5A fitness test | wiki leaves OpenAI debt and enters GE inventory exactly once | census mismatch |
| model authority remains Buddy-owned | policy boundary | regression | model-policy tests | current parity plus explicit/env override pass-through | GE profile/catalog selection |
| adjacent E5 consumers remain green | E5 regression surface | regression | focused E5C/E5D/E5E selection | no regression | newly failing test |

Exact verification commands:

```bash
uv lock --check
uv sync
uv run ruff check src/compiler/wiki_compiler.py tests/test_wiki_compiler.py tests/test_e5a_boundary_fitness.py tests/test_model_policy_authority.py
uv run pytest -q tests/test_wiki_compiler.py tests/test_e5a_boundary_fitness.py tests/test_model_policy_authority.py
git diff --check
git diff --name-only bcc3780811bdfdbb3b2b2b68ee55dc7fe94a7c9b...HEAD
```

### Minimal live / dogfood proof

Not applicable — this is a provider-transport migration with injected owning-
boundary request/concurrency witnesses. No paid-provider smoke is required.

### Baseline failure handling

If a required command fails, compare the same command at implementation base
`bcc378081…` and the PR head. Do not classify a Generation, concurrency, prompt,
model, or persistence failure as baseline debt.

## §8 Required review handback

Record:

1. Review Cycle number and exact PR #743 head;
2. implementation base `bcc378081…` and recovery authority base `80162f3b…`;
3. serial topology and observed open E5 PR set;
4. mission/invariant disposition;
5. independently rerun §7 results and CI provenance;
6. one-commit implementation story and any finding-led fix commits;
7. actual paths versus §4;
8. baseline failures or waivers;
9. paths outside §4 (`none` or stop);
10. concurrency, prompt/model, failure, persistence, and CLI dispositions;
11. named successor still false;
12. truthful note that lifecycle authority was recovered after initial dispatch.

## §9 Acceptance rubric

- [ ] This recovery handoff is durably present and ACTIVE on Buddy `main` before formal Review Cycle 1.
- [ ] The pre-existing dispatch is recorded truthfully; it is not misrepresented as having followed the newer lifecycle law.
- [ ] Serial topology is honored and only existing PR #743 is updated/reviewed.
- [ ] Exactly `compile_entity_page` moves from direct OpenAI execution to GE text execution.
- [ ] Buddy-owned selection, prompts, model/overrides, `temperature=0.35`, concurrency, incremental behavior, empty validation, and persistence are unchanged.
- [ ] Each production page operation constructs GE inside its own awaited worker context; no shared provider/GE client exists across workers.
- [ ] Actual changed paths are exactly the three §4 paths.
- [ ] Required §7 evidence passes independently or baseline differences are reported truthfully.
- [ ] No GE observation is added to wiki manifest/product persistence.
- [ ] No WorldKeeper/DungeonMind publication dependency is introduced.
- [ ] No successor consumer migration or second PR is opened.

## Stop conditions

Stop and return to the steward if review requires another production/test path,
changes model-policy/catalog/prompt/persistence/CLI semantics, discovers a real
WorldKeeper dependency, cannot prove per-worker client construction at the
workflow boundary, or would open another E5 PR before #743 merges and the state
sync completes.

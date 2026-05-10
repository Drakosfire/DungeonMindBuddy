# DungeonBuddy LLM + Benchmarking Client (extraction seed)

**Date created:** 2026-05-10
**Status:** **SEED** — observation captured during the PR #5 → A/B Benchmarking Sprint planning conversation. Not an active workstream. Do not let it pull weight from `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`'s active sprint. Promote to `PROPOSAL` only when an active workstream needs its surface, or when the A/B sprint's L3 deliverable lands and we have a concrete second consumer in scope.
**Scope:** A possible future extracted Python (initially) client that DungeonBuddy publishes — exposing **(1)** generic LLM calls and **(2)** the benchmarking-call discipline this vertical slice is converging on — to be consumed by sibling DungeonMind services and external automations.
**Replaces / supersedes:** No prior doc.

---

## 1. The seed observation

While planning the A/B Benchmarking Sprint (`PLAN-split-corpus-retrieval-to-autonomous-demo.md` § *A/B Benchmarking Sprint (post-PR #5)*), two surfaces inside `evals/sentence_routing_retrieval_falsification/` became visible as having different shapes than each other:

1. **The retrieval-benchmarking wrapper.** `breadcrumb_query_run.py` plus the route-equivalence loader, the per-scenario shadow payload builder, the `--retrieval-only` mode, the harness-boundary safety contract, the planned cohort runner and recall-via-equivalence metric, the upcoming additive ranking-input wiring — these all share a shape: **a benchmarking call** that takes (gold, records, options), produces a structured per-scenario report with cost / provenance / shadow lanes, and emits durable disk artifacts by default. This shape is increasingly abstract and not very Eldyrwild-specific.

2. **The LLM call itself.** `OpenAI()` constructed via `bootstrap_env.load_dungeonmindbuddy_dotenv()` + `_load_api_key()` (per `dungeonbuddy-environment.mdc`); strict JSON envelope via `text.format` (per `planner-turn-output-schema.mdc`); cost telemetry; structured-output validation; planner two-phase commit for any writes (per `corpus-two-phase-commit.mdc`). This shape is **already** generic — the model name, prompt, and schema vary per use case, but the canonical client-construction pattern, env-loading, output-shape enforcement, and cost / retry / error envelope are common.

Both shapes already exist as code in this repo. Neither is currently exposed as a library a sibling service could import; both are stitched into entry-point scripts and harnesses.

The seed: at some point — **not now** — both surfaces could be lifted into a thin `dungeonbuddy_client` package that DungeonMind sister services consume. The retrieval-benchmarking wrapper would be one of the first non-trivial benchmarking call shapes; the LLM call would be the generic surface underneath it.

## 2. What an extracted client could carry forward

Discipline this repo has accumulated that the client would carry as **defaults**, not opt-ins (rule references are always-on, not retrieved on demand):

| Lesson | Source rule / doc | What the client surface enforces |
| --- | --- | --- |
| Cost as leading indicator | `cost-as-signal.mdc` | Every call returns structured cost telemetry; cohort surfaces emit `min/mean/max/sum`; thresholds (1.5×, 2.0×, $200/$500/$1000) flagged in-band. |
| Anti-oracle leakage | `.cursor/rules/anti-oracle-leakage.mdc` | LLM-call surface refuses to inline gold-only fields; benchmarking-call surface refuses to mix grader internals into generation paths. |
| Verify before debug + tighten the contract | `verify-before-debug.mdc` | Benchmarking calls report rubric / threshold provenance with every result; gold realignment requires an explicit `notes` field, not a silent edit. |
| Gold realignment vs deflation | `.cursor/rules/gold-realignment-vs-deflation.mdc` | Same — rubric carries the "would I want to fix it or hide it?" diagnostic as a required check before accepting a gold edit. |
| Test the boundary that owns the rubric | `external-agent-pr-loop.mdc` invariant #2 (codified after PR #4 round 1) | Benchmarking-call results name the boundary their rubric describes; loader-side or unit-side coverage flagged as insufficient when the rubric is harness-level. |
| Stochastic gates need multi-trial | `verify-before-debug.mdc` § "Stochastic gates need multi-trial verification" | LLM-call surface exposes a built-in N-trial mode with pass-rate aggregation, not single-trial booleans. |
| Disk artifacts by default | `benchmark-disk-artifacts.mdc` | Every benchmark call writes a default summary artifact without env-var coercion; override is opt-in. |
| Two-phase commit for writes | `corpus-two-phase-commit.mdc` + `src/agent/corpus_writer.py` | Any client-mediated write surface enforces preview → `confirm_token` → commit; autonomous mode wraps both phases in dispatcher loopback. |
| LLM context discovery, not provision | `llm-context-discovery.mdc` | Generic LLM-call surface refuses to embed corpus paths or per-task workflows in `user_message`; only task framing + corpus tree + tool results allowed. |
| Strict JSON envelope (`user_intent` + `message` + `unsure_queue`) | `planner-turn-output-schema.mdc` | Planner-shaped LLM call uses `text.format` strict JSON; new top-level fields must be in `required` with nullable types for "absent." |
| OpenAI client construction canonical pattern | `dungeonbuddy-environment.mdc` | One way to construct the client; `OpenAI()` with no `api_key=` arg; pre-flight `_load_api_key()` check; never reinvent `_load_dotenv()`. |
| PII / payload hygiene | `corpus-pii-and-llm-payloads.mdc` | Client refuses to send corpus content to non-allowlisted tools; `.env` never echoed; secrets never passed via shell flags. |
| Workspace-relative provenance fields | PR #5 (`40be747a`) + new rubric bullet on `external_pull_requests[github-pr-5]` | Provenance fields rendered at the harness boundary, not at the loader; tested with subprocess from ≥2 CWDs asserting full-payload byte-identity. |
| External-agent PR loop discipline | `external-agent-pr-loop.mdc` + `.cursor/skills/external-agent-pr-loop/SKILL.md` | If the client is consumed by an automation that opens PRs, the four-stage cycle (HANDOFF → PR → judgment record → atomic doc-sync) is part of its operator runbook. |

This is not all of the discipline. It's the load-bearing patterns that most often pay back the cost of being reified as code rather than re-derived per project.

## 3. The DungeonMindServer audit angle

DungeonMindServer (`~/Projects/DungeonOverMind/DungeonMindServer/`, sibling repo) already serves LLM calls in production for CardGenerator, StatblockGenerator, RulesLawyer, and the Player Character Generator. It predates most of the discipline above. The seed insight from the user: a future client extraction is the right moment to **audit DungeonMindServer's existing LLM and benchmarking patterns** — what it does right (and we should keep), what's imperfect (and we should improve in the lift), and what's outright insecure (and the lift is a chance to repair, not entrench).

This audit is **not** a precondition for the A/B sprint. It's a precondition for promoting this seed to PROPOSAL. Concrete questions the audit would answer (for the future agent who picks this up):

- **Right:** What auth + secrets pattern is in production? What cost telemetry exists? What error-envelope conventions does the FastAPI surface assume? What patterns from `LandingPage` consume them well?
- **Imperfect:** Where does the same code repeat across `cardgenerator/`, `statblockgenerator/`, `playercharactergenerator/`, `ruleslawyer/`? Where do retry / timeout / structured-output validation policies diverge? Where is cost telemetry missing?
- **Insecure:** Are API keys ever logged, passed through query strings, embedded in client bundles, or echoed in tracebacks? Are PII / corpus contents ever sent to non-allowlisted tools? Are CSP / CORS / SPA `try_files` cases handled in nginx config?

The audit's deliverable would be a sibling design doc — `Docs/Design/AUDIT-dungeonmindserver-llm-and-benchmarking.md` (or similar) — that becomes the input contract for the client's first surface.

## 4. What this seed is NOT

- **Not** a refactor proposal. The current code stays where it is until there is a concrete second consumer asking for the lift.
- **Not** a redesign of `breadcrumb_query_run.py`, `route_equivalence_shadow.py`, or any active eval. The A/B Benchmarking Sprint runs against the code as-shipped.
- **Not** a sprint. No PR is anchored to this doc.
- **Not** a commitment to extract the client in this repo specifically. If the right home is a new sibling repo (`DungeonMindClient/` under `DungeonOverMind/`), that decision belongs to the audit + PROPOSAL stage.
- **Not** a service boundary change. Existing service independence rules (`QUICK-REFERENCE-DungeonMind.mdc` § "Service Independence (Non-Negotiable)") still hold. The client is a **library** consumed by services, not a fifth service.

## 5. Promotion criteria — when this doc moves from SEED to PROPOSAL

Promote (and rename to `DESIGN-...` without the `-seed` suffix) only when **all** are true:

1. **A/B Benchmarking Sprint L3 has shipped or is committed.** We need at least one Phase 5 exit's worth of lived experience with the benchmarking-call shape before extracting it.
2. **A concrete second consumer is named.** Either DungeonMindServer wants the LLM client, or a new sister project (a benchmarking-as-a-service surface, a different vertical slice) needs the benchmarking call.
3. **The DungeonMindServer audit doc exists.** Without it, "absorbs lessons from DungeonMindServer" is hand-waving.
4. **An owner exists.** Extraction work doesn't happen well without a single person (or a single agent thread) carrying the architectural memory.

If any criterion is not yet true, leave this doc as SEED and continue building the discipline in-place.

## 6. Cross-references

- **PLAN:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — § *A/B Benchmarking Sprint (post-PR #5)*. Source of the observation that triggered this seed.
- **Existing benchmark philosophy:** `Docs/Design/DESIGN-benchmark-philosophy-and-goals.md`, `Docs/Design/DESIGN-benchmark-philosophy.md`. The principles those docs describe become the client's defaults.
- **Existing citation-grounding direction:** `Docs/Design/DESIGN-citation-grounded-corpus-architecture.md`. Provenance fields the LLM-call surface would carry.
- **DungeonMindServer (read-only sibling):** `~/Projects/DungeonOverMind/DungeonMindServer/`. Audit target.
- **Always-on rule references:** see § 2 table.
- **Per-project backlog (this repo):** `Backlog.md` — see the `[IDEA]` entry pointing back here.
- **Cross-project tooling backlog:** `~/.cursor/learnings/Backlog.md` — see the cross-project `[IDEA]` on "benchmarking discipline becomes a reusable client surface."

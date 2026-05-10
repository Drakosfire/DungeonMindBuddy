# Naming: benchmark / evaluation vs runtime control

Use vocabulary that tells readers whether something **scores a harness** or **drives product behavior**.

## Principles

| Category | Meaning | Examples |
|----------|---------|----------|
| **Benchmark / observation** | After-the-fact checks, gold JSON, CI gates. Does **not** change planner instructions, tool list, or Cursor routing unless a human/script acts on the report. | Step 2 post-planner eval, `gold/*.json` `final.require`, `intent_expectations_*` |
| **Runtime / control** | What the agent actually does next: model calls, tool dispatch, env-driven scenario selection for a **live** run, skill attachment. | `run_planning_turn_detailed`, `make_tool_dispatcher`, `classify_intent` when used to pick a skill before a turn |

## Lysandra vertical slice — quick map

| Name | Kind | Note |
|------|------|------|
| `gold/planner_step1_*.json` | **Benchmark** | Scenario **gates** (substring / tool / min chars). `steps: []` — no scripted model checklist. |
| `LYSANDRA_PLANNER_STEP1_SCENARIO` | **Harness input** | Picks which **gold file** to load for that run. **Unset** in the Step 1 CLI → default **`upgrade_prose`** (power-rise benchmark). Not the production “session type” API. |
| `scenario_key` / `fixture_role` on `PlannerStep1Run` | **Benchmark** | Which gold scenario was used for scoring. |
| `scenario_key_for_user_line` | **Harness helper** | Chooses **which gold file** when only a user line is set (intent → `upgrade_prose` vs `autonomous`). Same classifier as product may use, but here the **consumer** is benchmark loading, not the planner loop. |
| `gold/step2_canonical_and_intent.json` → `planner_bridge` | **Benchmark (JSON key)** | Historical key name: **post-planner Step 2 checks only** (intent assertions + optional trace vs canonical path). **Does not** connect two runtime pipelines. |
| `intent_expectations_by_planner_scenario_key` | **Benchmark** | Optional **gold assertions** on `classify_intent` output for a given planner scenario key (“intent lock” in informal chat = **benchmark intent assertion**). |
| `evaluate_step2_post_planner_benchmark` | **Benchmark** | Python entrypoint for the above. |
| `LiveEvalResult.violations["step2_bridge"]` | **Benchmark (legacy bucket key)** | Where post–Step-1 Step 2 violations are merged for reporting. Key name kept for compatibility with existing parsers. |
| `post_planner_step2_benchmark_detail` on `PlannerStep1Run` | **Benchmark** | Echo / debug payload from that evaluation. |
| Cursor skill `npc-power-increase` | **Runtime guidance** | Human/agent workflow outside this JSON gate. |

When adding new APIs, prefer names like **`evaluate_*`**, **`assert_gold_*`**, **`benchmark_*`** for observation paths, and reserve **`run_*`**, **`dispatch_*`**, **`route_*`** for paths that change behavior.

# Flow: user text → intent → skill → research → attach → prose → combine

**Status:** Target architecture (partially implemented in Buddy + Cursor skill).  
**Related:** `src/agent/skill_pipeline.py`, `.cursor/skills/npc-power-increase/SKILL.md`, `evals/lysandra_vertical_slice/step1_planner_trace.py` (`upgrade_prose`), `src/npc_statblock_pipeline/canonical_intent.py` (`classify_intent`).

---

## Target pipeline (what you expect)

```mermaid
flowchart LR
  U[User text] --> I[Intent check]
  I --> S[Select skill]
  S --> R[Research]
  R --> A[Attach baseline]
  A --> P[Write prose]
  P --> C[Combine]
```

| Step | Meaning | Primary artifacts |
|------|---------|-------------------|
| **1. User text in** | GM request (e.g. bump Lysandra, prep Mossford). | `user_line` |
| **2. Intent check** | Classify ask: upgrade vs lookup vs comparison, power axis. | `IntentClassification` (`classify_intent`) |
| **3. Select skill** | Pick workflow pack (instructions + gates). | Cursor skill id, e.g. `npc-power-increase` |
| **4. Research** | Hub README → dossier / timeline / recaps via `read_corpus_file`. | `tool_trace` paths |
| **5. Attach** | Load canonical `*_statblock_*.md` into working context. | `load_context_markdown` + trace |
| **6. Write prose** | Creative power-rise brief (no stat retype). | `final_text` (planner) or assistant message |
| **7. Combine** | Merge user line + intent + skill id + trace + prose into a **bundle** for generator/store/Step 4. | Level-up context JSON / HTTP payload (future or `step4_levelup_context`) |

---

## What exists today

| Step | Buddy / repo state |
|------|---------------------|
| **Intent** | `classify_intent()` in `canonical_intent.py` — LLM-backed (cheap model via `MODEL_POLICY.json`; test doubles for offline). |
| **Skill select** | `route_user_line_to_skill()` in `src/agent/skill_pipeline.py` maps `upgrade_request` → `npc-power-increase`. |
| **Scenario routing** | When ``LYSANDRA_PLANNER_STEP1_SCENARIO`` is **unset** and there is **no** user-message override, default gold is **upgrade_prose** (power-rise benchmark). If ``LYSANDRA_PLANNER_USER_MESSAGE`` (or ``user_line_override=``) is set without SCENARIO, ``scenario_key_for_user_line`` picks ``upgrade_prose`` vs ``autonomous``. Explicit env pins ``directed`` / ``stat_check`` / etc. |
| **Skill body** | Cursor skill `.cursor/skills/npc-power-increase/SKILL.md` (human + IDE agent). |
| **Research + attach + prose** | Planner tools + global `instructions` only; `upgrade_prose` gold adds **gates** (`read_corpus_file` + `load_context_markdown`) but no scenario instruction appendix. |
| **Intent after planner (benchmark only)** | Step 2 **`evaluate_step2_post_planner_benchmark`** (gold key `planner_bridge`) may run `classify_intent` on the same `user_message` for **harness** scoring (`step2_bridge` violation bucket) — **post hoc observation**, not a router that picks the skill before the turn. |
| **Combine** | Step 4 bundle / StatblockGenerator handoff is **separate**; not a single function that consumes `RoutedTurn` yet. |

---

## Gap (explicit)

- **Orchestrator** that runs: `RoutedTurn` → inject full Cursor skill markdown into planner `instructions` is **not** wired yet. The benchmark **CLI** defaults to **upgrade_prose** when both env vars are unset; intent-route via ``LYSANDRA_PLANNER_USER_MESSAGE`` without ``LYSANDRA_PLANNER_STEP1_SCENARIO`` still picks gold from ``scenario_key_for_user_line``.
- **Combine** as one typed “handoff object” from intent + trace + prose is still **design / Step 4** work.

---

## Suggested next implementation (when you wire the orchestrator)

1. On each user line: `routed = route_user_line_to_skill(user_line)`.
2. If `routed.skill_cursor_id == "npc-power-increase"`: append skill protocol (from SKILL or a short cached excerpt) to planner instructions **before** `responses.create`.
3. Run planner (research → attach → prose inside model behavior + gates).
4. **Combine:** build a dict `{user_line, intent: routed.intent, skill: routed.skill_cursor_id, tool_trace, final_text}` and pass to Step 4 / generator.

This doc is the contract reference until that orchestrator lands.

<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-20T14:41:58Z | scenario: dustwalker_factual_ac | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--dustwalker_factual_ac--gpt-5.4-mini--PASS--1turn--20260420T144158Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_dustwalker_factual_ac
scenario_key:     dustwalker_factual_ac
model_id:         gpt-5.4-mini
gates_passed:     True
review_mode:      summary
corpus_fprint:    a090a1d95dc07bcba3f2cb95ee6128d9
corpus_dir:       /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  3

========================================================================
§ Prompt payload sizes (characters)
========================================================================
instructions:  {'chars': 20876, 'bytes': 23548, 'sha256_16': 'f8e3a0f291cd75ef'}
user_line:     {'chars': 104, 'bytes': 106, 'sha256_16': '161dc77e839ae03a'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=8699 output_tokens=88 cached_tokens=8192
  round[1] input_tokens=9535 output_tokens=41 cached_tokens=8704
  round[2] input_tokens=11592 output_tokens=98 cached_tokens=9216
  planner_estimated_cost_usd: 0.005765
  scenario_estimated_cost_usd: 0.005765

========================================================================
§ Statblock / working-context evidence (tool wire)
========================================================================
Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of each tool return (same bytes sent to the API in that round).

load_context_markdown: 0 calls — no explicit attach tool in trace; if the model only used ``read_corpus_file`` on a statblock, the file still entered that round's outputs, but nothing is labeled ``[context attached: …]``.

read_corpus_file on paths containing 'statblock': 2 (indices [1, 2])

========================================================================
§ Clarification (turn 0 prose / JSON heuristics)
========================================================================
Clarification is expressed in the final JSON (`user_intent` + `message`) when needed; there is no separate clarification tool in the planner.

tool_trace rows (for context): 3

(Single-turn scenario: final answer is only under § Final LLM answer below.)
========================================================================
§ Final LLM answer
========================================================================
{"user_intent":"factual_lookup","message":"Dustwalker’s AC from the Shepherd’s Flock mechanical sheet is **13** in `Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md`. The legacy redirect `Elderwyld/Shephards Flock/Statblocks and Tokens/DustWalker.md` just points back to that sheet.","unsure_queue":null}
========================================================================

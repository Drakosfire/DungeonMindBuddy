<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-20T17:55:06Z | scenario: dustwalker_factual_ac | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--dustwalker_factual_ac--gpt-5.4-mini--PASS--1turn--20260420T175506Z.md -->

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
tool_trace rows:  2

========================================================================
§ Prompt payload sizes (characters)
========================================================================
instructions:  {'chars': 24887, 'bytes': 27703, 'sha256_16': '7445ed6d03ca09bc'}
user_line:     {'chars': 104, 'bytes': 106, 'sha256_16': '161dc77e839ae03a'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=9739 output_tokens=26 cached_tokens=9216
  round[1] input_tokens=10411 output_tokens=41 cached_tokens=9216
  round[2] input_tokens=12468 output_tokens=68 cached_tokens=10240
  planner_estimated_cost_usd: 0.005717
  scenario_estimated_cost_usd: 0.005717

========================================================================
§ Statblock / working-context evidence (tool wire)
========================================================================
Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of each tool return (same bytes sent to the API in that round).

load_context_markdown: 0 calls — no explicit attach tool in trace; if the model only used ``read_corpus_file`` on a statblock, the file still entered that round's outputs, but nothing is labeled ``[context attached: …]``.

read_corpus_file on paths containing 'statblock': 1 (indices [1])

========================================================================
§ Clarification (turn 0 prose / JSON heuristics)
========================================================================
Clarification is expressed in the final JSON (`user_intent` + `message`) when needed; there is no separate clarification tool in the planner.

tool_trace rows (for context): 2

(Single-turn scenario: final answer is only under § Final LLM answer below.)
========================================================================
§ Final LLM answer
========================================================================
{"user_intent":"factual_lookup","message":"Dustwalker’s AC is **13** in the Shepherd’s Flock stat markdown at `Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md`.","unsure_queue":null}
========================================================================

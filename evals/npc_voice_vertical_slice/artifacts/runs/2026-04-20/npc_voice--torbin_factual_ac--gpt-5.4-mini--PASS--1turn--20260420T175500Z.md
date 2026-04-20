<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-20T17:55:00Z | scenario: torbin_factual_ac | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--torbin_factual_ac--gpt-5.4-mini--PASS--1turn--20260420T175500Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_torbin_factual_ac
scenario_key:     torbin_factual_ac
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
user_line:     {'chars': 102, 'bytes': 102, 'sha256_16': '27ff02a7fb2be7a9'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=9740 output_tokens=66 cached_tokens=9216
  round[1] input_tokens=10904 output_tokens=75 cached_tokens=9728
  planner_estimated_cost_usd: 0.00333
  scenario_estimated_cost_usd: 0.00333

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
{"user_intent":"factual_lookup","message":"Torbin Jove’s Armor Class on the ingested sheet in `Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md` is **10**.","unsure_queue":null}
========================================================================

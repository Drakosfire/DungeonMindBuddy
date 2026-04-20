<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-17T03:31:29Z | scenario: dustwalker_factual_ac | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--dustwalker_factual_ac--gpt-5.4-mini--PASS--1turn--20260417T033129Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_dustwalker_factual_ac
scenario_key:     dustwalker_factual_ac
model_id:         gpt-5.4-mini
gates_passed:     True
review_mode:      summary
corpus_fprint:    bc0dc21deff76ffaf4efa409d6d91968
corpus_dir:       /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  2

========================================================================
§ Prompt payload sizes (characters)
========================================================================
instructions:  {'chars': 17251, 'bytes': 19393, 'sha256_16': 'cd28059f8f6f99cf'}
user_line:     {'chars': 104, 'bytes': 106, 'sha256_16': '161dc77e839ae03a'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=7200 output_tokens=91 cached_tokens=6656
  round[1] input_tokens=9951 output_tokens=63 cached_tokens=7168
  planner_estimated_cost_usd: 0.004225
  scenario_estimated_cost_usd: 0.004225

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
{"user_intent":"factual_lookup","message":"Dustwalker’s AC is **13** in the Shepherd’s Flock stat markdown: `Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md`."}
========================================================================

<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-20T14:42:06Z | scenario: dustwalker_directed_statblock_path | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--dustwalker_directed_statblock_path--gpt-5.4-mini--PASS--1turn--20260420T144206Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_dustwalker_directed_statblock_path
scenario_key:     dustwalker_directed_statblock_path
model_id:         gpt-5.4-mini
gates_passed:     True
review_mode:      summary
corpus_fprint:    a090a1d95dc07bcba3f2cb95ee6128d9
corpus_dir:       /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  1

========================================================================
§ Prompt payload sizes (characters)
========================================================================
instructions:  {'chars': 20876, 'bytes': 23548, 'sha256_16': 'f8e3a0f291cd75ef'}
user_line:     {'chars': 256, 'bytes': 258, 'sha256_16': '304b6f74a0de0cea'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=8739 output_tokens=41 cached_tokens=8192
  round[1] input_tokens=10796 output_tokens=123 cached_tokens=8704
  planner_estimated_cost_usd: 0.003984
  scenario_estimated_cost_usd: 0.003984

========================================================================
§ Statblock / working-context evidence (tool wire)
========================================================================
Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of each tool return (same bytes sent to the API in that round).

load_context_markdown: 0 calls — no explicit attach tool in trace; if the model only used ``read_corpus_file`` on a statblock, the file still entered that round's outputs, but nothing is labeled ``[context attached: …]``.

read_corpus_file on paths containing 'statblock': 1 (indices [0])

========================================================================
§ Clarification (turn 0 prose / JSON heuristics)
========================================================================
Clarification is expressed in the final JSON (`user_intent` + `message`) when needed; there is no separate clarification tool in the planner.

tool_trace rows (for context): 1

(Single-turn scenario: final answer is only under § Final LLM answer below.)
========================================================================
§ Final LLM answer
========================================================================
{"user_intent":"factual_lookup","message":"- Combat fact: `Elderwyld/Shephards Flock/NPCs/dustwalker/dustwalker_statblock.md` gives Dustwalker **AC 13, HP 45, CR 3**, and **Words of the Shepherd** can charm a creature within 60 ft. as a bonus action.\n- Roleplay hook: he speaks in **slow poetic riddles**, hates mirrors, and is terrified of being **forgotten** more than of dying.","unsure_queue":null}
========================================================================

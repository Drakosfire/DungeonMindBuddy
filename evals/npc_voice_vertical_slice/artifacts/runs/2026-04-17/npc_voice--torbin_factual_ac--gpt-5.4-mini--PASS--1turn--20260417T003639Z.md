<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-17T00:36:39Z | scenario: torbin_factual_ac | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--torbin_factual_ac--gpt-5.4-mini--PASS--1turn--20260417T003639Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_torbin_factual_ac
scenario_key:     torbin_factual_ac
model_id:         gpt-5.4-mini
gates_passed:     True
review_mode:      summary
corpus_fprint:    52196a8642f41500d73d1fdc98ca334a
corpus_dir:       /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  2

========================================================================
§ Prompt payload sizes (characters)
========================================================================
instructions:  {'chars': 14482, 'bytes': 16414, 'sha256_16': 'c736a5d88620fcfe'}
user_line:     {'chars': 102, 'bytes': 102, 'sha256_16': '27ff02a7fb2be7a9'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=5694 output_tokens=83 cached_tokens=5120
  round[1] input_tokens=6826 output_tokens=61 cached_tokens=5632
  planner_estimated_cost_usd: 0.00278
  scenario_estimated_cost_usd: 0.00278

========================================================================
§ Statblock / working-context evidence (tool wire)
========================================================================
Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of each tool return (same bytes sent to the API in that round).

load_context_markdown: 0 calls — no explicit attach tool in trace; if the model only used ``read_corpus_file`` on a statblock, the file still entered that round's outputs, but nothing is labeled ``[context attached: …]``.

========================================================================
§ Clarification (tool + turn 0 prose)
========================================================================
Use this block to see whether the model surfaced clarification via tool calls and/or turn-0 prose.

propose_clarification tool: 0 calls in merged trace

(Single-turn scenario: final answer is only under § Final LLM answer below.)
========================================================================
§ Final LLM answer
========================================================================
{"user_intent":"factual_lookup","message":"Torbin Jove’s Armor Class on the ingested sheet is **10**. It appears in **Longmont Campaign/NPCs/Torbin Jove/Torbin Jove.md**."}
========================================================================

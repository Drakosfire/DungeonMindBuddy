<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-17T00:36:51Z | scenario: dustwalker_factual_cr | model: gpt-5.4-mini | gates: PASS | turns: 1 | primary: npc_voice--dustwalker_factual_cr--gpt-5.4-mini--PASS--1turn--20260417T003651Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_dustwalker_factual_cr
scenario_key:     dustwalker_factual_cr
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
user_line:     {'chars': 28, 'bytes': 28, 'sha256_16': 'e0ad41a4ec23d5b5'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=5676 output_tokens=89 cached_tokens=5120
  round[1] input_tokens=10284 output_tokens=53 cached_tokens=5632
  planner_estimated_cost_usd: 0.005351
  scenario_estimated_cost_usd: 0.005351

========================================================================
§ Statblock / working-context evidence (tool wire)
========================================================================
Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of each tool return (same bytes sent to the API in that round).

load_context_markdown: 0 calls — no explicit attach tool in trace; if the model only used ``read_corpus_file`` on a statblock, the file still entered that round's outputs, but nothing is labeled ``[context attached: …]``.

read_corpus_file on paths containing 'statblock': 1 (indices [0])

========================================================================
§ Clarification (tool + turn 0 prose)
========================================================================
Use this block to see whether the model surfaced clarification via tool calls and/or turn-0 prose.

propose_clarification tool: 0 calls in merged trace

(Single-turn scenario: final answer is only under § Final LLM answer below.)
========================================================================
§ Final LLM answer
========================================================================
{"user_intent":"factual_lookup","message":"The Dustwalker’s CR is **3** in `Elderwyld/Shephards Flock/Statblocks and Tokens/DustWalker.md`."}
========================================================================

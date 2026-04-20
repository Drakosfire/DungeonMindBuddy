<!-- benchmark_artifact: npc_voice_planner | iso_utc: 2026-04-17T01:26:24Z | scenario: torbin_factual_recruited_kid | model: gpt-5.4-mini | gates: FAIL | turns: 1 | primary: npc_voice--torbin_factual_recruited_kid--gpt-5.4-mini--FAIL--1turn--run008--20260417T012624Z.md -->

========================================================================
NPC VOICE PLANNER — REVIEW
========================================================================
scenario_id:      npc_voice_torbin_factual_recruited_kid
scenario_key:     torbin_factual_recruited_kid
model_id:         gpt-5.4-mini
gates_passed:     False
review_mode:      summary
corpus_fprint:    52196a8642f41500d73d1fdc98ca334a
corpus_dir:       /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown
hit_tool_limit:   False
tool_trace rows:  1

========================================================================
§ Prompt payload sizes (characters)
========================================================================
instructions:  {'chars': 16998, 'bytes': 18932, 'sha256_16': 'f785027e11c8b041'}
user_line:     {'chars': 69, 'bytes': 69, 'sha256_16': '69bf9d745aef29c3'}

========================================================================
§ Token usage (per responses.create completion)
========================================================================
  round[0] input_tokens=7146 output_tokens=53 cached_tokens=6656
  round[1] input_tokens=7278 output_tokens=46 cached_tokens=6656
  planner_estimated_cost_usd: 0.002278
  scenario_estimated_cost_usd: 0.002278

========================================================================
§ Statblock / working-context evidence (tool wire)
========================================================================
Evidence uses stored ``tool_trace`` rows: ``output_excerpt`` is the first 800 chars of each tool return (same bytes sent to the API in that round).

load_context_markdown: 0 calls — no explicit attach tool in trace; if the model only used ``read_corpus_file`` on a statblock, the file still entered that round's outputs, but nothing is labeled ``[context attached: …]``.

========================================================================
§ Clarification (tool + turn 0 prose)
========================================================================
Use this block to see whether the model surfaced clarification via tool calls and/or turn-0 prose.

propose_clarification tool: 1 call(s) in merged trace
  trace[0] question='Do you mean the recruited kid NPC from Campaign 2, or someone from the Mirathorn/Elderwyld side?'
            missing_slots=['entity', 'scope']

(Single-turn scenario: final answer is only under § Final LLM answer below.)
========================================================================
§ Final LLM answer
========================================================================
{"user_intent":"factual_lookup","message":"Do you mean the recruited kid NPC from Campaign 2, or someone from the Mirathorn/Elderwyld side?"}
========================================================================
GATE VIOLATIONS:
final: [planner_live_eval:npc_voice_torbin_factual_recruited_kid] final: output_text must contain one of ['Torbin', 'torbin']
final: [planner_live_eval:npc_voice_torbin_factual_recruited_kid] final: tool_trace must include 'read_corpus_file'; got ['propose_clarification']
final: [planner_live_eval:npc_voice_torbin_factual_recruited_kid] final: read_corpus_paths_must_include set but no read_corpus_file / load_context_markdown paths in tool_trace

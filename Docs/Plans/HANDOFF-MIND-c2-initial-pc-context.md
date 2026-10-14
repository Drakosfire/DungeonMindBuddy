# MIND: verified initial C2 PC context

Status: ACTIVE. Owner: PRIME, solo implementation.
Pinned base: `9083530dae7cfadb4578a4727dab09478e4b5db2`.
Topology: parallel-independent of held PR #1139 (`95511dcb`): no shared paths, dependency or runtime lease. Relevant open PRs inspected; no other steward work resumed.

## Outcome and evidence

Initialize C2's existing PC roster convention from Session 1 rather than Session 20. The first two C2 recaps name Baergrom, Bonogo, Caelynn, Ephanna, Karsemine and Stafl; each has a typed C2 PC hub. Existing numeric forward carry supplies standing PC identity context until the next explicit roster. This is identity/standing context, not proof of participation in every intervening session.

The registered C2S2 baseline had zero PC anchors, known entities and mentions, with a missing-roster warning, but reached reviewable. Actor prompts exclude PCs because they expect supplied anchors. Correct the actual input rather than add a generic validation gate or copy later companion membership backwards.

## Write lease

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json`
- `tests/test_c2_initial_pc_context.py`
- this handoff

Keep companion entries and existing later PC entries unchanged. No new runtime API, formats, provider calls, server changes or World publication. Settled Karsemine remains a PC; Ogonob is not a PC identity alias and Thrin is not backdated.

Verification: owning deterministic party→known-entity→source-mention path supplies six PCs for C2S2; no future companions; before-first-session remains empty. Existing roster/registry suites pass. Inspect exact cumulative diff and lint.
Carry through PR. PRIME authors this change; independent review required before merge, with no implicit agent dispatch during solo work. After acceptance, evaluate a fresh candidate package before publication. Original baseline source and run remain pinned to their original refs.

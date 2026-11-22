# Preserve manual summon mechanics in Build variants

ACTIVE under Alan’s Old Bath House implementation authorization. Serial slice on `codex/build-preserve-manual-summons`, based on `34cf026322645d55157c80052f9b6af0e9187bcf` in the isolated Combat checkout. Write scope is this handoff, `src/application_state/agent_conversation/native_completion.py`, and `tests/test_statblock_definition_validation.py`. Depends on merged variant witness and receipt support. No runtime, provider, or schema ownership change.

The hosted writer replaced a manual summon with a multiattack targeting a nonexistent self-contained rule. Preserve the original manual mechanic when the proposed single sequence cannot resolve and leave the rendered rule text intact. Preserve resolvable sequences and owner validation. Check positive and negative cases locally and reproduce the ordinary signed-in saveable review after operator rollout.

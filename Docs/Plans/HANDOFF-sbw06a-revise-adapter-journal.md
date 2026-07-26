# HANDOFF — SBW06a Buddy Exact Edited-Definition Revise Adapter + Durable Revise Journal

**Created:** 2026-07-26
**Repository:** `Drakosfire/DungeonMindBuddy`
**Workstream:** Threat + Statblock Authoring and Projection (`SBW`)
**Slice:** `SBW06a`
**Status:** IN PROGRESS — implementation on `feat/sbw06a-revise-adapter-journal`
**Normative contract:** `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md` §12
**Logical Buddy predecessor:** PR `#413`, merge `e9264610238ccf59a91d66fd3ea4e4d68cfcd3a4`, frozen contract head `b8877e342cb4ac9fce86b582b5354e65d4dc286c`
**External recovery-gate predecessor:** DungeonMindServer PR `#24`, merge `2c7d2566baa744f2b1a4667761775c1dec87a2d4`, reviewed head `1ad8de2baf0431c7ddb401cdd72389afc730519a`
**Buddy base SHA:** `5c19d433c9e103573ea6bd72ae1f34483862569f`
**Next slice:** `SBW06b` — attach one durable candidate ref with embedded `CandidateLineageV1` and perform the frozen ThreatDraft CAS/status transition

> Full dispatch text for this bite lives in the agent transcript / parent brief of 2026-07-26. This file is the in-repo status pointer; §12 of `HANDOFF-sbw06-candidate-revise-lineage.md` remains normative.

## Success claim (merge bar)

```text
exact edited source_definition
+ normalized revision instructions
+ one stable request_id
→ separate durable revise claim
→ durable claimed → dispatched_unknown write-ahead
→ same-key Server revise/replay
→ one exact candidate identity recorded
→ candidate stored through the existing cache boundary
→ operation remains pending ThreatDraft materialization (cache_stored_ref_pending)
```

Ordinary product revise success / `reconciled` remains false until SBW06b.

# REFERENCE — read back captured native Play references

Status: ACTIVE, serial PRIME repair under the current References closure goal.
Source base: 3ed6cf28f087e174c64401b045a41e4010507cd5; branch codex/play-reference-history in the existing buddy-context-loop checkout. No unmerged parent.

Ordinary live mixed-reference Play delivered a supported answer and an exact opening citation, but the subsequent saved-history read returned500. The base history DTO rejects authored references for Play; native Play receipts also fall through the Plan history projection branch. Preserve the original turn0746c2a4-820b-4c88-83b5-5103f08c3369, its answer, source/revision pins and private original failure witness. Do not replay inference to repair a read.

Adopt the existing Play history DTO and projector for native Play, and allow captured references on the already-supported Play surface. Keep existing World/provenance/execution/grounding validation and unsupported-surface refusal. No schema, migration, provider, ingestion, writer, source authority or compatibility path changes.

Exclusive writes:
- apps/live_control_server/models/agent_turn.py
- apps/live_control_server/routes/agent.py
- tests/test_authored_graph_references.py
- tests/test_play_authored_source_references.py
- tests/test_plan_jev_writer.py solely to check actual structured-output format instead of requiring the word JSON in user evidence
- this handoff
- HANDOFF-SURFACE-cross-surface-proposal-history.md solely to settle merged/delivered predecessor2359.

No current open PR overlaps these paths. Ingestion2360, Index/native-demo and CI lanes remain separate; ADVERSARY coordination stays off.

Verification: synthetic history DTO supported/unsupported/foreign-World cases; actual provider-free native Play factory persists and projects exact history in both correlation modes, including object/source mixed references; existing Play history owners; preserved exact live row replay. Retain original failures. Independent exact-head Bugbot and owning local backend contract before PRIME merge. No frontend changes or unnecessary frontend rerun.

Delivery boundary: running API is76bb8c4b38178158e9a94a4b00cf65773edbda87/schema147. Current main has unrelated writer experiments and a GE dependency update that this repair must not silently activate. Prepare a separately pinned candidate containing only this reviewed backend fix atop the running API revision; independently review both source identities and exact changed production blobs, qualify that candidate, and use the established protected API stop/start after identity/active-turn/read-only preflight. UI1517059 and both retained PostgreSQL stores remain intact. This is an immutable delivery-source pin, not a second runtime execution path.

Done for this slice: original saved turn reads successfully through lightweight/full history and both modes, the answer/citation and exact selections survive reload, prior conversation can be restored through ordinary controls, no additional inference or saved Run/page changes, and the source/merge/runtime revisions are explicit. Broader image generation remains pending its own approval/diagnosis.

Baseline qualification: unchanged3ed6cf28f reproduces the factory failure in the shared WriterWire fixture before history readback: it requires the word JSON inside input messages despite the actual structured JSON output format. Replace that incidental wording assertion with checks of the actual JSON-schema transport contract. Retain baseline and first-failure logs; no production writer change.

Qualification: 12/12 ordinary Play factory cases pass; captured original live row validates with unchanged answer SHA and two exact references; 17 CI/ownership guards pass. Broader owner comparison against unchanged3ed6cf28f: baseline195pass/29fail, repair208pass/21fail (five new passing tests and eight repaired stale-fixture failures; no new failures). The21 remaining failures are retained, not waived as whole-product success. Evidence: private play-history-owner-regression-{baseline,working}.log and comparison.json. Preliminary independent Bugbot review found no source defects; final exact-head and delivery review remain required.

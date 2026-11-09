# CI: restore closed Playable edit-codec V1 capture parity

Status: ACTIVE under coordinator's explicit codec product-repair assignment.
Owner: CI worker. Base fetched main f6e174e407ab83b4632160771412b77c09833ed0;
branch codex/ci-playable-v1-capture-parity; isolated ci-playable-v1-capture-parity.
Topology parallel-independent product repair, no unmerged behavior dependency on
CI2288/2298/2299 or graph2276. Open one scoped draft PR; merge separately authorized.
No ports/services/live databases used; reuse unchanged locked task dependencies.

## Ownership adoption before edits

Coordinator assigned narrow resolver ownership/transfer before product edits.
Latest resolver writer is merged1830/62749f; its named-table handoff is SETTLED.
Older selected-card913 is SETTLED. Older ACTIVE capture-roundtrip handoff belongs
to merged1822/cbb1c264 (merge04e1f9c2), and its stale implementation lease is settled
in this slice without inferring delivery. Checked94existingworktrees: no dirty
resolver/test overlap and no active named-table/playable-capture checkout. OpenPR
path inspection shows graph2276 owns localWorldSurface/canvas only, ADV2297 owns
provider runtime/types/test_surface_native_context only, no overlap. No external
agent outreach. Adopt the released resolver/test ownership into this bounded lane.

Exclusive expected writes:
- this handoff;
- Docs/Plans/HANDOFF-PLAN-playable-capture-roundtrip.md (old merged lease only);
- apps/live-control-ui/src/planSurface/agentEdit/planPlayableBodyTarget.ts;
- apps/live-control-ui/src/planSurface/agentEdit/planPlayableBodyTarget.test.ts;
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts.
No server, golden-vector, general parser/editor, graph-route, CI workflow,
classification/lockfile, authority/schema, database or live-data changes.

## Critiqued contract

Independent paired audit proves six expected-unavailable V1 vectors produce
frontend edit capture while server rejects both original/canonical drafts. Both
advertise plan-playable-body-markdown-v1; actual replace_playable_body admission
returns422playable_target_invalid. Server remains safely closed. Preserve its
contract and all original golden expectations/assertions/IDs, not a new codec.
General editor readability/save capability is broader than this edit codec.

Reject ordinary link marks anywhere in the draft, matching the server's whole-
Plan link guard. Reject hard breaks inside the selected
body, matching server canonical-body refusal; do not reject an outside-target
hard break just because it exists. Preserve inline code, typed Graph/document
references, named tables/captions, protected siblings/identities, exact accepted
body bytes/hashes, range versions and8000characterlimit. Keep ordinary web-link/
hard-break authoring usable; no global Markdown rollback or admission relaxation.

Verify all25unchanged shared vectors paired frontend/server, source/canonical
hashes, outside-target distinctions, actual Plan capture rejection before request
construction, accepted named-table/protected-structure controls, ordinary editor
roundtrip, type/build and independent exact-head review. No costly unchanged full
qualification rerun; existing required PR gates stay intact and must run. Record
dependency/proof in CI2298 without merging it or changing selector/graph holds.

## Author proof before exact-head review

Focused frontend4files245PASS (all originals retained,4newboundary/capture cases),
unchanged server29PASS; typecheck/productionbuildPASS. Exact-main archived product
with byte-identical new tests yields236PASS/9FAIL: six original mismatch vectors,
new outside-target link and two real capture rejection regressions. Outside-target
hard-break positive passes on both. Archived tests retain required pinned corpus
fixtures; initial missing-fixture setup diagnostic is preserved separately and
not counted as a product regression. Original six golden entries remain false;
all25vectors/server source unchanged. Existing assertions/test definitions are
unchanged and new cases append. No full legacy qualification rerun performed.

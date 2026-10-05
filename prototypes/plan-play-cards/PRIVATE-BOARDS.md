# Private full-adventure boards — development witness

The operator-authorized follow-up adds a separate `/boards.html` view on the assigned loopback port 5203. Existing Session 29 stays at `/`; its fixture, storage key, backups and immutable design-v1 stylesheet are unchanged. The new view imports the runtime stylesheet and adds only scoped layout rules. No production route, Graph, provider, OCR or GPU operation is introduced.

## Handling and runtime

Adventure-derived JSON, PDFs, images, assembly scripts, exact evidence references and interpretive manifests live in ignored `prototypes/plan-play-cards/.private/one-shots/`. They are not in committed `content.json`, screenshots or this public record. Do not run the old unrestricted static-directory server with private inputs present. Use:

```sh
python3 prototypes/plan-play-cards/private_server.py \
  --catalog prototypes/plan-play-cards/.private/one-shots/catalog.json --port 5203
```

The handler binds only 127.0.0.1, serves public prototype files plus explicitly registered private file URLs, and rejects directory/unselected-file paths. It does not expose a filesystem root. Real HTTP checks returned 200 for the selected catalog/PDF and 404 for hidden-directory and unselected-file requests. Synthetic tests exercise that owning route inventory and malformed route rejection.

## Coverage and review status

Two independently selectable full-adventure development datasets retain 19 and 6 OCR pages respectively: 114 and 135 evidence units. Following manual cross-page continuation joins, their boards contain 47 and 23 cards, including reference/back matter as well as playable moments. Every unit remains mapped to a GM/source card and every full Stage A page remains in Document view. Coverage is retention, not semantic correctness or playable-scene count.

The private reference manifests map cards/lenses, entities, mechanical references, assets, suggested options, navigation endpoints/conditions and candidate semantic relations to exact page/unit/line spans and source hashes. They record manual grouping, authored projection glue, cross-page rejoins, known OCR discrepancies, disclosure and external-rule gaps. Dataset pins include source plus interpreted card assembly; private receipt.json also pins board and manifest file hashes. Readback opens exact unit text and the source PDF page.

The records are **development gold candidates**, not frozen reviewed gold or untouched held-out evaluation. Exact Stage B heading inheritance was insufficient for interleaved statblocks, sidebars and encounter continuations. Limited PDF visual audits validated selected player-facing passages and exposed missing table cells / consequential OCR mistakes. Full independent source audit and operator task review remain pending. Existing COMPOSITOR evidence and prior treatments were read; no new provider treatment was executed.

## Interaction contract

- Grouped collapsible outline and search permit non-linear scene access. Conditional navigation exposes its condition and never prevents another route.
- Situation, Read aloud, Do now, GM only, Relevant and Missing reference show available source spans or explicitly authored/unresolved projections. Source OCR is visibly audit-pending; no GM text is automatically declared player-safe.
- Maps retain GM scope and exact image identity. Location/asset associations are navigation aids, not inferred spatial adjacency.
- Entity pills open source-local roles, candidate connections, linked scenes/statblock references and notes. They do not claim native Graph bindings or live encounter values.
- Plan lens overrides preserve original evidence; Play choices, unexpected notes, completion marks, shared writing and contextual notes remain a separate per-adventure, per-dataset state. Refresh retains selected scene/lens/mode. Full play backups include overrides and record source pin. No restore UI or server durability is claimed.

## Verification and review tasks

Passed source-reference/authority/link/resource validation tests, synthetic prep/play separation tests, private-server route tests, existing model tests, exact Session29 fixture verification and whitespace checks. Dataset audit retained all 249 units without missing references. Runtime CSS equals the immutable design-v1 copy.

Browser walkthroughs: selected the opening scene; jumped directly to a later scene; opened an explicitly source-backed read-aloud passage; read back its four exact spans/PDF page; opened the tactical map; switched adventures; opened a late scene in Play; wrote scene/shared notes and verified refresh persistence. Temporary test writing was removed through the UI. Original Session29 storage was not read or modified by the new code. Private screenshots remain outside Git.

Operator review should now challenge: a social/noncombat approach; a conditional escalation; a location/map lookup; a statblock discrepancy; an unexpected action and later note recovery; and full-source readback for every lens used. Request separate scores for usefulness, source fidelity, disclosure, branch preservation, mechanics readiness and writing/navigation effort. Visual polish cannot waive unresolved evidence. Candidate entity relations remain sparse; no complete discovered graph or automated compositor success is claimed.

Final verification: preparation override save and reset were exercised in the browser. Backup control was invoked, but the browser download-event wait timed out; an exported-file round trip is not claimed. Export serialization is covered by model checks; restore remains unresolved. A durable private mirror outside the temporary checkout retains both datasets, PDFs, selected images and receipt hashes. Assembly scripts are historical recipes; the pinned current snapshots include subsequent manual joins and corrections and are the recovery authority.

## Bounded disclosure/profile repair v2
Prior private snapshots are retained unchanged. New dataset pins hide absent lenses, move template/verification diagnostics into collapsed Source review, and remove generic instruction filler. Operators may write an absent lens explicitly. PDF physical9 was visually checked for outward description and separate conditional Mark/Torbin dialogue; Torbin introduction belongs to Torbin. No blanket GM-to-player promotion occurs. Torbin profile now includes source narration of family/activity and separately attributed testimony, fear and food stakes. Full-name exact corpus matching supplements both entity sets; unnamed seller identity, aliases, timing corroboration and complete biography remain unresolved.

A visible Recover previous writing control offers an explicit copy from the prior dataset. It first archives current state under a timestamped browser key, retains prior state untouched, and copies notes, decisions, edits and orphaned references without silent deletion. Old preparation overrides require source review. Tests prove preservation and copy isolation; browser checks verified the recovery offer, repaired home description and coherent Torbin profile. Export/restore remains unverified.

Outline repair: proposed navigation now separates arrival/hooks, exploration/approaches, conditional escalation, aftermath, people and reference material according to each adventure. Source-order Next/Previous links were removed from cards; Document retains original order. Existing cited conditional links remain, and Jove home links to the two NPC dialogue triggers. This is a navigation adaptation, not a canonical chronology or inferred spatial graph.

Sheep fidelity successor: `.private/sheep-successor-v1/` contains board, reference manifest and prototype-local derivative receipt; it references the immutable `sheep-f11be03c` parent rather than duplicating PDF/media/play/renderer snapshots. It is not a `capture_candidate.py` complete snapshot and remains `candidate_not_accepted`. No active catalog change or runtime transfer is part of this slice. Verify parent files and exact renderer Git bytes before relying on receipt evidence.

## Conks source-structure derivative candidate

The private `conks-successor-v1` derivative implements five independently reviewed findings and89 exact source spans from packagev2 `bf221249244946851f1f225b25cac0cdfd6e8b50676389651d590c8eee88f227`. Store/Wagon/Tree sensory candidates stay in GM material; Wagon biography is split with exact original ranges. Statblocks use escaped field/action hierarchy and paired six-column abilities. Original OCR is ranged before existing reviewed correction display; printed600-ft blindsight and Guardian39 remain unchanged. Source presentation conventions are available in collapsed review details. Stale diagnostics are corrected only in derivative metadata, not frozen sources.

Conks has its own complete transformation and coherent manifest verifier, with independent source-package review evidence and immutable parent/renderer inventories. Twelve rehashed invalid derivatives reject; Sheep's nine adversarial cases and storage recovery tests remain green. This is a private derivative receipt, not a full capture-candidate snapshot or active catalog switch. No server/browser/provider/native acceptance follows. Mapalpha/illustrated-PDF inventory, disclosure, rendered comparison and operator/full-gold acceptance remain held.

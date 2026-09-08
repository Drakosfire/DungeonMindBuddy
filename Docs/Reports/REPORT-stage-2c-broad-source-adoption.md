# REPORT — Stage 2C broad exact source adoption

**Created:** 2026-09-08  
**Capability:** adopt every exact recoverable C1/C2 source claim into durable APP-STATE `source.artifact` / `source.revision`  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2c-broad-source-adoption-v1.md`  
**Branch:** `dogfood-continuity/stage-2c-broad-source-adoption-v1`  
**Reviewed code head (Cycle 3 CODE PASS):** `310c2b839b7f4b623aec5671be4330733ce1b9be`  
**Review:** `5147030710` — CODE PASS / PR HOLD for live evidence  
**This report's commit is the next distinct head (Cycle 4 live evidence).**  
**Draft PR:** `#696`

DSN passwords and `.env` contents are omitted. Recap prose is omitted.

---

## Operator ruling

> If DungeonMind or the accepted historical Ingest ledger already gives us a source identity and expected digest, and we still possess exact matching bytes, adopt those bytes into durable APP-STATE. Missing material remains missing; conflicting material fails closed.

Cycle 1–3 closed the operator-contract blockers (artifact-wide scope preflight, stable fingerprint, mandatory World-head pin, multi-locator walk, unknown-vs-concrete scope). This report is the live apply/replay/recovery/product witness, not a merge claim. Stage 2 / STOP 2 remain OPEN. Stage 4 remains NOT DONE.

---

## Authority coordinates (sanitized)

| Field | Value |
| --- | --- |
| Repo HEAD at apply | `310c2b839b7f4b623aec5671be4330733ce1b9be` |
| Buddy APP-STATE | `dungeonbuddy_application_state` @ `127.0.0.1:54331` |
| Schema | `20260906_0006` at head |
| DungeonMind World | `dungeonmind_cutover_live` @ `127.0.0.1:54330` (read-only) |
| Product API / UI | already-running `127.0.0.1:8000` / `127.0.0.1:5173` against the durable DSN |
| Disposable tests | `127.0.0.1:54329`; never the live `54331` |
| No `down -v` | live named volume untouched |

World head observed before preview, before apply, after apply/replay, and after product dogfood:

```text
eldyrwild  rev:680c246047d67f9fe0293ee90526f670
```

Unchanged.

---

## §11A Preview

```text
ingest.run count                53
claims                          136
unique artifact+digest targets  89
CURRENT_EXACT                   1
ADOPTABLE_EXACT                 22
UNAVAILABLE_BYTES               8
AUTHORITY_METADATA_INCOMPLETE    0
UNSUPPORTED_MEDIA               58
blocking conflicts              0
blocked                         no
source_target_set_sha256        d9cf1648247bb7e297a10f7dbc76333fbf6b67b1ce43de4788bcc3d1dc9043b5
World head                      rev:680c246047d67f9fe0293ee90526f670
```

Classification by campaign (all 89 targets; unknown/world-owned counted as `none`):

| Campaign | CURRENT | ADOPTABLE | UNAVAILABLE | UNSUPPORTED |
| --- | ---: | ---: | ---: | ---: |
| longmont-c1 | 0 | 14 | 1 | 1 |
| longmont-c2 | 1 | 6 | 1 | 0 |
| none / World-owned / other ids | 0 | 2 | 6 | 57 |

Domain/prefix mix of the 22 `ADOPTABLE_EXACT` targets: 17 existing ingest recap artifacts, plus 5 World-referenced textual sources (`corpus:eldyrwild:session-22-recap`, `corpus:eldyrwild:session-23-recap`, `source:longmont-c2:session-24:raw-recap-placeholder`, `corpus:eldyrwild:mirathorn-city`, `corpus:eldyrwild:mireward-readme`).

---

## §11B Pre-write safety

Live `54331` fingerprint before any Stage 2C write matched the Stage 2B post-repopulation fingerprint. `source.*` was still the single C2S25 revision. `ingest.run` digest unchanged from Stage 2B.

```text
pre-write fingerprint           c1d17b77a8d2fe885ed88ed72615e2fb0b2c5f9ab2d21c7d8608145e870ba168
pre-write backup SHA-256        d2096edbcf670a95c068a0c00f02586fddaa8ef5940b073a71329464eaea053d
source.artifact / revision       1 / 1
ingest.run                      53  digest 1152dd828a50008c646a5a441a08e2216e8a5fdd6f6ddeec3973c0ecb96f5cd6
```

External custom-format dump stayed under gitignored `out/stage-2c/`. The live volume was not destroyed.

---

## §11C Apply

Apply used `--expected-set-sha256 d9cf1648247bb7e297a10f7dbc76333fbf6b67b1ce43de4788bcc3d1dc9043b5` and `--expected-world-head rev:680c246047d67f9fe0293ee90526f670`.

```text
applied                         yes
blocked                         no
newly_adopted                   22
CURRENT_EXACT / noop             1  (C2S25)
new_durable_identities          22
skipped                         66
blocking conflicts              0
source_target_set_sha256        d9cf1648247bb7e297a10f7dbc76333fbf6b67b1ce43de4788bcc3d1dc9043b5
ingest.run digest               1152dd828a50008c646a5a441a08e2216e8a5fdd6f6ddeec3973c0ecb96f5cd6  (unchanged)
```

Known historical UUID preserved exactly:

```text
8ed1e034-23c6-4295-b2ff-05d5cdd643a9
artifact:recap:longmont-c2:session-25:fd38b5915b32
fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
```

### Adopted target table

| Campaign | Session | Domain | source_artifact_id | content_sha256 | source_revision_id | identity |
| --- | --- | --- | --- | --- | --- | --- |
| longmont-c1 | session-1 | recap | `artifact:recap:longmont-c1:session-1` | `b01733e7c2a943ac8db29e338c4e57204db1148069f3050ad9bac9e484ba8284` | `2b6f3cd6-f902-41a6-b884-d9e5e0fbbb20` | new durable |
| longmont-c1 | session-2 | recap | `artifact:recap:longmont-c1:session-2` | `9f0e7dfa6bfcc47c60ea446d1f0ff0e6bf727c45c9e6e575eadba01c1ea513be` | `afc9667a-222c-4da1-8def-be6c7315ab73` | new durable |
| longmont-c1 | session-3 | recap | `artifact:recap:longmont-c1:session-3` | `4bf9af0ca38f99e41fee48df1b881c1094568a9d02baa1644b27e42bb65ed107` | `916433e8-d4b2-4b94-a15b-1ed26066d750` | new durable |
| longmont-c1 | session-4 | recap | `artifact:recap:longmont-c1:session-4` | `60854a0537bbd5d7a621c76c3837c1a91b11a7ab0e3269193069349df76cb8f3` | `ee5759f4-6462-4bd9-80dc-5a595267bdfa` | new durable |
| longmont-c1 | session-5 | recap | `artifact:recap:longmont-c1:session-5` | `857778650365589f24050e55fdc7d041f00d86dde00f0da8cdacdcaf1578c5b5` | `173ad773-35df-4450-83cf-97339f55c6a5` | new durable |
| longmont-c1 | session-6 | recap | `artifact:recap:longmont-c1:session-6` | `d5ea4c32d3072bb4263eceed78d5e45caef45df609a689c1d4fcd048116dbeda` | `8e76d8ea-77e2-4e06-8586-c33b4949421e` | new durable |
| longmont-c1 | session-7 | recap | `artifact:recap:longmont-c1:session-7` | `8443eb3113eb57236bcd303d21d60b332f659e72048d81a2e32e48fd31ebb471` | `944aa3b3-995c-4043-8553-ae1ef1668984` | new durable |
| longmont-c1 | session-8 | recap | `artifact:recap:longmont-c1:session-8` | `8463945d7548f8a7a31ea4d96d1d61b95a28830c57f2deead99627aac8271bc2` | `267f3161-55bc-4048-afc9-b02551d038cf` | new durable |
| longmont-c1 | session-9 | recap | `artifact:recap:longmont-c1:session-9` | `74b7fb39ee0915ebfa6957538d5f0a07ec7ad230e8b7c45accd5addf882bbc5b` | `e6d61ecf-17fd-42f3-b6c7-b795718ba210` | new durable |
| longmont-c1 | session-10 | recap | `artifact:recap:longmont-c1:session-10` | `04e6b145f64e4c2788f1afbb8a820b9be1222039471e343419bf247fbc6b96bf` | `6c86501b-d0fc-4e7c-9195-42856ecb962c` | new durable |
| longmont-c1 | session-11 | recap | `artifact:recap:longmont-c1:session-11` | `902326bb759b3411298eee461f4b800da2dcfab293a163b8c4f4ee8c2e75c186` | `2fe53fdc-f17c-4a15-aeb8-4d0e5356ea0c` | new durable |
| longmont-c1 | session-12 | recap | `artifact:recap:longmont-c1:session-12:7184000a8cfb` | `7184000a8cfbbd993e5e871b48d83fa274cd36d83f5e05a05cdc408b349ca5c9` | `303a99a0-0eb8-4b00-88e3-01d767ec6d4e` | new durable |
| longmont-c1 | session-13 | recap | `artifact:recap:longmont-c1:session-13:ca6e5c7c4af0` | `ca6e5c7c4af02183f1f7a8a2a9ac8525eb1f6b7aab74e04f7a54311dea615a21` | `523dccb9-41f7-4288-baba-2f96c5270fb6` | new durable |
| longmont-c1 | session-17 | recap | `artifact:recap:longmont-c1:session-17` | `90823bf0610beca9fee22df4806a318b1f892c3c194a434563f6f37250b0690f` | `0333c3b9-bc88-4874-bd80-9be2f8d933a0` | new durable |
| longmont-c2 | session-22 | recap | `corpus:eldyrwild:session-22-recap` | `06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083` | `b7690a60-4c8b-403b-a796-5eb5319eecff` | new durable |
| longmont-c2 | session-23 | recap | `corpus:eldyrwild:session-23-recap` | `77ba5030b5c89e8888e8a3d900fe3fc07b94313af81a7ad5f888eb663d4c7782` | `3805bef8-6d16-4c1a-bead-f225a942877d` | new durable |
| longmont-c2 | session-23 | recap | `artifact:recap:longmont-c2:session-23` | `aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `ffe51425-6a3d-4e21-9b52-b7a6bfe83c7f` | new durable |
| longmont-c2 | session-23 | recap | `artifact:recap:longmont-c2:session-23:aed38be1e2c2` | `aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `318089e3-337b-416a-9ed8-b1f22f6aef58` | new durable |
| longmont-c2 | session-24 | recap | `artifact:recap:longmont-c2:session-24` | `603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95` | `82f725d7-6216-4597-b1d8-2228094f6740` | new durable |
| longmont-c2 | session-24 | recap | `source:longmont-c2:session-24:raw-recap-placeholder` | `d800d442cd66c6c0984c5de6500aa8272378f8c7606205b5d8f71fd19c7f526a` | `f271b3b9-1d34-436a-b9cb-6e410ab43a1a` | new durable |
| longmont-c2 | session-25 | recap | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | `fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d` | `8ed1e034-23c6-4295-b2ff-05d5cdd643a9` | historical recovered |
| — | — | worldbuilding | `corpus:eldyrwild:mirathorn-city` | `70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342` | `7cdc643b-7a16-44a1-a86c-36c56c992ee2` | new durable |
| — | — | worldbuilding | `corpus:eldyrwild:mireward-readme` | `9a971a9bcc293dcd9f919d7ec578ccb5378c5325a8f67408fdea7ca59aab7250` | `d8fa9b9f-f003-42f2-a750-43e559ca422d` | new durable |

Two ingest identities for C2 Session 23 share digest `aed38be1…` and were persisted as two artifact rows (same bytes, distinct IDs). A third Session 23 World corpus identity has a different digest and is a separate revision.

---

## Skipped targets (non-blocking)

### `UNAVAILABLE_BYTES` (8)

| Identity | digest prefix | note |
| --- | --- | --- |
| `artifact:recap:longmont-c1:session-2` | `fba8abdeb3d9` | second digest under session-2; the other digest adopted |
| `artifact:recap:longmont-c2:session-23` | `b87f12495d66` | second digest under session-23; other exact bytes adopted |
| `threat-publication-operation:53be1ecf-3047-414d-929b-71b06bdd710c` | `37c8de50b4b9` | locator missing |
| `threat-publication-operation:b3e5d2c8-a538-4dd4-8642-b883ae39872b` | `34f48faebf01` | locator missing |
| `threat-publication-operation:ca9fff4d-92f4-45ed-bb02-672b3b175e34` | `b79d8cd54984` | locator missing |
| `threat-publication-resolution:916419bc-57b7-4ae8-a26c-a001b18f4453` | `37c8de50b4b9` | locator missing |
| `threat-publication-resolution:9e5b5881-9313-4a07-9c1e-a18fed6791ca` | `34f48faebf01` | locator missing |
| `threat-publication-resolution:c05f202f-2f94-4902-88a4-902bc9f91066` | `b79d8cd54984` | locator missing |

### `UNSUPPORTED_MEDIA` (58)

Not UTF-8 Markdown. Families:

```text
graph-native:*                  53
threat-publication-operation    2
threat-publication-resolution   2
artifact:party-registry:*       1
```

Identities (no payload dump):

```text
artifact:party-registry:longmont-c1
graph-native:eldyrwild-c2-initial-v1:003-questionable-company-roster
graph-native:eldyrwild-c2-initial-v1:006-tripod-null-calf-threat-prep
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u001
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u002
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u003
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u004
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u005
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u006
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u007
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u008
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u009
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u010
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u011
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u012
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u013
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u014
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u015
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u016
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u017
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u018
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u019
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u020
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u021
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u022
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u023
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u024
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u025
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u026
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u027
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u028
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u029
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u030
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u031
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u032
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u033
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u034
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u035
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u036
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u037
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u038
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u039
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u040
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u041
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u042
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u043
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u043:atomics
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u044
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u045
graph-native:eldyrwild-correction:eldyrwild-relationship-semantic-closure-v1:u046
graph-native:eldyrwild-correction:lysandra-threat-direction-v1
graph-native:eldyrwild-correction:session24-cube-karsemine-false-location-v1
graph-native:eldyrwild-correction:session24-lysandra-caelynn-false-leads-v1
graph-native:eldyrwild-correction:session25-ephanna-thrin-false-hires-v1
threat-publication-operation:63fa9cf3-f9ba-44de-8a4c-e0401406f63d
threat-publication-operation:f1957a81-978c-4b01-ba45-140a0748c4ec
threat-publication-resolution:3fc80747-cc91-4002-b493-abce1a7a93bd
threat-publication-resolution:b047837d-d61f-4357-b260-58a55f6ad886
```

These remain skipped on purpose. Stage 2C does not coerce JSON/graph-native/threat-publication payloads into Markdown.

### Blocking conflicts

None at accepted apply.

---

## §11D Replay

Immediate second `--apply` with the same pins:

```text
newly_adopted                   0
noop / CURRENT_EXACT            23
new_durable_identities          0
source revision count           23  (unchanged)
source_target_set_sha256        d9cf1648247bb7e297a10f7dbc76333fbf6b67b1ce43de4788bcc3d1dc9043b5
World head                      rev:680c246047d67f9fe0293ee90526f670
```

`ADOPTABLE_EXACT → CURRENT_EXACT` did not change the operator pin.

---

## APP-STATE fingerprint before/after

```text
pre                             c1d17b77a8d2fe885ed88ed72615e2fb0b2c5f9ab2d21c7d8608145e870ba168
post                            4592d8e5ec76c9583259c472af7c3a669d1cf6f2762b3154d35eb9969bedfea1
source.artifact                  1 → 23
source.revision                  1 → 23
ingest.run                      53 / digest 1152dd828a50008c646a5a441a08e2216e8a5fdd6f6ddeec3973c0ecb96f5cd6 unchanged
content.* / play.*               unchanged row counts
```

---

## §12 Recovery proof

No live `down -v`. Post-apply external dump of `54331`, restore into clean `dungeonbuddy_application_state_stage2c_witness` on the same durable server, then drop the witness.

```text
post-apply backup SHA-256       17403a2bcc93b52d80f1b25df5e27af5f918fa99f91ac02ab595c820fd21891b
expected fingerprint            4592d8e5ec76c9583259c472af7c3a669d1cf6f2762b3154d35eb9969bedfea1
restore READY                   true
restored fingerprint            4592d8e5ec76c9583259c472af7c3a669d1cf6f2762b3154d35eb9969bedfea1
mismatches                      none
source.revision rows             23 live == 23 witness
C2S25 UUID                      8ed1e034-23c6-4295-b2ff-05d5cdd643a9 on both
C1S10 UUID                      6c86501b-d0fc-4e7c-9195-42856ecb962c on both
C1S1 UUID                       2b6f3cd6-f902-41a6-b884-d9e5e0fbbb20 on both
```

---

## §11E / §11F Product and no-checkout witnesses

Empty repo root `/tmp/stage-2c-empty-root` (no corpus files) plus the already-running API on `:8000` / UI on `:5173`. Inspection `sourceUri` is `None` in every case — runtime reads APP-STATE, not checkout locators.

| Witness | Inspection | source_revision_id | graph | notes |
| --- | --- | --- | --- | --- |
| C2S25 | `available`, digest `sha256:fd38b5915b32…`, 7024 chars | `8ed1e034-23c6-4295-b2ff-05d5cdd643a9` | `rev:680c246047d67f9fe0293ee90526f670` `isHead=true` | Orik mention `node:orik` present; inspect run `…T182312Z`; library exact-run `…T005650Z` |
| C1S10 | `available`, digest `sha256:04e6b145f64e…`, 3445 chars | `6c86501b-d0fc-4e7c-9195-42856ecb962c` | same head | previously catalog-only |
| C2S23 | `available`, digest `sha256:aed38be1e2c2…`, 9722 chars | `318089e3-337b-416a-9ed8-b1f22f6aef58` | same head | previously catalog-only; Orik mention present |
| C1S1 | `available`, digest `sha256:b01733e7c2a9…`, 3130 chars | `2b6f3cd6-f902-41a6-b884-d9e5e0fbbb20` | same head | additional C1 |
| C2S24 | `available`, digest `sha256:603c1590da3a…`, 8904 chars | `82f725d7-6216-4597-b1d8-2228094f6740` | same head | additional C2 |

Live catalog `GET /api/live/graph-preview/extraction-runs` still returns 53 runs.

Object retrieval `POST /api/live/world-graph/retrieval/object` at the same head, `outcome=enough`, `isHead=true`:

```text
node:orik                                              C2S25
loc:last_warehouse                                      C1S10
event:longmont-c2:session-23:mireward-gate-battle        C2S23
```

Assembled Graph Review (`127.0.0.1:5173/ingest?session=session-10&campaign=longmont-c1`) loaded exact run `graph-ingest:longmont-c1:session-10:20260722T023135Z`, bound `artifact:recap:longmont-c1:session-10`, showed World `eldyrwild` graph `rev:680c246047d67f9fe0293ee90526f670`, and rendered the Historical recap article from APP-STATE with mention pills. Recap prose is not copied here.

The chrome still warns `Projection campaign does not match requested campaign longmont-c2` while viewing C1; that is existing shell default noise, not a source-adoption miss.

---

## Automated evidence (Cycle 3 code head, still green)

```text
uv run pytest -q \
  tests/product_continuity/test_source_adoption_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_world_projection.py
→ 41 passed
ruff check (leased Python paths) → All checks passed
```

Tests used disposable PostgreSQL on `54329`, not live `54331`.

---

## Explicit still-missing / still-false

- Stage 2 / STOP 2 remain OPEN (human STOP after merge).
- Stage 4 presentation remains NOT DONE.
- 8 `UNAVAILABLE_BYTES` identities (second recap digests + threat-publication locators).
- 58 `UNSUPPORTED_MEDIA` graph-native / threat-publication / party-registry claims.
- Candidate graph / span / provenance-index durability.
- Build recovery.
- Validated ingest runs are still inspect-only / not REVIEWABLE (pre-existing lifecycle; not mutated).
- Shell “projection campaign does not match longmont-c2” chrome while viewing C1.

This slice did not write DungeonMind, advance the World head, re-ingest, or change ingest run status.

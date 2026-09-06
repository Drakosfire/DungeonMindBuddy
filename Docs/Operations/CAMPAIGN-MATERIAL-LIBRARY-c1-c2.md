# CAMPAIGN MATERIAL LIBRARY — Longmont C1 / C2

```text
Status: ACTIVE TRANSITIONAL RECOVERY LIBRARY

Purpose:
Keep a durable human-readable locator for existing C1/C2 material until
APP-STATE + durable artifact storage + remote hosting + backup/redundancy
make this ledger unnecessary.

This file is not product authority and does not authorize reconstruction
or mutation. It records where exact material currently survives.
```

**Surveyed:** 2026-09-06  
**Product `main`:** `678e9c276ad58505c53ce61d5a659ea8c792ca31`  
**APP-STATE:** `dungeonbuddy_application_state` @ `127.0.0.1:54329`, schema `20260902_0005` (`LIVE-READ`)  
**Ingest identity digest (sorted `run_id` SHA-256):** `59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1`

Root aliases (no home-directory paths):

| Alias | Meaning |
| --- | --- |
| `current-main` | This survey checkout of current `main` |
| `primary-checkout` | DFC-1 historical root `DungeonMindBuddy` |
| `of-conks` | DFC-1 historical root `DungeonMindBuddy-of-conks-end-to-end` (UI/design evidence only; not target corpus) |
| `stewardship-si6` | DFC-1 historical root `DungeonMindBuddy-stewardship-finish-si` |
| `leftover-app-state` | Configured local PostgreSQL `dungeonbuddy_application_state` |

Do not enumerate every World graph node here. World availability is in `REPORT-c1-c2-demo-readiness.md`.

---

## 1. Recap / source prose (git-tracked)

Canonical normalized recaps for the dogfood sessions. Titles are filenames, not product authority.

| Campaign | Session | Material type | Human title/description | Stable ID | Current product authority | Root | Exact relative path | Git-tracked / DB / local-only | Owning surface | Visible in product? | Openable? | Interaction level | Redundancy posture | Evidence provenance | Known blocker / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | session-10 | recap/source | Thraxx and the Last Warehouse | `artifact:recap:longmont-c1:session-10` (on adopted runs) | Git-tracked file; SourceArtifact id on ingest.run | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 10 - Thraxx and the Last Warehouse.md` | Git-tracked | Ingest | Catalog-visible session; prose not rendered after Load | File exists; Graph Review does not show it | CATALOG_ONLY | Git + leftover ingest.run pointer | `LIVE-READ` | Exact-review resolver rejects `validated` |
| C2 | session-23 | recap/source | Mireward Gate Battle | `artifact:recap:longmont-c2:session-23` | Git-tracked file; SourceArtifact id on ingest.run | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | Git-tracked | Ingest | Catalog-visible; prose not rendered after Load | File exists; Graph Review does not show it | CATALOG_ONLY | Git + leftover ingest.run pointer | `LIVE-READ` | Same resolver dead-end; gold fixture expected in picker |
| C2 | session-25 | recap/source | Mireward Gate Battle II | `artifact:recap:longmont-c2:session-25:fd38b5915b32` (one run) | Git-tracked file; SourceArtifact id on ingest.run | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | Git-tracked | Ingest | Catalog-visible; prose not rendered after Load | File exists on `current-main` | CATALOG_ONLY | Git + leftover ingest.run pointer | `LIVE-READ` | Known current example of validated history dead-end |
| C1 | session-1 | recap/source | Stonebridge and Glowkindle Rats (additional rich-interaction session; gold expected) | several ingest.run SourceArtifact ids | Git-tracked file | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` | Git-tracked | Ingest | Session tab + gold expected label | File exists | CATALOG_ONLY | Git | `LIVE-READ` | Four catalog runs; picker shows history, not reviewable |

Many additional C1/C2 recaps exist under the same `Session Recaps/` tree (canonical, `_normalized`, `_breadcrumbed`, `_archive`). They are git-tracked on `current-main`. This library does not list every archive copy. Absence from the Ingest catalog means **not adopted as an ExtractionRun**, not `MISSING`.

---

## 2. Ingest runs — recovery ledger (APP-STATE + exact artifact locators)

Leftover APP-STATE holds **53** `ingest.run` rows. Status mix: `validated=36`, `prepared=17`, `reviewable=0`.
Component URI + SHA-256 below are **APP-STATE claims** (`LIVE-READ`); path existence was checked on `primary-checkout` and `current-main`.
**32 / 53** runs have a complete review bundle (`source_artifact` + `source_span_index` + `candidate_graph`) on `primary-checkout`.
Paths are **not** derivable from `run_id` alone (Session 25 uses run stamp `20260808T005650Z` but artifact dir `20260808T005534Z`).

### 2.1 Canonical full-entry example — C2 Session 25

| Field | Value |
| --- | --- |
| Campaign | `longmont-c2` |
| Session | `session-25` |
| Material type | `Ingest run + review artifact bundle` |
| Human title | Mireward Gate Battle II |
| Stable run ID | `graph-ingest:longmont-c2:session-25:20260808T005650Z` |
| SourceArtifact ID | `artifact:recap:longmont-c2:session-25:fd38b5915b32` |
| Lifecycle status | `validated` |
| Current product authority | APP-STATE PostgreSQL (`leftover-app-state`) for run metadata |
| Owning surface | Ingest |
| Product state | `CATALOG_ONLY` |
| Visible in product? | Yes |
| Recap readable in product? | No |
| Reviewable/promotable? | No |
| Exact recap path | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` |
| Recap storage | Git-tracked |
| Recap SHA-256 | sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d |
| Recap bytes location | primary-checkout |
| Candidate graph path | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/candidate_graph.json` |
| Candidate graph SHA-256 | sha256:83d6675b7a1700790a749277cdf6cc18e41e911987d5a9522410358879d0d203 |
| Candidate graph location | primary-checkout |
| Source span index path | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/source_span_index.json` |
| Source span SHA-256 | sha256:94a7ba5770846f63ccb83485249a786ba7f198762e57af88ef50df702e7372d9 |
| Source span location | primary-checkout |
| Validation report path | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/candidate_validation_report.json` |
| Validation report SHA-256 | sha256:1f1107417fa73384026e000f7822191c5765da0a7512449f8ba84611e3cd47f2 |
| Validation report location | primary-checkout |
| Provenance index path | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/provenance_index.json` |
| Provenance SHA-256 | — |
| Provenance location | primary-checkout |
| Review bundle complete on `primary-checkout`? | Yes |
| Exact bytes in `current-main` checkout? | No |
| Redundancy | Poor — local untracked `out/` (+ git recap when under `corpus/`) |
| Evidence | `LIVE-READ` APP-STATE component claims + path existence on `primary-checkout` |
| Primary blocker | Historical inspection coupled to `reviewable`/promotion resolver |
| Recovery action later | Adopt digest-matching artifact bytes into durable product storage; do not re-ingest |


### 2.2 Dogfood representative full entries

#### `graph-ingest:longmont-c1:session-10:20260722T023135Z`

| Field | Value |
| --- | --- |
| Campaign | `longmont-c1` |
| Session | `session-10` |
| Material type | `Ingest run + review artifact bundle` |
| Human title | Thraxx and the Last Warehouse |
| Stable run ID | `graph-ingest:longmont-c1:session-10:20260722T023135Z` |
| SourceArtifact ID | `artifact:recap:longmont-c1:session-10` |
| Lifecycle status | `validated` |
| Current product authority | APP-STATE PostgreSQL (`leftover-app-state`) for run metadata |
| Owning surface | Ingest |
| Product state | `CATALOG_ONLY` |
| Visible in product? | Yes |
| Recap readable in product? | No |
| Reviewable/promotable? | No |
| Exact recap path | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 10 - Thraxx and the Last Warehouse.md` |
| Recap storage | Git-tracked |
| Recap SHA-256 | sha256:04e6b145f64e4c2788f1afbb8a820b9be1222039471e343419bf247fbc6b96bf |
| Recap bytes location | primary-checkout |
| Candidate graph path | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/candidate_graph.json` |
| Candidate graph SHA-256 | sha256:cbc8302397a33907c7741e6189dd21ee63c408afadf25b62996c6537f87a99bf |
| Candidate graph location | primary-checkout |
| Source span index path | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/source_span_index.json` |
| Source span SHA-256 | sha256:ee99c6a6ff9f21c12fc85b1aeeea3649550276ae8384281a4d6309229e9596d7 |
| Source span location | primary-checkout |
| Validation report path | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/candidate_validation_report.json` |
| Validation report SHA-256 | sha256:a770a0e1080ef66cfcc6313083ec7c1f4852d6a21990f1f25c94c211011288e8 |
| Validation report location | primary-checkout |
| Provenance index path | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/provenance_index.json` |
| Provenance SHA-256 | sha256:3b053859df446e64ef31809985e7eec51fc61acdaec0e8eefc416102bdcb364e |
| Provenance location | primary-checkout |
| Review bundle complete on `primary-checkout`? | Yes |
| Exact bytes in `current-main` checkout? | No |
| Redundancy | Poor — local untracked `out/` (+ git recap when under `corpus/`) |
| Evidence | `LIVE-READ` APP-STATE component claims + path existence on `primary-checkout` |
| Primary blocker | Historical inspection coupled to `reviewable`/promotion resolver |
| Recovery action later | Adopt digest-matching artifact bytes into durable product storage; do not re-ingest |


#### `graph-ingest:longmont-c2:session-23:20260629T040857Z`

| Field | Value |
| --- | --- |
| Campaign | `longmont-c2` |
| Session | `session-23` |
| Material type | `Ingest run + review artifact bundle` |
| Human title | Mireward Gate Battle |
| Stable run ID | `graph-ingest:longmont-c2:session-23:20260629T040857Z` |
| SourceArtifact ID | `artifact:recap:longmont-c2:session-23` |
| Lifecycle status | `validated` |
| Current product authority | APP-STATE PostgreSQL (`leftover-app-state`) for run metadata |
| Owning surface | Ingest |
| Product state | `CATALOG_ONLY` |
| Visible in product? | Yes |
| Recap readable in product? | No |
| Reviewable/promotable? | No |
| Exact recap path | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Session-23 Mireward Gate Battle.md` |
| Recap storage | Git-tracked |
| Recap SHA-256 | sha256:b87f12495d66ead07940f9c06282d12e97c2f396e94e701dfa65d0f55ceff77d |
| Recap bytes location | missing |
| Candidate graph path | `out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/candidate_graph.json` |
| Candidate graph SHA-256 | sha256:a00c64db0b67878c57b076e52d7653f04f9fb16c386088206f2e70ea60853f1d |
| Candidate graph location | primary-checkout |
| Source span index path | `out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/source_span_index.json` |
| Source span SHA-256 | sha256:f60fb3e6b85d7397ecac10bd15408fc73b263983880d59bc154634528ee43fd8 |
| Source span location | primary-checkout |
| Validation report path | `out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/candidate_validation_report.json` |
| Validation report SHA-256 | sha256:6ac42fd62b3ba08c66d0829bcccdc014c3673e558ae4306214dc2c2cb4be1d4c |
| Validation report location | primary-checkout |
| Provenance index path | `out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/provenance_index.json` |
| Provenance SHA-256 | sha256:783606dd09437d931ce6a68182cf6e4e6c34380edb98c3b735eb6b4457f6058f |
| Provenance location | primary-checkout |
| Review bundle complete on `primary-checkout`? | No |
| Exact bytes in `current-main` checkout? | No |
| Redundancy | Poor — local untracked `out/` (+ git recap when under `corpus/`) |
| Evidence | `LIVE-READ` APP-STATE component claims + path existence on `primary-checkout` |
| Primary blocker | Historical inspection coupled to `reviewable`/promotion resolver |
| Recovery action later | Adopt digest-matching artifact bytes into durable product storage; do not re-ingest |


#### `graph-ingest:longmont-c1:session-1:20260701T185713Z`

| Field | Value |
| --- | --- |
| Campaign | `longmont-c1` |
| Session | `session-1` |
| Material type | `Ingest run + review artifact bundle` |
| Human title | Stonebridge and Glowkindle Rats |
| Stable run ID | `graph-ingest:longmont-c1:session-1:20260701T185713Z` |
| SourceArtifact ID | `artifact:recap:longmont-c1:session-1` |
| Lifecycle status | `validated` |
| Current product authority | APP-STATE PostgreSQL (`leftover-app-state`) for run metadata |
| Owning surface | Ingest |
| Product state | `CATALOG_ONLY` |
| Visible in product? | Yes |
| Recap readable in product? | No |
| Reviewable/promotable? | No |
| Exact recap path | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` |
| Recap storage | Git-tracked |
| Recap SHA-256 | sha256:b01733e7c2a943ac8db29e338c4e57204db1148069f3050ad9bac9e484ba8284 |
| Recap bytes location | primary-checkout |
| Candidate graph path | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/candidate_graph.json` |
| Candidate graph SHA-256 | — |
| Candidate graph location | primary-checkout |
| Source span index path | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/source_span_index.json` |
| Source span SHA-256 | — |
| Source span location | primary-checkout |
| Validation report path | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/candidate_validation_report.json` |
| Validation report SHA-256 | — |
| Validation report location | primary-checkout |
| Provenance index path | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/provenance_index.json` |
| Provenance SHA-256 | — |
| Provenance location | primary-checkout |
| Review bundle complete on `primary-checkout`? | Yes |
| Exact bytes in `current-main` checkout? | No |
| Redundancy | Poor — local untracked `out/` (+ git recap when under `corpus/`) |
| Evidence | `LIVE-READ` APP-STATE component claims + path existence on `primary-checkout` |
| Primary blocker | Historical inspection coupled to `reviewable`/promotion resolver |
| Recovery action later | Adopt digest-matching artifact bytes into durable product storage; do not re-ingest |


### 2.3 Complete review bundles (`primary-checkout`) — 32 runs

| Stable run ID | Campaign | Session | Status | SourceArtifact ID | Recap path | Recap SHA-256 | Span path | Span SHA-256 | Candidate path | Candidate SHA-256 | Validation path | Validation SHA-256 | Provenance path | Provenance SHA-256 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `graph-ingest:longmont-c1:session-1:20260701T185713Z` | `longmont-c1` | `session-1` | `validated` | `artifact:recap:longmont-c1:session-1` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` | `sha256:b01733e7c2a943ac8db29e338c4e57204db1148069f3050ad9bac9e484ba8284` | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/source_span_index.json` | `—` | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/candidate_graph.json` | `—` | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/candidate_validation_report.json` | `—` | `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c1:session-1:20260701T204409Z` | `longmont-c1` | `session-1` | `validated` | `artifact:recap:longmont-c1:session-1` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` | `sha256:b01733e7c2a943ac8db29e338c4e57204db1148069f3050ad9bac9e484ba8284` | `out/graph_memory/runs/longmont-c1/session-1/20260701T204317Z/source_span_index.json` | `sha256:fa8295265d57365c812569753ed107dd1bd48426a04f41190a4eb05ee3a21adc` | `out/graph_memory/runs/longmont-c1/session-1/20260701T204317Z/candidate_graph.json` | `sha256:45835e42521154e3d34435fa6091db2825402f1d09a851e2b099bd154c305cc6` | `out/graph_memory/runs/longmont-c1/session-1/20260701T204317Z/candidate_validation_report.json` | `sha256:95cebaa29d2cf0d11428413e6aa6c2335708e4e7f5031721b1ec8e57b3507e80` | `out/graph_memory/runs/longmont-c1/session-1/20260701T204317Z/provenance_index.json` | `sha256:4650adba367dcc0775e57204b1e59d932ac9199f5b53e967e1dfed639d5c39bc` |
| `graph-ingest:longmont-c1:session-1:20260701T215257Z` | `longmont-c1` | `session-1` | `validated` | `artifact:recap:longmont-c1:session-1` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` | `sha256:b01733e7c2a943ac8db29e338c4e57204db1148069f3050ad9bac9e484ba8284` | `out/graph_memory/runs/longmont-c1/session-1/20260701T215207Z/source_span_index.json` | `sha256:fa8295265d57365c812569753ed107dd1bd48426a04f41190a4eb05ee3a21adc` | `out/graph_memory/runs/longmont-c1/session-1/20260701T215207Z/candidate_graph.json` | `sha256:29397f268a7cb6151611af7ac3f5c751c75f12381aefc533239dc5f38861b35e` | `out/graph_memory/runs/longmont-c1/session-1/20260701T215207Z/candidate_validation_report.json` | `sha256:ab19c1ad6f8a04f661c39c9f917cc8fdb831785c18192c8a7b2afbdc53ce642c` | `out/graph_memory/runs/longmont-c1/session-1/20260701T215207Z/provenance_index.json` | `sha256:ebcdc827ad7f1a274b710d02f31cc6f8cc42a5e287fa02a44169afe4a6da0354` |
| `graph-ingest:longmont-c1:session-10:20260722T023135Z` | `longmont-c1` | `session-10` | `validated` | `artifact:recap:longmont-c1:session-10` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 10 - Thraxx and the Last Warehouse.md` | `sha256:04e6b145f64e4c2788f1afbb8a820b9be1222039471e343419bf247fbc6b96bf` | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/source_span_index.json` | `sha256:ee99c6a6ff9f21c12fc85b1aeeea3649550276ae8384281a4d6309229e9596d7` | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/candidate_graph.json` | `sha256:cbc8302397a33907c7741e6189dd21ee63c408afadf25b62996c6537f87a99bf` | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/candidate_validation_report.json` | `sha256:a770a0e1080ef66cfcc6313083ec7c1f4852d6a21990f1f25c94c211011288e8` | `out/graph_memory/runs/longmont-c1/session-10/20260722T023048Z/provenance_index.json` | `sha256:3b053859df446e64ef31809985e7eec51fc61acdaec0e8eefc416102bdcb364e` |
| `graph-ingest:longmont-c1:session-11:20260724T031946Z` | `longmont-c1` | `session-11` | `validated` | `artifact:recap:longmont-c1:session-11` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 11 - Midnight Politics.md` | `sha256:902326bb759b3411298eee461f4b800da2dcfab293a163b8c4f4ee8c2e75c186` | `out/graph_memory/runs/longmont-c1/session-11/20260724T031850Z/source_span_index.json` | `sha256:cfeca3674ccd1fab8cbe7e53ec78b8046921e5bbe0100fe4497e315756cb9166` | `out/graph_memory/runs/longmont-c1/session-11/20260724T031850Z/candidate_graph.json` | `sha256:a745c4a22a343955e00333d219b8ed8e00f921676318af27c98518f5b84d6cb3` | `out/graph_memory/runs/longmont-c1/session-11/20260724T031850Z/candidate_validation_report.json` | `sha256:83e5b8b04e20d3ff27e43765033b71c6ed4bc43f6817f4b43cadac3ee7224cbc` | `out/graph_memory/runs/longmont-c1/session-11/20260724T031850Z/provenance_index.json` | `sha256:191a0c442afb1aa6c7add7c5da667e7c1aef1742fce4fed4e3d2371e59ae2d64` |
| `graph-ingest:longmont-c1:session-12:20260727T180223Z` | `longmont-c1` | `session-12` | `validated` | `artifact:recap:longmont-c1:session-12:7184000a8cfb` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 12 - The Persistent Bugbear.md` | `sha256:7184000a8cfbbd993e5e871b48d83fa274cd36d83f5e05a05cdc408b349ca5c9` | `out/graph_memory/runs/longmont-c1/session-12/20260727T180121Z/source_span_index.json` | `sha256:4a30a019f3362784dca70080c252a082257390e8e15ff39070fc9f034963c675` | `out/graph_memory/runs/longmont-c1/session-12/20260727T180121Z/candidate_graph.json` | `sha256:f6bf5516df6c4aedcad7544fea8305e8812b4ba5458bb28212a4f28ae22bea6a` | `out/graph_memory/runs/longmont-c1/session-12/20260727T180121Z/candidate_validation_report.json` | `sha256:fce31d45284f7c3dbcfab95d114f86196a5b331f1571756b046e237e00085265` | `out/graph_memory/runs/longmont-c1/session-12/20260727T180121Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c1:session-12:20260727T181654Z` | `longmont-c1` | `session-12` | `validated` | `artifact:recap:longmont-c1:session-12:7184000a8cfb` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 12 - The Persistent Bugbear.md` | `sha256:7184000a8cfbbd993e5e871b48d83fa274cd36d83f5e05a05cdc408b349ca5c9` | `out/graph_memory/runs/longmont-c1/session-12/20260727T181554Z/source_span_index.json` | `sha256:4a30a019f3362784dca70080c252a082257390e8e15ff39070fc9f034963c675` | `out/graph_memory/runs/longmont-c1/session-12/20260727T181554Z/candidate_graph.json` | `sha256:74b4801ab4e47cc8a7c18118559dcbbc563153bfb3fbd40ab7dbb2e3299f33eb` | `out/graph_memory/runs/longmont-c1/session-12/20260727T181554Z/candidate_validation_report.json` | `sha256:14add2d278639ce9a6be58c6073173658493921b1b93192fe3a194945ee9847c` | `out/graph_memory/runs/longmont-c1/session-12/20260727T181554Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c1:session-13:20260727T200538Z` | `longmont-c1` | `session-13` | `validated` | `artifact:recap:longmont-c1:session-13:ca6e5c7c4af0` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md` | `sha256:ca6e5c7c4af02183f1f7a8a2a9ac8525eb1f6b7aab74e04f7a54311dea615a21` | `out/graph_memory/runs/longmont-c1/session-13/20260727T200403Z/source_span_index.json` | `sha256:4804c779b4fc8022ddbb8545dc1ef1762a103197e51233f74bfde3efa354393d` | `out/graph_memory/runs/longmont-c1/session-13/20260727T200403Z/candidate_graph.json` | `sha256:7ab54d6fb8ae9cc92aa28b65512f094e530584899e0d5f6a47745f5acd3bc566` | `out/graph_memory/runs/longmont-c1/session-13/20260727T200403Z/candidate_validation_report.json` | `sha256:6d81c0efe89399c6a59d73765721b7a1cf99cc192b983d173816f7fea3bff03f` | `out/graph_memory/runs/longmont-c1/session-13/20260727T200403Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c1:session-17:20260724T031527Z` | `longmont-c1` | `session-17` | `validated` | `artifact:recap:longmont-c1:session-17` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 17 - Festival Aftermath Loose Ends.md` | `sha256:90823bf0610beca9fee22df4806a318b1f892c3c194a434563f6f37250b0690f` | `out/graph_memory/runs/longmont-c1/session-17/20260724T031429Z/source_span_index.json` | `sha256:a0cc5c26444f2856c001533537fe62c397e3ebb64068d249c7a0c454e8776edb` | `out/graph_memory/runs/longmont-c1/session-17/20260724T031429Z/candidate_graph.json` | `sha256:ba335a702f3751029fb17f57dd578dfec4df11b3bc61c607a69d67eebf5c4878` | `out/graph_memory/runs/longmont-c1/session-17/20260724T031429Z/candidate_validation_report.json` | `sha256:dfa49ab82b3b11d6b26e4504fd48d96c5bed67c3b191ed477b1de2d063629c26` | `out/graph_memory/runs/longmont-c1/session-17/20260724T031429Z/provenance_index.json` | `sha256:992c0762b0fe2612e6676247b8e26e38a4d3c2df9feac87385241a76849c7858` |
| `graph-ingest:longmont-c1:session-2:20260706T024026Z` | `longmont-c1` | `session-2` | `validated` | `artifact:recap:longmont-c1:session-2` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 02 - Finishing the Job.md` | `sha256:9f0e7dfa6bfcc47c60ea446d1f0ff0e6bf727c45c9e6e575eadba01c1ea513be` | `out/graph_memory/runs/longmont-c1/session-2/20260706T023949Z/source_span_index.json` | `sha256:9f08eb00251bdcd241a2b9f47eca6f05295c85c1417240e45c2f3db3c3834a06` | `out/graph_memory/runs/longmont-c1/session-2/20260706T023949Z/candidate_graph.json` | `sha256:b03d094476d7ec4cc708aee2940004bc97018d7541017b91d6de3e4e2216e84e` | `out/graph_memory/runs/longmont-c1/session-2/20260706T023949Z/candidate_validation_report.json` | `sha256:601747bc7ff4ff3ca06bc133f394aefaabc504fa42a3bd698fce95c6d5f3ed84` | `out/graph_memory/runs/longmont-c1/session-2/20260706T023949Z/provenance_index.json` | `sha256:f732a6d3086ee4442e7799a842f2de7f91062695463391214151a03c32382bd8` |
| `graph-ingest:longmont-c1:session-3:20260718T221836Z` | `longmont-c1` | `session-3` | `validated` | `artifact:recap:longmont-c1:session-3` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md` | `sha256:4bf9af0ca38f99e41fee48df1b881c1094568a9d02baa1644b27e42bb65ed107` | `out/graph_memory/runs/longmont-c1/session-3/20260718T221738Z/source_span_index.json` | `sha256:c634aae126de75871ef05572b9cc0ab5b4af3bbce8af005b42e8e21668792262` | `out/graph_memory/runs/longmont-c1/session-3/20260718T221738Z/candidate_graph.json` | `sha256:359e873f15b8750160770d269a4e7bd68632e16cbf32f1f334c4f245f1250015` | `out/graph_memory/runs/longmont-c1/session-3/20260718T221738Z/candidate_validation_report.json` | `sha256:55f0e0e0864ddc981ee0f7049af4869600c81a4cd90fd0713c3b28b3a1962afe` | `out/graph_memory/runs/longmont-c1/session-3/20260718T221738Z/provenance_index.json` | `sha256:f25f450d20445f3379ee8fd1098de5ffee3b3fded888934dff66c004bec80ec9` |
| `graph-ingest:longmont-c1:session-3:20260718T225145Z` | `longmont-c1` | `session-3` | `validated` | `artifact:recap:longmont-c1:session-3` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md` | `sha256:4bf9af0ca38f99e41fee48df1b881c1094568a9d02baa1644b27e42bb65ed107` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225044Z/source_span_index.json` | `sha256:c634aae126de75871ef05572b9cc0ab5b4af3bbce8af005b42e8e21668792262` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225044Z/candidate_graph.json` | `sha256:041d013dffcc974a4c6451900eaf963a4fe264abcb5c02fbdcaade31cc5b36c3` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225044Z/candidate_validation_report.json` | `sha256:9e7569b4246ebd307e19df5e7688676202ca2e4d68e27d02536030e6617a1d36` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225044Z/provenance_index.json` | `sha256:00fd56bf26dcf3670ea98f01337ba70a4d440c67db4e7700f13006eafc3b9ed5` |
| `graph-ingest:longmont-c1:session-3:20260718T225250Z` | `longmont-c1` | `session-3` | `validated` | `artifact:recap:longmont-c1:session-3` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md` | `sha256:4bf9af0ca38f99e41fee48df1b881c1094568a9d02baa1644b27e42bb65ed107` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225156Z/source_span_index.json` | `sha256:c634aae126de75871ef05572b9cc0ab5b4af3bbce8af005b42e8e21668792262` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225156Z/candidate_graph.json` | `sha256:d07e7ff696115d4a74b0973e66582293f6d5b135684be2176877f7bb97061839` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225156Z/candidate_validation_report.json` | `sha256:45da97b02ff4c77d2c5d0bcda3297a32ed8209bdedf538f9370119abacd4260c` | `out/graph_memory/runs/longmont-c1/session-3/20260718T225156Z/provenance_index.json` | `sha256:64c94799aa45674ea94853bfe3152e1a1122e870700bf0c30c6bd8b7d338a20d` |
| `graph-ingest:longmont-c1:session-4:20260719T154814Z` | `longmont-c1` | `session-4` | `validated` | `artifact:recap:longmont-c1:session-4` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 04 - The Grotesque Tree of Hempholm.md` | `sha256:60854a0537bbd5d7a621c76c3837c1a91b11a7ab0e3269193069349df76cb8f3` | `out/graph_memory/runs/longmont-c1/session-4/20260719T154730Z/source_span_index.json` | `sha256:4186f663ffb845fe287fbc38a5a9901ed0dffc271516e2f86c5e3d2993733aa5` | `out/graph_memory/runs/longmont-c1/session-4/20260719T154730Z/candidate_graph.json` | `sha256:0162725c4d9c94c6246741d96e1bf8ce6edfdb12c7539cc60153f06d8ad62240` | `out/graph_memory/runs/longmont-c1/session-4/20260719T154730Z/candidate_validation_report.json` | `sha256:d7236a7499f0d96bb8304df88dcb95ed245cc434ed938272420214652c4e013f` | `out/graph_memory/runs/longmont-c1/session-4/20260719T154730Z/provenance_index.json` | `sha256:f9325f94afaf1b156d8927d87481490906b99aa654d3940c4decd112610cfdff` |
| `graph-ingest:longmont-c1:session-5:20260719T201457Z` | `longmont-c1` | `session-5` | `validated` | `artifact:recap:longmont-c1:session-5` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 05 - Underneath Hempholm.md` | `sha256:857778650365589f24050e55fdc7d041f00d86dde00f0da8cdacdcaf1578c5b5` | `out/graph_memory/runs/longmont-c1/session-5/20260719T201346Z/source_span_index.json` | `sha256:146087431f656af9964b5240926e30f1afc1a4e56ed8e3a939eb41d83c25d626` | `out/graph_memory/runs/longmont-c1/session-5/20260719T201346Z/candidate_graph.json` | `sha256:d22b3a34a5c59159a8d29011097e88506f042cf407b62e53eb11d54029fafe64` | `out/graph_memory/runs/longmont-c1/session-5/20260719T201346Z/candidate_validation_report.json` | `sha256:20938b36e0bbbd28100c98d34a0294bb6c2f7abada0fd27db5a682db59b60be3` | `out/graph_memory/runs/longmont-c1/session-5/20260719T201346Z/provenance_index.json` | `sha256:e6312fbe45f5a8a50164fe60c38402390efccbcdca5bfe433341c79c99b6e539` |
| `graph-ingest:longmont-c1:session-6:20260719T230637Z` | `longmont-c1` | `session-6` | `validated` | `artifact:recap:longmont-c1:session-6` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 06 - The Road to Miraholm.md` | `sha256:d5ea4c32d3072bb4263eceed78d5e45caef45df609a689c1d4fcd048116dbeda` | `out/graph_memory/runs/longmont-c1/session-6/20260719T230553Z/source_span_index.json` | `sha256:b62cc87951c2949966e8badebe00b5feac5a79361b7fb7ac9aef44772d616747` | `out/graph_memory/runs/longmont-c1/session-6/20260719T230553Z/candidate_graph.json` | `sha256:ddf6904c18f12459569d372fefc1a17051dfe3d489c44d2b5d57c448ad0682f2` | `out/graph_memory/runs/longmont-c1/session-6/20260719T230553Z/candidate_validation_report.json` | `sha256:ccd2a0580becd673a24208a4cf3cd4750a64d2f004900c7116526e2d50117756` | `out/graph_memory/runs/longmont-c1/session-6/20260719T230553Z/provenance_index.json` | `sha256:5959df2cc223d11fa009f08b4abdbcd0e09c2302aeefd7fd4236e5aca5aa8932` |
| `graph-ingest:longmont-c1:session-7:20260721T141801Z` | `longmont-c1` | `session-7` | `validated` | `artifact:recap:longmont-c1:session-7` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 07 - Passing Mirathorn Gates.md` | `sha256:8443eb3113eb57236bcd303d21d60b332f659e72048d81a2e32e48fd31ebb471` | `out/graph_memory/runs/longmont-c1/session-7/20260721T141659Z/source_span_index.json` | `sha256:e59ba85b3c4a4e0ef421184872ef7874c42d11fec6b4f95c6486863d1898db50` | `out/graph_memory/runs/longmont-c1/session-7/20260721T141659Z/candidate_graph.json` | `sha256:d409537e433c2659ddac86965264bf14cbf6941d1528c01455681d3d94d9688b` | `out/graph_memory/runs/longmont-c1/session-7/20260721T141659Z/candidate_validation_report.json` | `sha256:007f20d41909b3724e0b5af3e672adf530aa667f6527e22d103ba05bd13b66e3` | `out/graph_memory/runs/longmont-c1/session-7/20260721T141659Z/provenance_index.json` | `sha256:f6cc704e1c2499622feb6abadef5ba9d80762b1a4872a5d0214b94d33ed50bd7` |
| `graph-ingest:longmont-c1:session-8:20260721T231322Z` | `longmont-c1` | `session-8` | `validated` | `artifact:recap:longmont-c1:session-8` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 08 - Captain Lysandra Quest.md` | `sha256:8463945d7548f8a7a31ea4d96d1d61b95a28830c57f2deead99627aac8271bc2` | `out/graph_memory/runs/longmont-c1/session-8/20260721T231221Z/source_span_index.json` | `sha256:2c8360cc56d1108e1b9c7ea48726866c92f8c647a85e0d205aa9f1ec974ce190` | `out/graph_memory/runs/longmont-c1/session-8/20260721T231221Z/candidate_graph.json` | `sha256:5777f549120dd8aa514f6ca154d9905483e15416d13e0f5e66eccc5ff32d2779` | `out/graph_memory/runs/longmont-c1/session-8/20260721T231221Z/candidate_validation_report.json` | `sha256:85a43aa48cb97e49f8ffb44b4824de02b8a3180c1ad0ff7aecf001dc1b7c6237` | `out/graph_memory/runs/longmont-c1/session-8/20260721T231221Z/provenance_index.json` | `sha256:f2d8bed74f943613dac93a1e41f7875e90a481c063c5d41deafa1efd64b59e7b` |
| `graph-ingest:longmont-c1:session-9:20260722T020338Z` | `longmont-c1` | `session-9` | `validated` | `artifact:recap:longmont-c1:session-9` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 09 - Battle with the Meat Monsters.md` | `sha256:74b7fb39ee0915ebfa6957538d5f0a07ec7ad230e8b7c45accd5addf882bbc5b` | `out/graph_memory/runs/longmont-c1/session-9/20260722T020243Z/source_span_index.json` | `sha256:96147b3ef3cdfc8bb6ee669676e7ec54ce9094c902f4f93ce2dbb21636e8893c` | `out/graph_memory/runs/longmont-c1/session-9/20260722T020243Z/candidate_graph.json` | `sha256:75e74364a88ff5b47035cce43b5fb4eea8261964ae5ec3a27c3d9819b3bc975f` | `out/graph_memory/runs/longmont-c1/session-9/20260722T020243Z/candidate_validation_report.json` | `sha256:9f5b12433927ef896b0ccb53b977ead8a2ca2ee84524c87479a56d06249955ee` | `out/graph_memory/runs/longmont-c1/session-9/20260722T020243Z/provenance_index.json` | `sha256:a656154117dfbdb866a7d47f280b1db29f1235b98950a1133da0ecbeec156f43` |
| `graph-ingest:longmont-c2:session-23:20260629T041111Z` | `longmont-c2` | `session-23` | `validated` | `artifact:recap:longmont-c2:session-23` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | `sha256:aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `out/graph_memory/runs/longmont-c2/session-23/20260629T040935Z/source_span_index.json` | `sha256:c12013414c4c4d50de0b4bbfb192de97535c3656b7f257056c498cb1b0783edb` | `out/graph_memory/runs/longmont-c2/session-23/20260629T040935Z/candidate_graph.json` | `sha256:720bbbf75ef2820699e67b84c8ab2ce7fc680f13670bc1bd5aaeaf8714b2b414` | `out/graph_memory/runs/longmont-c2/session-23/20260629T040935Z/candidate_validation_report.json` | `sha256:9ed3463e2ee06707762e838119d32b875bcfb63407c46ec56a85935559f3b2dc` | `out/graph_memory/runs/longmont-c2/session-23/20260629T040935Z/provenance_index.json` | `sha256:a945dd283630414794ba8b7e95785cf789b882d89afdf8ee930e15d693c36024` |
| `graph-ingest:longmont-c2:session-23:20260629T125348Z` | `longmont-c2` | `session-23` | `validated` | `artifact:recap:longmont-c2:session-23` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | `sha256:aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125244Z/source_span_index.json` | `sha256:c12013414c4c4d50de0b4bbfb192de97535c3656b7f257056c498cb1b0783edb` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125244Z/candidate_graph.json` | `sha256:cb12c10c7a3b4febcba496933c32a90c1c91f1034ca626562c06956e23839604` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125244Z/candidate_validation_report.json` | `sha256:5697be0a4fc6b048ec2a6a073276da2f6a882f827754130089efb9cfaf5ebec5` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125244Z/provenance_index.json` | `sha256:8990905bbcb2889f08228766a0b0c5d215241fd2798e18241963e594530b1bf2` |
| `graph-ingest:longmont-c2:session-23:20260629T125456Z` | `longmont-c2` | `session-23` | `validated` | `artifact:recap:longmont-c2:session-23` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | `sha256:aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125401Z/source_span_index.json` | `sha256:c12013414c4c4d50de0b4bbfb192de97535c3656b7f257056c498cb1b0783edb` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125401Z/candidate_graph.json` | `sha256:489e88e652b66f3da6a96efee0b1c26511e51e5aed70dc195b45522b437d026d` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125401Z/candidate_validation_report.json` | `sha256:14194c782071d7b3b348985eb14f2ffece1013afda5111cc2fc3206e03dc4462` | `out/graph_memory/runs/longmont-c2/session-23/20260629T125401Z/provenance_index.json` | `sha256:7a2694d23c09e743aabcafa868c73b759107b1292f26d7fd0c3131b703ee62cd` |
| `graph-ingest:longmont-c2:session-23:20260629T144607Z` | `longmont-c2` | `session-23` | `validated` | `artifact:recap:longmont-c2:session-23` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | `sha256:aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `out/graph_memory/runs/longmont-c2/session-23/20260629T144508Z/source_span_index.json` | `sha256:c12013414c4c4d50de0b4bbfb192de97535c3656b7f257056c498cb1b0783edb` | `out/graph_memory/runs/longmont-c2/session-23/20260629T144508Z/candidate_graph.json` | `sha256:91a50e1b64f149e3a0796c478e63d3d8887b1134d030b5f6155695728b2ab001` | `out/graph_memory/runs/longmont-c2/session-23/20260629T144508Z/candidate_validation_report.json` | `sha256:36d5a2720243823d63dc9998ed1750af068c8988b6cf08a612304d6e0c840ef9` | `out/graph_memory/runs/longmont-c2/session-23/20260629T144508Z/provenance_index.json` | `sha256:f467b30780eaf9905cfa8fb2516329229cb04dff1e0619fe71d8b35fa18fa4fe` |
| `graph-ingest:longmont-c2:session-23:20260629T183203Z` | `longmont-c2` | `session-23` | `validated` | `artifact:recap:longmont-c2:session-23` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | `sha256:aed38be1e2c20771eeb0f2c3248b991e859cf4c3dcaa631d7d88eeecc7f52b23` | `out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/source_span_index.json` | `sha256:c12013414c4c4d50de0b4bbfb192de97535c3656b7f257056c498cb1b0783edb` | `out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/candidate_graph.json` | `sha256:cd36b0c17aa6f049f79aff4d00a03a9df4c3401e5e6bc13555eac67c1009b404` | `out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/candidate_validation_report.json` | `sha256:a6574181ec59acd7733222c1f0f045f295edfdd3631af08f782c6f6b95ddb768` | `out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/provenance_index.json` | `sha256:54cf6be3ffd427e7c6dd0bccab2b39888accf5cb6ca03ef8ccdc5ebaee60eb24` |
| `graph-ingest:longmont-c2:session-24:20260629T035803Z` | `longmont-c2` | `session-24` | `validated` | `artifact:recap:longmont-c2:session-24` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md` | `sha256:603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95` | `out/graph_memory/runs/longmont-c2/session-24/20260629T035701Z/source_span_index.json` | `sha256:24893969811d794c3870105c28230168a75ba01836fe9f2e7db5e77d078553ad` | `out/graph_memory/runs/longmont-c2/session-24/20260629T035701Z/candidate_graph.json` | `sha256:fbde631155367ada9421447e356d84db3746278519f842d5060b56eb7436c167` | `out/graph_memory/runs/longmont-c2/session-24/20260629T035701Z/candidate_validation_report.json` | `sha256:bac8a4ecd164f2867cf63c501ac53553df09591e57a9c0a6167a12138d3d856e` | `out/graph_memory/runs/longmont-c2/session-24/20260629T035701Z/provenance_index.json` | `sha256:2e82e3d3021d3978ed44ac542026791f8a384fdf8affd59706922562ad26c5c0` |
| `graph-ingest:longmont-c2:session-24:20260713T181901Z` | `longmont-c2` | `session-24` | `validated` | `artifact:recap:longmont-c2:session-24` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md` | `sha256:603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181801Z/source_span_index.json` | `sha256:24893969811d794c3870105c28230168a75ba01836fe9f2e7db5e77d078553ad` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181801Z/candidate_graph.json` | `sha256:be3b05218b271e429ce5a29addcd3bd05b8aad96c45cc04beafeb70279a730c5` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181801Z/candidate_validation_report.json` | `sha256:0fe0eec0b489c82f5c6d36b0b5f8843fc040cafc14f0adf7bd612b42cec303ba` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181801Z/provenance_index.json` | `sha256:266db856415f41deefcdca3c0f967f515ad09863cffa8aff769bb6c75c29b9f1` |
| `graph-ingest:longmont-c2:session-24:20260713T182027Z` | `longmont-c2` | `session-24` | `validated` | `artifact:recap:longmont-c2:session-24` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md` | `sha256:603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181934Z/source_span_index.json` | `sha256:24893969811d794c3870105c28230168a75ba01836fe9f2e7db5e77d078553ad` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181934Z/candidate_graph.json` | `sha256:43e591f30be3b54d5a8ad1376fcc053ca6b5a19bba58600c7853ed723f7d893f` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181934Z/candidate_validation_report.json` | `sha256:5eacf3a670deea1e6049ea05c6eb02b3ccdec0c07ba4659cdbab829a26f56343` | `out/graph_memory/runs/longmont-c2/session-24/20260713T181934Z/provenance_index.json` | `sha256:6e7de2f2c5af8dfa65ea6ac46fabfb286bc8d19f269c57b4e2b1dd4dbafc47e4` |
| `graph-ingest:longmont-c2:session-25:20260808T005650Z` | `longmont-c2` | `session-25` | `validated` | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | `sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d` | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/source_span_index.json` | `sha256:94a7ba5770846f63ccb83485249a786ba7f198762e57af88ef50df702e7372d9` | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/candidate_graph.json` | `sha256:83d6675b7a1700790a749277cdf6cc18e41e911987d5a9522410358879d0d203` | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/candidate_validation_report.json` | `sha256:1f1107417fa73384026e000f7822191c5765da0a7512449f8ba84611e3cd47f2` | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c2:session-25:20260808T010324Z` | `longmont-c2` | `session-25` | `validated` | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | `sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010206Z/source_span_index.json` | `sha256:94a7ba5770846f63ccb83485249a786ba7f198762e57af88ef50df702e7372d9` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010206Z/candidate_graph.json` | `sha256:e947fdac47ec4f12e9e1ddbc2d58065519b85c6aa8be54cc6bf22b7329f6575d` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010206Z/candidate_validation_report.json` | `sha256:8a103bc8c8e50aee81630c726031d868bb6f2559729e2dcd6cef7b3c715ef212` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010206Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c2:session-25:20260808T010457Z` | `longmont-c2` | `session-25` | `validated` | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | `sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010341Z/source_span_index.json` | `sha256:94a7ba5770846f63ccb83485249a786ba7f198762e57af88ef50df702e7372d9` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010341Z/candidate_graph.json` | `sha256:43d75af0044b722a22bae053afb0b502368e55fe58ca8fc1b8000b51513cbafb` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010341Z/candidate_validation_report.json` | `sha256:b8434e26c8db27910734ca00094cd9c359a411a779e0bd84d639344ec0fc547b` | `out/graph_memory/runs/longmont-c2/session-25/20260808T010341Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c2:session-25:20260808T181823Z` | `longmont-c2` | `session-25` | `validated` | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | `sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d` | `out/graph_memory/runs/longmont-c2/session-25/20260808T181644Z/source_span_index.json` | `sha256:94a7ba5770846f63ccb83485249a786ba7f198762e57af88ef50df702e7372d9` | `out/graph_memory/runs/longmont-c2/session-25/20260808T181644Z/candidate_graph.json` | `sha256:a369322b89c82091a376046e1043c17557a9d78dea61e690207e239b94d4d86a` | `out/graph_memory/runs/longmont-c2/session-25/20260808T181644Z/candidate_validation_report.json` | `sha256:39495cdafa5036479ebbc6a4617b284309b336c09c07ec68c9ec9ecfb61dec65` | `out/graph_memory/runs/longmont-c2/session-25/20260808T181644Z/provenance_index.json` | `—` |
| `graph-ingest:longmont-c2:session-25:20260808T182312Z` | `longmont-c2` | `session-25` | `validated` | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | `sha256:fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d` | `out/graph_memory/runs/longmont-c2/session-25/20260808T182149Z/source_span_index.json` | `sha256:94a7ba5770846f63ccb83485249a786ba7f198762e57af88ef50df702e7372d9` | `out/graph_memory/runs/longmont-c2/session-25/20260808T182149Z/candidate_graph.json` | `sha256:1e6339fe7e4b065e8e74cd3978f2f55a90349041ce531bc67f40a511d79002c9` | `out/graph_memory/runs/longmont-c2/session-25/20260808T182149Z/candidate_validation_report.json` | `sha256:5aac3d6af12c1edee337a150747df7f992649c420ee83084e8e7f249c84ea0e2` | `out/graph_memory/runs/longmont-c2/session-25/20260808T182149Z/provenance_index.json` | `—` |

### 2.4 Incomplete / partial bundles — 21 runs

These catalog rows survive in APP-STATE but at least one review component byte is missing on `primary-checkout`. URIs/digests are still recorded for recovery.

| Stable run ID | Campaign | Session | Status | Missing on `primary-checkout` | SourceArtifact ID | Recorded component URIs (APP-STATE) |
| --- | --- | --- | --- | --- | --- | --- |
| `graph-ingest:longmont-c1:session-1:vocabulary-ablation-projection-dogfood` | `longmont-c1` | `session-1` | `validated` | source_span_index, candidate_graph, validation_report, provenance_index | `artifact:recap:longmont-c1:session-1` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md |
| `graph-ingest:longmont-c1:session-12:20260725T234131Z` | `longmont-c1` | `session-12` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c1:session-12:7184000a8cfb` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 12 - The Persistent Bugbear.md; source_span_index=out/graph_memory/runs/longmont-c1/session-12/20260725T234129Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c1/session-12/20260725T234129Z/provenance_index.json |
| `graph-ingest:longmont-c1:session-2:20260706T023954Z` | `longmont-c1` | `session-2` | `validated` | source_artifact | `artifact:recap:longmont-c1:session-2` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 02 - Stonebridge and Glowkindle Rats.md; source_span_index=out/graph_memory/runs/longmont-c1/session-2/20260706T023913Z/source_span_index.json; candidate_graph=out/graph_memory/runs/longmont-c1/session-2/20260706T023913Z/candidate_graph.json; validation_report=out/graph_memory/runs/longmont-c1/session-2/20260706T023913Z/candidate_validation_report.json; provenance_index=out/graph_memory/runs/longmont-c1/session-2/20260706T023913Z/provenance_index.json |
| `graph-ingest:longmont-c1:session-3:20260718T221306Z` | `longmont-c1` | `session-3` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c1:session-3` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md; source_span_index=out/graph_memory/runs/longmont-c1/session-3/20260718T221306Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c1/session-3/20260718T221306Z/provenance_index.json |
| `graph-ingest:longmont-c1:session-3:20260718T221321Z` | `longmont-c1` | `session-3` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c1:session-3` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 03 - The Stone Bridge Flood.md; source_span_index=out/graph_memory/runs/longmont-c1/session-3/20260718T221321Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c1/session-3/20260718T221321Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-23:20260629T040857Z` | `longmont-c2` | `session-23` | `validated` | source_artifact | `artifact:recap:longmont-c2:session-23` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Session-23 Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/source_span_index.json; candidate_graph=out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/candidate_graph.json; validation_report=out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/candidate_validation_report.json; provenance_index=out/graph_memory/runs/longmont-c2/session-23/20260629T040747Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-23:20260726T195010Z` | `longmont-c2` | `session-23` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-23:aed38be1e2c2` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195010Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195010Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-23:20260726T195016Z` | `longmont-c2` | `session-23` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-23:aed38be1e2c2` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195016Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195016Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-23:20260726T195019Z` | `longmont-c2` | `session-23` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-23:aed38be1e2c2` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195019Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195019Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-23:20260726T195025Z` | `longmont-c2` | `session-23` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-23:aed38be1e2c2` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195025Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-23/20260726T195025Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T031256Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031256Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031256Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T031305Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031305Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031305Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T031852Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031851Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031851Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T031856Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031855Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T031855Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T032202Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T032106Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T032106Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T033807Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T033729Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T033729Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:20260629T035216Z` | `longmont-c2` | `session-24` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-24` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md; source_span_index=out/graph_memory/runs/longmont-c2/session-24/20260629T035116Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-24/20260629T035116Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-24:manual-projection-dogfood` | `longmont-c2` | `session-24` | `validated` | source_span_index, candidate_graph, validation_report, provenance_index | `source:longmont-c2:session-24:raw-recap-placeholder` | source_artifact=evals/graph_memory_layer/examples/session_24_manual_projection_dogfood/session_24_raw_recap_PLACEHOLDER.md |
| `graph-ingest:longmont-c2:session-25:20260808T175430Z` | `longmont-c2` | `session-25` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md; source_span_index=out/graph_memory/runs/longmont-c2/session-25/20260808T175306Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-25/20260808T175306Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-25:20260808T175628Z` | `longmont-c2` | `session-25` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md; source_span_index=out/graph_memory/runs/longmont-c2/session-25/20260808T175504Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-25/20260808T175504Z/provenance_index.json |
| `graph-ingest:longmont-c2:session-25:20260808T180543Z` | `longmont-c2` | `session-25` | `prepared` | candidate_graph, validation_report | `artifact:recap:longmont-c2:session-25:fd38b5915b32` | source_artifact=corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md; source_span_index=out/graph_memory/runs/longmont-c2/session-25/20260808T180419Z/source_span_index.json; provenance_index=out/graph_memory/runs/longmont-c2/session-25/20260808T180419Z/provenance_index.json |

### 2.5 Catalog-only identity index (all 53)

Grouped by campaign/session for navigation. Full locators are in §2.3–§2.4.
**longmont-c1 / session-1** (4): `graph-ingest:longmont-c1:session-1:20260701T185713Z` `graph-ingest:longmont-c1:session-1:20260701T204409Z` `graph-ingest:longmont-c1:session-1:20260701T215257Z` `graph-ingest:longmont-c1:session-1:vocabulary-ablation-projection-dogfood`
**longmont-c1 / session-10** (1): `graph-ingest:longmont-c1:session-10:20260722T023135Z`
**longmont-c1 / session-11** (1): `graph-ingest:longmont-c1:session-11:20260724T031946Z`
**longmont-c1 / session-12** (3): `graph-ingest:longmont-c1:session-12:20260725T234131Z` `graph-ingest:longmont-c1:session-12:20260727T180223Z` `graph-ingest:longmont-c1:session-12:20260727T181654Z`
**longmont-c1 / session-13** (1): `graph-ingest:longmont-c1:session-13:20260727T200538Z`
**longmont-c1 / session-17** (1): `graph-ingest:longmont-c1:session-17:20260724T031527Z`
**longmont-c1 / session-2** (2): `graph-ingest:longmont-c1:session-2:20260706T023954Z` `graph-ingest:longmont-c1:session-2:20260706T024026Z`
**longmont-c1 / session-3** (5): `graph-ingest:longmont-c1:session-3:20260718T221306Z` `graph-ingest:longmont-c1:session-3:20260718T221321Z` `graph-ingest:longmont-c1:session-3:20260718T221836Z` `graph-ingest:longmont-c1:session-3:20260718T225145Z` `graph-ingest:longmont-c1:session-3:20260718T225250Z`
**longmont-c1 / session-4** (1): `graph-ingest:longmont-c1:session-4:20260719T154814Z`
**longmont-c1 / session-5** (1): `graph-ingest:longmont-c1:session-5:20260719T201457Z`
**longmont-c1 / session-6** (1): `graph-ingest:longmont-c1:session-6:20260719T230637Z`
**longmont-c1 / session-7** (1): `graph-ingest:longmont-c1:session-7:20260721T141801Z`
**longmont-c1 / session-8** (1): `graph-ingest:longmont-c1:session-8:20260721T231322Z`
**longmont-c1 / session-9** (1): `graph-ingest:longmont-c1:session-9:20260722T020338Z`
**longmont-c2 / session-23** (10): `graph-ingest:longmont-c2:session-23:20260629T040857Z` `graph-ingest:longmont-c2:session-23:20260629T041111Z` `graph-ingest:longmont-c2:session-23:20260629T125348Z` `graph-ingest:longmont-c2:session-23:20260629T125456Z` `graph-ingest:longmont-c2:session-23:20260629T144607Z` `graph-ingest:longmont-c2:session-23:20260629T183203Z` `graph-ingest:longmont-c2:session-23:20260726T195010Z` `graph-ingest:longmont-c2:session-23:20260726T195016Z` `graph-ingest:longmont-c2:session-23:20260726T195019Z` `graph-ingest:longmont-c2:session-23:20260726T195025Z`
**longmont-c2 / session-24** (11): `graph-ingest:longmont-c2:session-24:20260629T031256Z` `graph-ingest:longmont-c2:session-24:20260629T031305Z` `graph-ingest:longmont-c2:session-24:20260629T031852Z` `graph-ingest:longmont-c2:session-24:20260629T031856Z` `graph-ingest:longmont-c2:session-24:20260629T032202Z` `graph-ingest:longmont-c2:session-24:20260629T033807Z` `graph-ingest:longmont-c2:session-24:20260629T035216Z` `graph-ingest:longmont-c2:session-24:20260629T035803Z` `graph-ingest:longmont-c2:session-24:20260713T181901Z` `graph-ingest:longmont-c2:session-24:20260713T182027Z` `graph-ingest:longmont-c2:session-24:manual-projection-dogfood`
**longmont-c2 / session-25** (8): `graph-ingest:longmont-c2:session-25:20260808T005650Z` `graph-ingest:longmont-c2:session-25:20260808T010324Z` `graph-ingest:longmont-c2:session-25:20260808T010457Z` `graph-ingest:longmont-c2:session-25:20260808T175430Z` `graph-ingest:longmont-c2:session-25:20260808T175628Z` `graph-ingest:longmont-c2:session-25:20260808T180543Z` `graph-ingest:longmont-c2:session-25:20260808T181823Z` `graph-ingest:longmont-c2:session-25:20260808T182312Z`
---

## 4. Plan — recovery ledger

Leftover APP-STATE **Plan count = 0** (`list_plans(status=None)`, `LIVE-READ`). Workspace document registry HTTP: `records=0`.

Historical Plan evidence survives on `primary-checkout` file registries and orphan workspace paths. DFC-2a recovered `80630cc2-…` exactly once into leftover APP-STATE; that row was lost when local Postgres/tmpfs restarted. This survey did **not** re-adopt.

| Stable identity | Human title | DFC-1 class | Registry root | Registry path | Declared `target_relpath` | Exact bytes survive? | Bytes on `primary-checkout`? | Byte count | SHA-256 | Current leftover APP-STATE | Product state | Recovery action later |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `80630cc2-33ee-40db-bf9d-fb5217085e17` | C2 Session 27 Prep | RECOVERABLE_EXACT | `primary-checkout` | `out/registries/workspace_documents.json` | `out/workspace/plan/80630cc2-33ee-40db-bf9d-fb5217085e17.md` | Yes | Yes | 2631 | `sha256:d8a8595d5211d00a57731354ea06bce25aa6236332b66dece59870ed9d77a511` | NOT_ADOPTED (lost after DB recreate) | STRANDED_EXACT | Re-adopt exact bytes if still intact; do not invent prose |
| `61b3a73b-df4e-4133-9879-bb2096796055` | C2 Session 27 Prep | RECOVERABLE_EXACT | `primary-checkout` | `out/registries/workspace_documents.json` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 27 Prep.md` | No | No | 0 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) | NOT_ADOPTED | MISSING_BYTES | DFC-2p archive hunt; no blank-shell adoption |
| `c2121a99-d0da-4ba1-b1ef-511f4f2e3abf` | C2 Session 23 Prep | RECOVERABLE_EXACT | `primary-checkout` | `out/registries/workspace_documents.json` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md` | No | No | 0 | empty-file digest | NOT_ADOPTED | MISSING_BYTES | DFC-2p archive hunt |
| `d6ed9790-ebbf-401d-90ba-182aff80917d` | C2 Session 23 Prep | RECOVERABLE_EXACT | `primary-checkout` | `out/registries/workspace_documents.json` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md` | No | No | 0 | empty-file digest | NOT_ADOPTED | MISSING_BYTES | DFC-2p archive hunt |
| `00000000-0000-4000-8000-000000000000` | probe | RECOVERABLE_EXACT | `primary-checkout` | `out/registries/workspace_documents.json` | `out/workspace/plan/00000000-0000-4000-8000-000000000000.md` | No | No | 0 | empty-file digest | NOT_ADOPTED | MISSING_BYTES | discard residue only |
| `0bcfbf24-6afd-4dff-8d3b-939ca2f86cab` | _(untitled orphan)_ | NEEDS_ADAPTER | `primary-checkout` | _(no registry row)_ | `out/workspace/plan/0bcfbf24-6afd-4dff-8d3b-939ca2f86cab.md` | Yes | Yes | 457 | `sha256:0b404c09541a3b75c9180f9c10180b026f9f2d49543524a79d42264112bf7c5c` | NOT_ADOPTED | NEEDS_ADAPTER | DFC-2p metadata adapter before import |
| `0eab57a6-c1e1-4b07-a66b-b29e2ef50ed4` | _(untitled orphan)_ | NEEDS_ADAPTER | `primary-checkout` | _(no registry row)_ | `out/workspace/plan/0eab57a6-c1e1-4b07-a66b-b29e2ef50ed4.md` | Yes | Yes | 461 | `sha256:39db0770cc08b1586be26a5abbaa5ef24197e725fc8d727c07558bfc01b5b3f7` | NOT_ADOPTED | NEEDS_ADAPTER | DFC-2p metadata adapter before import |

Assembled `/plan` showed chooser residue `local-plan:c917bba1-5993-4e24-96b7-b29a5376ab7d` (“C2 Session 23 Prep (no longer listed as active)”). That is a **browser/local draft identity**, not WorkObject `c2121a99-…` (`LIVE-READ`).

---

## 5. Build / worldbuilding source — recovery ledger

APP-STATE / workspace registry: **0** Build documents (`LIVE-READ`). Assembled `/build` chooser empty.

All four DFC-1 Build identities remain `NEEDS_ADAPTER`. Of Conks registry rows are **locators only**; Of Conks is not the target corpus.

| Stable identity | Human title | DFC-1 class | Registry root | Registry path | Declared `target_relpath` | Exact bytes survive? | Bytes on declared root? | Byte count | SHA-256 | Current leftover APP-STATE | Product state | Recovery action later |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `6678fafc-cea7-4101-b36d-fa1b0a1d1170` | Ironveil Manor | NEEDS_ADAPTER | `of-conks` | `out/registries/workspace_documents.json` | `corpus/eldyrwild-markdown/_dungeonbuddy/sources/6678fafc-cea7-4101-b36d-fa1b0a1d1170/source.md` | No | No | 0 | — | NOT_ADOPTED | MISSING_BYTES | DFC-2b locate bytes or abandon |
| `9e7786d8-2253-4f8d-b37f-e0720feeaeda` | Hempholm — run packet | NEEDS_ADAPTER | `of-conks` | `out/registries/workspace_documents.json` | `corpus/of-conks-cons-markdown/_dungeonbuddy/sources/9e7786d8-2253-4f8d-b37f-e0720feeaeda/source.md` | No | No | 0 | — | NOT_ADOPTED | MISSING_BYTES | locator only (Of Conks corpus) |
| `d10bd414-d461-48eb-a514-2c34d0fe2d8d` | SI-6 Find-existing Witness | NEEDS_ADAPTER | `stewardship-si6` | `out/registries/workspace_documents.json` | `corpus/eldyrwild-markdown/_dungeonbuddy/sources/d10bd414-d461-48eb-a514-2c34d0fe2d8d/source.md` | No | No | 0 | — | NOT_ADOPTED | MISSING_BYTES | DFC-2b locate bytes |
| `6cfebc9a-aa71-4799-8505-fbd0f5b5fb6b` | _(untitled orphan)_ | NEEDS_ADAPTER | `primary-checkout` | _(no registry row)_ | `out/workspace/worldbuilding/6cfebc9a-aa71-4799-8505-fbd0f5b5fb6b.md` | Yes | Yes | 1938 | `sha256:adeeaaee313c35f7110d9bfd5b5a6766dd647fc223fc9ff558573096119eecff` | NOT_ADOPTED | NEEDS_ADAPTER | DFC-2b registry-metadata adapter |

Evidence: `LIVE-READ` registry JSON on historical roots + path existence checks (`primary-checkout`, `of-conks`, `stewardship-si6`).

---

## 6. Runbook / Play

| Material | Leftover APP-STATE | Historical DFC-1 roots | Assembled product | Interaction level |
| --- | --- | --- | --- | --- |
| Runbook | 0 | 0 admitted | `/play`: “No active Runbooks are available.” | NOT_ADOPTED |
| Play Run | 0 | 0 admitted | `/play`: “No durable Runs are available.” | NOT_ADOPTED |

Create blank Runbook was visible but disabled until Campaign is filled. This survey did not type a campaign or create a Runbook (`LIVE-READ` only).

---

## 7. What this library is not

- Not a World node dump.
- Not authorization to copy `out/` artifacts, re-ingest, or mutate leftover APP-STATE.
- Not proof that `current-main` missing files are globally missing.
- Component URIs in §2 are authoritative locators; do not infer artifact directories from `run_id` timestamps alone.

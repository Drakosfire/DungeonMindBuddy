# REPORT — TL01G V15 / Adv V13 Cohort Certification

**Disposition:** `CERTIFIED_FOR_EXECUTION`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/498  
**Branch:** `timeline/tl01g-v15-adv13-cohort-certification`  
**Handoff:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md`  
**Implementation base:** `d3b4060fabd6c2b7fff0403af260637845c86dd9`  
**Certification SHA:** `24679b19ac093cdbefa430cb0e930dff8c8a6dae`  
**Invalidated prior certification SHAs:** `e59dd742…` (cycle 1); `09da5f76…` (cycle 2); `0ea6c2a9…` (cycle 3)  
**Provider calls in this PR:** **0**

## Review cycle 1 — invalidation and repair

Prior certification `e59dd742…` is **invalid**. Review 4840512822 found:

1. V15 `assertion:a61c1383591400f3` stimulus contained `before winter storms` while gold claimed no execution-time expression.
2. Adv V13 source-time trap stimulus/label contained `overnight` while gold claimed no narrated occurrence time.
3. Sibling source-template Jaccard between V15 and Adv V13 was claimed but untested.

Repairs (provider-unobserved; new certification required):

- Stimulus now: `Neris Quill intends to chart every shoal.` (no deadline phrase); gold remains unresolved.
- Stimulus/label now: `Lira Spelt shelves the Ashpetal folios` / `… in good order.` (no `overnight`); gold remains unresolved; assertion id is now `assertion:0a21dac97f3021a6`.
- Added `test_v15_adv_v13_sibling_source_template_jaccard_below_threshold` (exact templates disjoint; Jaccard `< 0.40`).

## Review cycle 2 — owning-fixture abstention proofs

Prior certification `09da5f76…` is **invalid**. Review cycle 2 found that repaired false-abstention cases still lacked owning-fixture regressions: existing tests confirmed only unresolved + null lanes, not that V15’s stimulus lacks an execution-time phrase or that Adv V13’s session temptation exists only in registry metadata.

Repairs (provider-unobserved; new certification required; fixture bytes unchanged):

- Added `test_holdout_v15_future_commitment_stimulus_lacks_execution_time_phrase` binding `assertion:a61c1383591400f3` / `shoal-intent.md`.
- Added `test_adversarial_v13_source_time_trap_session_temptation_is_metadata_only` binding `assertion:0a21dac97f3021a6` / `register-keeps-session19.md` (session-19 in metadata only; owned prose has neither session-19 nor `overnight`).

## Review cycle 3 — exact sealed fixture bytes

Prior certification `0ea6c2a9…` is **invalid**. Review cycle 3 found that deny-list / regex guards still miss mutations such as `by spring`, `during winter`, or `at dawn` that would recreate defective unresolved/null gold.

Repairs (provider-unobserved; new certification required; fixture bytes unchanged):

- Both owning tests now assert exact sealed `label`, gold `source_phrase`, and resolved stimulus text.
- Adv V13 retains metadata-only `session-19` licensing checks.

Exact sealed values:

| Cohort | Assertion | Label | Source phrase | Resolved stimulus |
|---|---|---|---|---|
| V15 | `assertion:a61c1383591400f3` | `Neris Quill intends to chart every shoal` | `intends to chart every shoal` | `neris quill intends to chart every shoal.` |
| Adv V13 | `assertion:0a21dac97f3021a6` | `Lira Spelt shelves the Ashpetal folios` | `shelves the Ashpetal folios` | `lira spelt shelves the ashpetal folios in good order.` |

## Mission (copied)

The Timeline steward can merge one provider-unobserved, Gate-faithful V15 / Adv V13
cohort pair so a later execution PR can test frozen `tl01g-v1` without authoring or
repairing gold under observation.

## Merge-ready invariant (copied)

At one recorded certification SHA descended from current main, V15 and Adv V13 are
synthetic, mutually independent, cumulatively novel, exactly paired between frozen
`tl01f-v1` and `tl01g-v1`, fully bound to owned evidence, and Gate-faithful for every
selected assertion; all certification tests pass, no provider call or calibration
artifact exists, and the certified fixture, gold, source, case, audit, and owning-test
bytes remain unchanged for the successor execution PR.

## Frozen identities

| Identity | Value |
|---|---|
| Control | `tl01f-v1` / `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate | `tl01g-v1` / `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Retired cutoffs | holdout `14`, adversarial `12` |
| Later execution model (not called) | `gpt-5.4-mini` |

## Nano-commits (current head lineage)

1. `4b4377f0` — handoff
2. `6c9dfba8` — certification gates
3. `cfe9e7f2` / `e59dd742` — initial V15 / Adv V13 fixtures (**superseded**)
4. `1037c090` — initial certification record (**invalidated**, cycle 1)
5. `3b69e403` — sibling source-template Jaccard test
6. `09da5f76` — abstention gold/stimulus repair (**invalidated**, cycle 2)
7. `2be91e02` — cycle-1 re-certification record (**stale**)
8. `0ea6c2a9` — owning-fixture false-abstention proofs (**invalidated**, cycle 3)
9. `23833b79` — cycle-2 re-certification record (**stale**)
10. `24679b19` — exact sealed false-abstention fixture byte proofs (**current certification SHA**)
11. (this commit) — re-certification report + README seal pointers

## Assertion inventory

### Holdout V15 (12)

| Assertion ID | Proposition | Status |
|---|---|---|
| `assertion:ee27c2a2af8e0bc8` | Neris Quill sounds the tide-horn thrice | resolved |
| `assertion:43f19c97a48f5add` | The Mosscoil Ferry leaves at dusk tide | resolved |
| `assertion:1131fb59ebcaae89` | Bram Hollow is quay reckoner | resolved |
| `assertion:1191825403bf6375` | The Whisperloom Vault is sealed against night clerks | resolved |
| `assertion:b49813f9a03057f6` | Osha Venn audits the reef ledger | resolved |
| `assertion:a576743588c19513` | Tilda Crowe rings the dusk gong | resolved |
| `assertion:5fdb60f975578b33` | Bram Hollow is the quay reckoner | not_applicable |
| `assertion:135b7836d400b922` | The emberglass seal is ordinary glass | not_applicable |
| `assertion:a61c1383591400f3` | Neris Quill intends to chart every shoal | unresolved |
| `assertion:cdd4df453fb0efef` | The quay council must appoint a pier scribe | unresolved |
| `assertion:72e257f48e124234` | Witnesses conflict whether the tide-horn tally bound Bram Hollow as night watch or merely listed him as alternate | ambiguous |
| `assertion:6f267289e9f12821` | Neris Quill tends the tide-horn | unresolved |

### Adversarial V13 (10)

| Assertion ID | Proposition | Status |
|---|---|---|
| `assertion:0a21dac97f3021a6` | Lira Spelt shelves the Ashpetal folios | unresolved |
| `assertion:ea6b7307edde4448` | Corven Ash will open Thornfen Beacon once the fog lifts | unresolved |
| `assertion:bd8eefd165efe613` | Pell Marrow lights the causeway lanterns at moonrise | resolved |
| `assertion:d72fbcdad287e1a5` | The Gloomwick Causeway is open to night carts | resolved |
| `assertion:692dbca9df0475f8` | Pell Marrow records beacon fuel tallies | resolved |
| `assertion:041d3a9d5014a1e7` | Corven Ash is fuel clerk | not_applicable |
| `assertion:5420f58150e514c9` | Clerks dispute whether the Ashpetal folio roster seated Lira Spelt as night clerk or only queued her as standby | ambiguous |
| `assertion:3ed3e502da2f502a` | The Thornfen Beacon cracked nine winters earlier | resolved |
| `assertion:3057260d5a4c0cdd` | Lira Spelt bolts the Ashpetal folio chest at nightfall | resolved |
| `assertion:5fb7af52f7731558` | Ashpetal Register ink is black | not_applicable |

## Grounding defect lists

```text
_collect_resolved_value_grounding_defects(HOLDOUT_V15) == []
_collect_resolved_value_grounding_defects(ADV_V13) == []
```

## §7 command results (at certification SHA `24679b19…`)

| Command | Result |
|---|---|
| `uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py` | `98 passed` |
| `uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py tests/test_temporal_shadow_grounding_path.py` | `113 passed, 1 skipped` |
| `uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py` | All checks passed |
| `python -m json.tool` on eight cohort JSON files | OK |
| `test ! -e …/tl01g/promotion-v15` | true |
| Provider / artifact absence | 0 calls; no aggregate path |

Baseline failures / waivers: **none**  
Paths outside §4: **none**  
Stop conditions: **none**

## Certified file digests (SHA-256 at `24679b19…`)

```text
17918e9f8ec30c7d8d23f2d26dd88eb1138d4a2b64a9a2c7df33991dafae6069  tests/test_temporal_shadow_extraction_tl01g.py
7a4044375b70d421920f8ab302e88ea6fb2f74ca35187600332dfa6217815445  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/GOLD-AUDIT.md
ab5ab1f2b4dd3bd77b5750bb6ec826f1ccd80da69e7608e3459cca1d036e304e  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/base-contribution.json
cb8b3739d7ec79e3215d9c4e6fb61bb990846a72afabcb045f95027d788b48b8  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/gold-overlay.json
7ef55ca2297f13b0ebce890c1fa420c9311e3ab9f4d7bcfeca8b85b68738a71a  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01f.json
af0e61cf31a1d368a4148c166d8c8913f28d1319d3c9a7bea2669d0d79156e79  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/temporal-case-tl01g.json
f4b0d87e8034393229e9b6dd06a6976a46ed2928066a8f27f2c6bc5c4d827710  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/dusk-gong-ceased.md
881ba3901c1b915e4631a88c174a094dd8afe94dbf5f944ba3c3277be5a266c1  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/emberglass-identity.md
23fcc6234f5dfa0bd297fae067259d0a183f1ee4f216456760ba9f91ea924d27  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/ferry-dusk-tide.md
9963d300c35fb11210e9f83388bd9f0a3bb72a35cec12ef2fd8957b8a12effa6  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/marshal-ambiguous.md
15ae7f52f9ec336b2c4ddaa9fa19b6e39f8ec6d7bb9f169dd3b8d04058fcafe0  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/pier-scribe-missing.md
07b2c803e0964aa084c2d607516851570decfcd187e54c7e3b58cef282776314  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/reckoner-start.md
4a49f2720345b7d89f37e797809101ce5477285de9b5a4b8077a71c88f603388  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/reckoner-still.md
69d9997d96485c9aef4c5a48c14ad17fb680aa18f8ac41a37fda5019c99f5ce6  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/reef-ledger-end.md
d1bbded5f2df89eb12e608c98dd15c5cf88a115635647ca84aa9dfad12e7d0de  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/session-21-tide-horn-tending.md
5212dec5fc38184e26cd852810bf1f8ba6ffac2966872024310c263118c743cc  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/shoal-intent.md
f2b11adc5efe520e28dfa407d7abac881c8c5e7ff2280de0f999178cb7d7a2b0  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/tide-horn-session.md
ac839cd60ad7bacb79a4da02040c150c742f2f892cf20fc1802ce7b292989b07  evals/graph_memory_layer/examples/temporal_shadow_holdout_v15/sources/vault-sealed-since.md
c566a0b2ad05e1d0184d1f900bc1b3e1876dda23ce23987bea80de798b1f60e7  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/GOLD-AUDIT.md
47babf81f9c1224482e3b895c5813ac12b4358e1840b6f8c832173a626b4bb06  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/base-contribution.json
f937a3d9216c8baf2213a63cc30c49dcc90e4c7aa8382b7d04d1dc07fef79da7  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/gold-overlay.json
83e214ccc99cdc2f52277b0cb30938a9297dd8781bacd18cbbc2c496d2cecd62  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01f.json
924f79ab30e1fbe64e23d3b593fb5a1843f2e7cd5d06a58b1decf6903a060791  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/temporal-case-tl01g.json
a6dfdcc2b344b2f19c6c66069aefbdec555c1e238d2612172db35ca381da62e0  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/beacon-cracked-historical.md
65d5ef51369a9dc4811bc6938376a57ae40623121d13fbca5beff39b3efc4d04  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/beacon-fog-prerequisite.md
d51634c740b42451499faf2d690b339f6ef99c25ccae28403930027775eb39cf  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/causeway-moonrise.md
eeae1d2ca2b5111f45905e2aa9b17a30479d664f9cebbbd4f4152687b71a2cb4  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/causeway-open-edict.md
2bf3730ed454003faa3acbd6c072addc0dfa84d33043e7594f85ea889725183c  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/fuel-clerk-still.md
4f42a7da9369f25acaff1c6af82577c52fe6fa6fe7d2b1bcde60274cabcdf8ad  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/fuel-tally-end.md
da250b8f21b335e4de0aea37cf7e945d3701112b76130b61b724f53f563a71cb  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-ink-black.md
da41ff52dd037cb420990235f23b5690a2dbc7239cfbd191f31a28caea4c9d69  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-keeper-ambiguous.md
fcdb75422c423764ad405faf2dcc098f66339202d564458cad5dfe4bfbf6662a  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-keeps-session19.md
33e3fc98f7943c60ecad607da7d8fbe16ff7d78b741815573ea12f1f0da620c9  evals/graph_memory_layer/examples/temporal_shadow_adversarial_v13/sources/register-locks-nightfall.md
```

## What remains false

- No provider matrix, aggregate, or promotion disposition
- No `tl01h-v1` / prompt / packet / renderer / runner / graph changes
- No corpus / Project Source / Supergraph ingest edits
- No broader-shadow readiness claim

## Named successor

```text
TIMELINE: execute certified TL01G promotion matrix
```

Verify certification SHA `24679b19…` and every digest above before any provider call; treat certified fixture bytes as read-only.

# REPORT — TL01G V15 / Adv V13 Cohort Certification

**Disposition:** `CERTIFIED_FOR_EXECUTION`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/498  
**Branch:** `timeline/tl01g-v15-adv13-cohort-certification`  
**Handoff:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-cohort-certification.md`  
**Implementation base:** `d3b4060fabd6c2b7fff0403af260637845c86dd9` (`origin/main` at certification)  
**Certification SHA:** `e59dd742557f35702b09b8f34a6bc6bea078262f`  
**Provider calls in this PR:** **0**

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

## Nano-commits

1. `4b4377f0` — `docs(timeline): add v15 adv13 cohort certification handoff`
2. `6c9dfba8` — `test(timeline): define v15 adv13 certification gates`
3. `cfe9e7f2` — `test(timeline): author v15 holdout certification fixtures`
4. `e59dd742` — `test(timeline): author adv13 certification fixtures` (**certification SHA**)
5. (this commit) — `docs(timeline): record v15 adv13 certification`

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
| `assertion:1d82e3638a885810` | Lira Spelt shelves the Ashpetal folios overnight | unresolved |
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

At certification SHA `e59dd742…`:

```text
_collect_resolved_value_grounding_defects(HOLDOUT_V15) == []
_collect_resolved_value_grounding_defects(ADV_V13) == []
```

Source-time traps remain unresolved with null lanes (V15 tide-horn tending; Adv V13 Ashpetal folio shelving).

## §7 command results (provenance: local worktree at certification SHA)

| Command | Result |
|---|---|
| `uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py` | `95 passed` |
| `uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py tests/test_temporal_shadow_grounding_path.py` | `113 passed, 1 skipped` |
| `uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py` | All checks passed |
| `python -m json.tool` on all eight V15/Adv13 JSON files | OK |
| `git status --short` | empty before report commit |
| `git merge-base --is-ancestor origin/main HEAD` | true |
| `test ! -e …/tl01g/promotion-v15` | true (no artifact) |
| Changed-path denylist scan | no hits (`scope_ok`) |

Baseline failures / waivers: **none**  
Paths outside §4 / bounded sources: **none**  
Stop conditions: **none**

## Certified file digests (SHA-256 at certification SHA)

Owning tests + fixture/gold/case/audit/stimulus bytes (README seal pointers updated in the documentation commit after this SHA and are not execution inputs):

```text
d5c3f52f780515ab106b959105630e4820923bacc883344fb6f818b3f48aedc2  tests/test_temporal_shadow_extraction_tl01g.py
abebf53815670493b25d874d56b1877ce0f6f4464e12e746bdb8e3631d7d6b13  .../holdout_v15/GOLD-AUDIT.md
ab5ab1f2b4dd3bd77b5750bb6ec826f1ccd80da69e7608e3459cca1d036e304e  .../holdout_v15/base-contribution.json
cb8b3739d7ec79e3215d9c4e6fb61bb990846a72afabcb045f95027d788b48b8  .../holdout_v15/gold-overlay.json
1fd5570c553cf7be7610015dde097e289d55e65d9836cabcb777f2f0d665f2e9  .../holdout_v15/temporal-case-tl01f.json
1d38babe2cdf0b56b3afe7edbbd943917b3aff08611e4df736a36c4ba8bf947a  .../holdout_v15/temporal-case-tl01g.json
f4b0d87e8034393229e9b6dd06a6976a46ed2928066a8f27f2c6bc5c4d827710  .../holdout_v15/sources/dusk-gong-ceased.md
881ba3901c1b915e4631a88c174a094dd8afe94dbf5f944ba3c3277be5a266c1  .../holdout_v15/sources/emberglass-identity.md
23fcc6234f5dfa0bd297fae067259d0a183f1ee4f216456760ba9f91ea924d27  .../holdout_v15/sources/ferry-dusk-tide.md
9963d300c35fb11210e9f83388bd9f0a3bb72a35cec12ef2fd8957b8a12effa6  .../holdout_v15/sources/marshal-ambiguous.md
15ae7f52f9ec336b2c4ddaa9fa19b6e39f8ec6d7bb9f169dd3b8d04058fcafe0  .../holdout_v15/sources/pier-scribe-missing.md
07b2c803e0964aa084c2d607516851570decfcd187e54c7e3b58cef282776314  .../holdout_v15/sources/reckoner-start.md
4a49f2720345b7d89f37e797809101ce5477285de9b5a4b8077a71c88f603388  .../holdout_v15/sources/reckoner-still.md
69d9997d96485c9aef4c5a48c14ad17fb680aa18f8ac41a37fda5019c99f5ce6  .../holdout_v15/sources/reef-ledger-end.md
d1bbded5f2df89eb12e608c98dd15c5cf88a115635647ca84aa9dfad12e7d0de  .../holdout_v15/sources/session-21-tide-horn-tending.md
9e05e80d2d8b2c671823df04c650c8d5f8f9096ae14e00e0bb9a852162e9f9ce  .../holdout_v15/sources/shoal-intent.md
f2b11adc5efe520e28dfa407d7abac881c8c5e7ff2280de0f999178cb7d7a2b0  .../holdout_v15/sources/tide-horn-session.md
ac839cd60ad7bacb79a4da02040c150c742f2f892cf20fc1802ce7b292989b07  .../holdout_v15/sources/vault-sealed-since.md
70364af6154abf4f8995f970d244e37bb145290f395cd44d133b82bcd7271b4d  .../adversarial_v13/GOLD-AUDIT.md
1a751d5363751d15faaebce81746af2535d2d736137f59abd86cad5ae446336a  .../adversarial_v13/base-contribution.json
edb2c8422325b1b6859bfc9f0cd9c0c04a7f75267f5fdd1981b69f8f17605a71  .../adversarial_v13/gold-overlay.json
af89f9d45089781120ad8b5c889ae296f1d230b3ea3d1a383b9bdca6e2a051c2  .../adversarial_v13/temporal-case-tl01f.json
307ab247de69db36caabc90c851fc531ae57066963712dfda68dc0e1b25e32e9  .../adversarial_v13/temporal-case-tl01g.json
a6dfdcc2b344b2f19c6c66069aefbdec555c1e238d2612172db35ca381da62e0  .../adversarial_v13/sources/beacon-cracked-historical.md
65d5ef51369a9dc4811bc6938376a57ae40623121d13fbca5beff39b3efc4d04  .../adversarial_v13/sources/beacon-fog-prerequisite.md
d51634c740b42451499faf2d690b339f6ef99c25ccae28403930027775eb39cf  .../adversarial_v13/sources/causeway-moonrise.md
eeae1d2ca2b5111f45905e2aa9b17a30479d664f9cebbbd4f4152687b71a2cb4  .../adversarial_v13/sources/causeway-open-edict.md
2bf3730ed454003faa3acbd6c072addc0dfa84d33043e7594f85ea889725183c  .../adversarial_v13/sources/fuel-clerk-still.md
4f42a7da9369f25acaff1c6af82577c52fe6fa6fe7d2b1bcde60274cabcdf8ad  .../adversarial_v13/sources/fuel-tally-end.md
da250b8f21b335e4de0aea37cf7e945d3701112b76130b61b724f53f563a71cb  .../adversarial_v13/sources/register-ink-black.md
da41ff52dd037cb420990235f23b5690a2dbc7239cfbd191f31a28caea4c9d69  .../adversarial_v13/sources/register-keeper-ambiguous.md
dd026feb377ab486ce621301d20d04e2f8a41bed9a6c3c3d56580541fe6e035b  .../adversarial_v13/sources/register-keeps-session19.md
33e3fc98f7943c60ecad607da7d8fbe16ff7d78b741815573ea12f1f0da620c9  .../adversarial_v13/sources/register-locks-nightfall.md
```

## What remains false

- No provider matrix, aggregate, or promotion disposition
- No `tl01h-v1` / prompt, packet, renderer, runner, or graph changes
- No corpus / Project Source / Supergraph ingest edits
- No broader-shadow readiness claim

## Named successor

```text
TIMELINE: execute certified TL01G promotion matrix
```

That PR must verify this certification SHA and every certified digest above, treat
V15/Adv13 fixture/gold/source/case/audit/owning-test bytes as read-only, and run at
most one six-lane × three-repetition matrix (≤18 attempts, no retry) on frozen
`tl01f-v1` / `tl01g-v1`.

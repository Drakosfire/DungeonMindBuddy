# GOLD-AUDIT — temporal_shadow_holdout_v13

Independent holdout after prompt freeze `67408bd871ba684e70ddf6e53dd7088d0036a475`. V12 retired. Sealed before first provider run.

This audit binds fixture consistency (assertion IDs, labels, gold status, lane class, supporting phrase). Human Gate judgment is recorded in rationale columns but is not machine-verified beyond those binding checks.

| Assertion ID | Assertion proposition | Gate B eligibility | Proposition class | Gold status | Gold lane | Supporting phrase | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:9baab53e44466c80` | Ogonob removes the head of the Storm Elemental | eligible | occurrence | resolved | occurrence (session) | `removes the head of the Storm Elemental` | see diagnostics | Supported |
| `assertion:d350cf2cef4c678b` | A city-wide BBQ will start in the morning | eligible | occurrence | resolved | occurrence (textual) | `There is a city wide BBQ that starts in the morning.` | see diagnostics | Supported |
| `assertion:2664411c0ccd65d0` | Questionable Company holds Wolf's Manor as their Mirathorn home base | eligible | valid-start | resolved | valid-start (session) | `Now the adventures have a home base inside Mirathorn` | see diagnostics | Supported |
| `assertion:f1a6f1780edc1fc2` | The sewer loot chamber has been ransacked by the cult | eligible | valid-start | resolved | valid-start (textual) | `recently found and ransacked` | see diagnostics | Supported |
| `assertion:f59b518d7e4767f6` | The rebel humans feel represented in Mirathorn | eligible | valid-end | resolved | valid-end (session) | `no longer feel represented` | see diagnostics | Supported |
| `assertion:37dcfb0a72eae5e9` | The proto-Shepherd faction departed Mirathorn in a schism about five years ago | eligible | occurrence | resolved | occurrence (textual) | `Around five years ago` | see diagnostics | Supported |
| `assertion:9ae2721c7e601c4f` | The true Shepherd is still at large | not | restatement/identity | not_applicable | none | `still at large` | see diagnostics | Supported |
| `assertion:7c3d1fab00dd7353` | The nest reptiles are young drakes | not | restatement/identity | not_applicable | none | `they are young drakes` | see diagnostics | Supported |
| `assertion:15bef3a0902f3d44` | The group must decide what to do with the Wolf | eligible | unresolved | unresolved | none | `must decide what to do with the Wolf` | see diagnostics | Supported |
| `assertion:0365f051c8e59219` | Thalia intends that every city guard receives a potion | eligible | unresolved | unresolved | none | `make sure each guard in the city also receives a potion` | see diagnostics | Supported |
| `assertion:44c8cce73e18e0a4` | Grobnok became festival revenue warden when the council voted or was only proposed then | eligible | proposition-ambiguous | ambiguous | none | `became festival revenue warden when the council voted, or maybe he was only proposed then` | see diagnostics | Supported |
| `assertion:d25ec476e8268f16` | The council raid on the compromised guardhouse has been postponed until dawn | eligible | occurrence | resolved | occurrence (textual) | `postponed until dawn` | see diagnostics | Supported |

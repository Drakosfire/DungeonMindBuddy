# GOLD-AUDIT — temporal_shadow_holdout_v11

Independent TL01G promotion holdout after prompt freeze `67408bd871ba684e70ddf6e53dd7088d0036a475`. V10 retired. Sealed before first provider run.

| Assertion ID | Assertion proposition | Gate B eligibility | Proposition class | Gold status | Gold lane | Supporting phrase | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:cf1fdd299bde2b12` | Caelynn killed the Dustwalker at the Glimmering Globe | eligible | occurrence | resolved | occurrence (session) | `kills the Dustwalker` | valid-start from session provenance alone | Supported |
| `assertion:4748bfc6a1bc87a4` | Coliseum results will be announced the following day | eligible | forecast | resolved | occurrence (textual) | `the following day` | copying session-11 as occurrence without textual phrase | Supported |
| `assertion:11a5c700e06ca5aa` | Lysandra is addressed as Lieutenant Lysandra | eligible | valid-start-session | resolved | valid-start (session) | `Lieutenant Lysandra now` | occurrence-only without persistent-state start boundary | Supported |
| `assertion:08211230b5672bb4` | The roadside meat-stick restaurant is abandoned | eligible | valid-start-textual | resolved | valid-start (textual) | `no more than a week ago` | session-22 source time as start boundary | Supported |
| `assertion:0fa2194c373d6af3` | Bonogo feels compelled to attack the meatwings | eligible | valid-end | resolved | valid-end (session) | `no longer feel compelled` | occurrence at session-23 charm beat | Supported |
| `assertion:089e429987da7d53` | The Stormspire professor left about thirty years ago | eligible | historical | resolved | occurrence (textual) | `about 30 years ago` | session source time for historical departure | Supported |
| `assertion:0fc1c3f35074b0bb` | Everyone is still on edge about the missing guards | not | persistent-restatement | not_applicable | none | `still on edge about all the missing guards` | valid-start from mere still-state | Supported |
| `assertion:f0b95eaba30b4c80` | The dragon scale is from an extinct dragon lineage | not | identity/classification | not_applicable | none | `long extinct` | ambiguous identity fork | Supported |
| `assertion:5e29b10e861a06f0` | The group must make a final decision on the next steps | eligible | unresolved-plan | unresolved | none | `must make a final decision on the next steps` | resolved occurrence from session-16 narration time | Supported |
| `assertion:9239f08721e45750` | The group must create a plan for the Edge refugees | eligible | unresolved-commitment | unresolved | none | `create a plan for the refugees` | not_applicable restatement | Supported |
| `assertion:7f1f9c3be3e91c22` | Caelynn holds the mushroom spores since Tealeaf's lesson or only received them then | eligible | proposition-ambiguous | ambiguous | none | `exchange mushroom spores` | resolved custody without proposition-level fork | Supported |
| `assertion:cd5bbef7b9bce21b` | The Mirathorn festival has been postponed | eligible | occurrence-postponement | resolved | occurrence (textual) | `has been postponed` | valid-end for postponement (V10 defect) | Supported |

## Coverage checklist

- occurrence-only (session): yes (rows 1)
- occurrence textual/relative forecast: yes (row 2)
- valid-start-only (session): yes (row 3)
- valid-start textual (reject source session): yes (row 4)
- valid-end-only: yes (row 5)
- historical textual occurrence: yes (row 6)
- restatement not-applicable: yes (row 7)
- identity/classification not-applicable: yes (row 8)
- unresolved future/plan: yes (rows 9–10)
- proposition-level temporal ambiguous (`or` in label): yes (row 11)
- postponement as occurrence textual (NOT valid-end): yes (row 12)
- occurrence session #2: yes (row 1; row 12 is textual occurrence)

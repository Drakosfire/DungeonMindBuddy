# GOLD-AUDIT — temporal_shadow_adversarial_v8

Independent TL01G promotion adversarial authored after prompt-only freeze `67408bd8…`. Novel constructions (no race/hold V5/V6 templates; disjoint from V7). Sealed before first provider run on this cohort.

| Assertion ID | Assertion proposition | Gate B eligibility | Proposition class | Gold status | Gold lane | Supporting phrase | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:54abc8ee0063987b` | Calyx Thorne confirms the Emberleaf Index opens tomorrow | eligible | forecast-with-time | resolved | occurrence (textual) | `opens tomorrow` | unresolved despite explicit tomorrow (V7 defect) | Supported |
| `assertion:8dcf5c7d478a2612` | Merridan pledged the Stormglass Causeway vault will reopen | eligible | future-promise | unresolved | none | `will reopen once Rookhaven is secure again` | resolved occurrence without execution-time phrase | Supported |
| `assertion:1f441d9524c742ec` | Merridan remains quartermaster of the Cinder Compact | not | persistent-restatement | not_applicable | none | `Merridan remains quartermaster of the Cinder Compact` | resolved occurrence from eventive wording | Supported |
| `assertion:014ea4f4c1f7fc2a` | Calyx Thorne secured the Emberleaf Index ledger | eligible | occurrence | resolved | occurrence (session) | `After the Stormglass Causeway beacon topples, Calyx Thorne secures` | not_applicable state restatement | Supported |
| `assertion:1463a94a4bbb16d9` | The Emberleaf Index has been sealed | eligible | valid-start-textual | resolved | valid-start (textual) | `has been sealed for no more than a fortnight` | session source time as start | Supported |
| `assertion:ba1dfafca14abf82` | Merridan keeps the Cinder Compact keys | eligible | valid-end | resolved | valid-end (session) | `no longer keeps the Cinder Compact keys` | occurrence-only without end boundary | Supported |
| `assertion:2be86ce1954e91ce` | Calyx Thorne still serves Rookhaven | not | still/remains | not_applicable | none | `still serves Rookhaven` | valid-start from still-state | Supported |
| `assertion:ea3165b10d3c0a33` | Calyx Thorne holds or recovered the Emberleaf Index at the quay fire | eligible | proposition-ambiguous | ambiguous | none | `holds the Emberleaf Index since the quay fire, or maybe Merridan only recovered it then` | resolved custody without proposition fork | Supported |
| `assertion:d3b60b24092b0a35` | Merridan left the Stormglass Causeway | eligible | historical | resolved | occurrence (textual) | `about forty years ago` | session-15 source time for historical departure | Supported |
| `assertion:7e167c0ecc5e572d` | Calyx Thorne opened the Emberleaf Index at the quay | eligible | grounding-trap | unresolved | none | `claims he opened the Emberleaf Index` | resolved with object NP `Cinder Compact oath-bell` as raw_expression (V7 defect) | Supported |

## Coverage

- future with grounded time (tomorrow): yes (row 1)
- future promise without execution time: yes (row 2)
- eventive-on-state NA: yes (row 3)
- event occurrence: yes (row 4)
- textual valid-start: yes (row 5)
- valid-end: yes (row 6)
- still/remains NA: yes (row 7)
- proposition-level ambiguous: yes (row 8)
- historical source-diff: yes (row 9)
- grounding trap unresolved: yes (row 10)

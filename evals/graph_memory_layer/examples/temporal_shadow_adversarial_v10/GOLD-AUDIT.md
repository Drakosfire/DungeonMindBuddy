# GOLD-AUDIT — temporal_shadow_adversarial_v10

Independent TL01G promotion adversarial authored after prompt freeze `3af1e470…`. Gate E2 faithful (textual occurrence/end, not session). Sealed before first provider run.

| Assertion ID | Assertion proposition | Gate B eligibility | Proposition class | Gold status | Gold lane | Supporting phrase | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:77aea867bb3dbc8a` | The supply barge reaches Sable Quay at dusk | eligible | forecast-with-time | resolved | occurrence (textual) | `at dusk` | unresolved despite explicit dusk phrase | Supported |
| `assertion:0f2eff82753b4879` | Liora Venn vows to petition the Paleoak Compact when she is ready | eligible | future-promise | unresolved | none | `when she is ready, naming no day` | resolved occurrence without execution-time phrase | Supported |
| `assertion:6d3818f2bfe92fb1` | Cartography duties for Mistglass Causeway still rest with Liora Venn | not | persistent-restatement | not_applicable | none | `still rest with Liora Venn` | resolved occurrence from eventive wording | Supported |
| `assertion:6e23891b620a0c97` | Liora Venn transfers the Thornledger Atlas to the Cairnwick clerk before the tide-gate seals | eligible | occurrence-textual | resolved | occurrence (textual) | `Before the tide-gate seals` | session source_time (Gate E2 defect) | Supported |
| `assertion:ea69d4c08a9e2373` | Archivists note the Thornledger Atlas has been closed since midwinter | eligible | valid-start-textual | resolved | valid-start (textual) | `since midwinter` | session source time as start | Supported |
| `assertion:89f983c69ca1a2b4` | Liora Venn no longer speaks for the Paleoak Compact following the river vote | eligible | valid-end-textual | resolved | valid-end (textual) | `following the river vote` | session source_time (Gate E2 defect) | Supported |
| `assertion:c245fb913a7f6cb3` | Liora Venn still refuses every Cairnwick summons | not | still/remains | not_applicable | none | `still refuses every Cairnwick summons` | valid-start from still-state | Supported |
| `assertion:a0f0ef0556974ada` | Liora Venn was elected chancellor at the solstice moot or only announced then | eligible | proposition-ambiguous | ambiguous | none | `elected chancellor at the solstice moot or only announced then` | resolved election without proposition fork | Supported |
| `assertion:6cea20d1de125912` | Liora Venn left the coast three winters earlier | eligible | historical | resolved | occurrence (textual) | `three winters earlier` | session source time for historical departure | Supported |
| `assertion:2be1e229a5db3a88` | Liora Venn claims the Thornledger Atlas is opening now | eligible | grounding-trap | unresolved | none | `claims the Thornledger Atlas is opening now` | resolved with harbor gong as raw_expression | Supported |

## Coverage

- future with grounded time (dusk): yes (row 1)
- future promise without execution time: yes (row 2)
- persistent restatement NA: yes (row 3)
- event occurrence textual (Gate E2): yes (row 4)
- textual valid-start: yes (row 5)
- valid-end textual (Gate E2): yes (row 6)
- still/remains NA: yes (row 7)
- proposition-level ambiguous: yes (row 8)
- historical textual: yes (row 9)
- grounding trap unresolved: yes (row 10)

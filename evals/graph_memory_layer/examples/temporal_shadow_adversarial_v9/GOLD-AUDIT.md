# GOLD-AUDIT — temporal_shadow_adversarial_v9

Independent TL01G promotion adversarial authored after prompt freeze `67408bd8…`. Gate E2 faithful (textual occurrence/end, not session). Sealed before first provider run.

| Assertion ID | Assertion proposition | Gate B eligibility | Proposition class | Gold status | Gold lane | Supporting phrase | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:ea73946bbeaeab04` | Quorin Hale reads that the Amberquill Codex opens tomorrow | eligible | forecast-with-time | resolved | occurrence (textual) | `opens tomorrow` | unresolved despite explicit tomorrow | Supported |
| `assertion:ac15be5e6c616661` | Velessa Mar vows the Frostmere Causeway vault will reopen | eligible | future-promise | unresolved | none | `with no date named` | resolved occurrence without execution-time phrase | Supported |
| `assertion:499d287809bae583` | Quartermaster duties at the Thornwick depot fall to Velessa Mar | not | persistent-restatement | not_applicable | none | `still fall to Velessa Mar` | resolved occurrence from eventive wording | Supported |
| `assertion:751173f90fd7f895` | The Amberquill Codex ledger passes to Quorin Hale's custody | eligible | occurrence-textual | resolved | occurrence (textual) | `After the Frostmere Causeway beacon topples` | session source_time (V8 Gate E2 defect) | Supported |
| `assertion:4f9c81e9ebbb53c8` | Archivists note the Amberquill Codex has been sealed | eligible | valid-start-textual | resolved | valid-start (textual) | `has been sealed for no more than a fortnight` | session source time as start | Supported |
| `assertion:e97a448099a98811` | Velessa Mar released custody of the Ironroot Compact keys | eligible | valid-end-textual | resolved | valid-end (textual) | `after the Thornwick audit` | session source_time (V8 Gate E2 defect) | Supported |
| `assertion:fdb32e03b48c7e07` | Quorin Hale's Thornwick posting has not changed | not | still/remains | not_applicable | none | `posting has not changed` | valid-start from still-state | Supported |
| `assertion:8c5f71ae9a3e553f` | Quorin Hale kept the Amberquill Codex since the quay fire or only recovered it during that fire | eligible | proposition-ambiguous | ambiguous | none | `kept the Amberquill Codex since the quay fire, or he may only have recovered it` | resolved custody without proposition fork | Supported |
| `assertion:e5111722054d185e` | Velessa Mar settled in Thornwick after departing the Frostmere Causeway | eligible | historical | resolved | occurrence (textual) | `about forty years ago` | session source time for historical departure | Supported |
| `assertion:87b024606fc39c36` | Quorin Hale claims he opened the Amberquill Codex | eligible | grounding-trap | unresolved | none | `claims he opened the Amberquill Codex` | resolved with object NP as raw_expression | Supported |

## Coverage

- future with grounded time (tomorrow): yes (row 1)
- future promise without execution time: yes (row 2)
- eventive-on-state NA: yes (row 3)
- event occurrence textual (Gate E2): yes (row 4)
- textual valid-start: yes (row 5)
- valid-end textual (Gate E2): yes (row 6)
- still/remains NA: yes (row 7)
- proposition-level ambiguous: yes (row 8)
- historical source-diff: yes (row 9)
- grounding trap unresolved: yes (row 10)

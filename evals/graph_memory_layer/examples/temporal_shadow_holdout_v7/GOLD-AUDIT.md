# GOLD-AUDIT — temporal_shadow_holdout_v7

Fresh replacement for retired V6 promotion evidence. V6 remains sealed/immutable but is not promotion-authoritative after the forest-arrival gold integrity finding.

Sealed before first TL01F V7 provider run. No gold changes after execution.

| Assertion ID | Assertion proposition | Proposition type | Gold status | Gold lane | Supporting phrase | Source time | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:ae3203c2ac4871df` | Stafl played the Song of Shattering | event | resolved | Occurrence | `plays the Song of Shattering` | session-6 | valid-start would invent a lasting state the assertion does not claim | Supported |
| `assertion:f38f7d44e4890e99` | Winna is in charge of the Dustwalker cell door | state-start | resolved | valid-start | `Winna is placed in charge of the door` | session-8 | occurrence-only would treat the resulting custody role as a one-shot event | Supported |
| `assertion:ad8f9795792eb501` | Bonogo is compelled to attack the meatwings | state-end | resolved | valid-end | `Both Bonogo and Ephanna no longer feel compelled to attack the meatwings` | session-23 | occurrence-only would miss that the assertion is the ended compulsion state | Supported |
| `assertion:316efafeb04f34d7` | The farmhouse family are moss farmers | restatement | not_applicable | none | `discover that they are moss farmers` | session-18 | valid-start would invent a boundary from a bare occupational observation | Supported |
| `assertion:f8941f36b57d401e` | Wolf Manor basement contains a summoning circle | non-temporal | not_applicable | none | `the floor is painted to create a summoning circle` | session-14 | occurrence session-14 would confuse discovery time with topology | Supported |
| `assertion:142e4910f554c446` | The Reach roadside restaurant was abandoned | source-different | resolved | Occurrence | `only recently abandoned, no more than a week ago` | session-22 | copying session-22 would treat provenance as the abandonment time | Supported |
| `assertion:e2b2653aa56abc35` | The migrating forest will reach Mossford | event-forecast | resolved | Occurrence | `the forest is set to arrive at the town in 4-5 hours` | session-18 | copying session-18 would treat provenance as the arrival time and discard the explicit relative forecast | Supported |
| `assertion:8b08ee37c7050c8c` | Dustwalker is present in the Academy cell | ambiguous | ambiguous | none | `They discover the Dustwalker sitting in his cell, right where they left him` | session-12 | valid-start custody would ignore the contradictory death-then-cell reading | Supported |
| `assertion:e09663d1767d3dcc` | Lysandra will search city contacts and old records for Caelynn's missing person | unresolved-future | unresolved | none | `She will work through her contacts in the city and use her position to access old records` | session-3 | resolved occurrence or valid-start at session-3 would invent execution timing from a future-tense commitment only | Supported |

## Coverage checklist

- occurrence-only (session): yes
- occurrence textual relative forecast: yes (forest arrival)
- valid-start-only: yes
- valid-end-only: yes
- restatement not-applicable: yes
- non-temporal not-applicable: yes
- source-different: yes
- unresolved: yes (Lysandra contacts/records pledge)
- ambiguous: yes

Rejected during authoring: V6 forest-as-unresolved reading (indefensible under TemporalPoint textual/relative contract).

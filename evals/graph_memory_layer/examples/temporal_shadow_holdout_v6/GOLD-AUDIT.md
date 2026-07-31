# GOLD-AUDIT — temporal_shadow_holdout_v6

Sealed before first TL01F provider run. No gold changes after execution.

| Assertion ID | Assertion proposition | Proposition type | Gold status | Gold lane | Supporting phrase | Source time | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:130e2c303989e455` | Stafl played the Song of Shattering | event | resolved | Occurrence | `plays the Song of Shattering` | session-6 | valid-start would invent a lasting state the assertion does not claim | Supported |
| `assertion:694c0497d27efa0c` | Winna is in charge of the Dustwalker cell door | state-start | resolved | valid-start | `Winna is placed in charge of the door` | session-8 | occurrence-only would treat the resulting custody role as a one-shot event | Supported |
| `assertion:ae464c1577720f3a` | Bonogo is compelled to attack the meatwings | state-end | resolved | valid-end | `Both Bonogo and Ephanna no longer feel compelled to attack the meatwings` | session-23 | occurrence-only would miss that the assertion is the ended compulsion state | Supported |
| `assertion:9e895a8230bbe0b8` | The farmhouse family are moss farmers | restatement | not_applicable | none | `discover that they are moss farmers` | session-18 | valid-start would invent a boundary from a bare occupational observation | Supported |
| `assertion:32481ece274e25b6` | Wolf Manor basement contains a summoning circle | non-temporal | not_applicable | none | `the floor is painted to create a summoning circle` | session-14 | occurrence session-14 would confuse discovery time with topology | Supported |
| `assertion:bc93e34fa8b21796` | The Reach roadside restaurant was abandoned | source-different | resolved | Occurrence | `only recently abandoned, no more than a week ago` | session-22 | copying session-22 would treat provenance as the abandonment time | Supported |
| `assertion:5df8d8029cf5a34c` | The migrating forest will reach Mossford | unresolved | unresolved | none | `the forest is set to arrive at the town in 4-5 hours` | session-18 | resolved occurrence at session-18 would assert a future arrival that has not happened | Supported |
| `assertion:c18c29870e398a23` | Dustwalker is present in the Academy cell | ambiguous | ambiguous | none | `They discover the Dustwalker sitting in his cell, right where they left him` | session-12 | valid-start custody would ignore the contradictory death-then-cell reading | Supported |

## Coverage checklist

- occurrence-only: yes
- valid-start-only: yes
- valid-end-only: yes
- restatement not-applicable: yes
- non-temporal not-applicable: yes
- source-different: yes
- unresolved: yes
- ambiguous: yes

Rejected during authoring: none after final selection.

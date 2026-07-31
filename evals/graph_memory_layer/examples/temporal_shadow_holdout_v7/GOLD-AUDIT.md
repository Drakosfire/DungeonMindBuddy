# GOLD-AUDIT — temporal_shadow_holdout_v7

Corrective replay of retired V6 promotion gold — **not** fresh/independent promotion authority. Eight rows share V6 proposition identity (same assertion IDs after `cohort_tag` removal). Lysandra pledge row is new. V6 remains sealed/immutable.

Sealed before the corrective-replay promotion rerun. No gold changes after that execution.

| Assertion ID | Assertion proposition | Proposition type | Gold status | Gold lane | Supporting phrase | Source time | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:130e2c303989e455` | Stafl played the Song of Shattering | event | resolved | Occurrence | `plays the Song of Shattering` | session-6 | valid-start would invent a lasting state the assertion does not claim | Supported |
| `assertion:694c0497d27efa0c` | Winna is in charge of the Dustwalker cell door | state-start | resolved | valid-start | `Winna is placed in charge of the door` | session-8 | occurrence-only would treat the resulting custody role as a one-shot event | Supported |
| `assertion:ae464c1577720f3a` | Bonogo is compelled to attack the meatwings | state-end | resolved | valid-end | `Both Bonogo and Ephanna no longer feel compelled to attack the meatwings` | session-23 | occurrence-only would miss that the assertion is the ended compulsion state | Supported |
| `assertion:9e895a8230bbe0b8` | The farmhouse family are moss farmers | restatement | not_applicable | none | `discover that they are moss farmers` | session-18 | valid-start would invent a boundary from a bare occupational observation | Supported |
| `assertion:32481ece274e25b6` | Wolf Manor basement contains a summoning circle | non-temporal | not_applicable | none | `the floor is painted to create a summoning circle` | session-14 | occurrence session-14 would confuse discovery time with topology | Supported |
| `assertion:bc93e34fa8b21796` | The Reach roadside restaurant was abandoned | state-start | resolved | valid-start | `only recently abandoned, no more than a week ago` | session-22 | occurrence-only ignores attribute/state proposition; session-22 would treat provenance as start; not_applicable would ignore explicit start phrase | Supported |
| `assertion:5df8d8029cf5a34c` | The migrating forest will reach Mossford | event-forecast | resolved | Occurrence | `the forest is set to arrive at the town in 4-5 hours` | session-18 | copying session-18 would treat provenance as the arrival time and discard the explicit relative forecast | Supported |
| `assertion:c18c29870e398a23` | Dustwalker is present in the Academy cell | ambiguous | ambiguous | none | `They discover the Dustwalker sitting in his cell, right where they left him` | session-12 | valid-start custody would ignore the contradictory death-then-cell reading | Supported |
| `assertion:0cd480dde6597bfe` | Lysandra will search city contacts and old records for Caelynn's missing person | unresolved-future | unresolved | none | `She will work through her contacts in the city and use her position to access old records` | session-3 | resolved occurrence or valid-start at session-3 would invent execution timing from a future-tense commitment only | Supported |

## Coverage checklist

- occurrence-only (session): yes
- occurrence textual relative forecast: yes (forest arrival)
- valid-start-only (session): yes (Winna)
- valid-start textual (reject source session): yes (abandoned restaurant)
- valid-end-only: yes
- restatement not-applicable: yes
- non-temporal not-applicable: yes
- unresolved: yes (Lysandra contacts/records pledge)
- ambiguous: yes

Rejected during authoring:

* V6 forest-as-unresolved reading (indefensible under TemporalPoint textual/relative contract)
* V6/V7 restaurant-as-occurrence reading for an attribute `abandoned` state with an explicit start phrase (belongs in `valid_time.start`)
* `cohort_tag` in assertion `value` (evaluation-only label must not enter semantic identity or packet semantic_value)

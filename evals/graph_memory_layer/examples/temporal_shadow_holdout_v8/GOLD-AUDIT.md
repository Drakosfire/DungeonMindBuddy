# GOLD-AUDIT — temporal_shadow_holdout_v8

Independent TL01G promotion holdout. Sealed before first provider run. No gold changes after execution.

| Assertion ID | Assertion proposition | Proposition type | Gold status | Gold lane | Supporting phrase | Source time | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:5c4e790d3046ca34` | A boy warned that shadows are coming from the Reach and an alarm bell rang | event | resolved | Occurrence | `shadows are coming from the Reach` | session-23 | valid-start would invent a lasting state the alarm event does not claim | Supported |
| `assertion:2ddbdee66df3dde4` | The gathering storm will arrive | event-forecast | resolved | Occurrence (textual) | `the gathering storm will arrive in about seven hours` | session-21 (rejected for occurrence) | copying session-21 would treat provenance as arrival time and discard explicit relative forecast | Supported |
| `assertion:961be3344354ca71` | Mirathorn Council instituted a curfew | state-start | resolved | valid-start | `The Mirathorn Council has instituted a curfew` | session-13 | occurrence-only would treat the resulting curfew as a one-shot event | Supported |
| `assertion:ff392152c6bf1ce2` | Frank has been compromised | state-start (source-different) | resolved | valid-start (textual) | `it appears he has been compromised` | session-22 (rejected for start) | copying session-22 as start would treat spoken-in-session report as the compromise boundary; textual `has been compromised` is defensible | Supported |
| `assertion:a572398539c61220` | Ephanna is compelled to attack the meatwings | state-end | resolved | valid-end | `Ephanna no longer feel compelled to attack the meatwings` | session-23 | occurrence-only would miss that the assertion is the ended compulsion state | Supported |
| `assertion:d74124ff46698f0f` | The term Reaches originated from early settlement | historical event | resolved | Occurrence (textual) | `The term "Reaches" originated from the early days of settlement` | none (world doc) | session provenance unavailable; not_applicable would ignore explicit historical phrase | Supported |
| `assertion:56855181d5da17d9` | Orik Tane is mayor | restatement | not_applicable | none | `As mayor, Orik Tane` | session-23 | valid-start would invent an appointment the evidence does not state | Supported |
| `assertion:a520c570c9c7c82a` | Wolf Manor library has a wall full of books | non-temporal structure | not_applicable | none | `a wall full of books` | session-4 | occurrence session-4 would confuse discovery time with topology | Supported |
| `assertion:4168dacb57687edf` | Karsemine promised to speak to someone at the Academy on Winna's behalf | unresolved-future | unresolved | none | `Karsemine had promised to speak to someone at the Academy on her behalf` | session-2 | resolved occurrence or valid-start at session-2 would invent execution timing from a future-tense commitment only | Supported |
| `assertion:048402f4a022f344` | The group needs to get to the other side of the migration and reach the vanguard trees | unresolved-plan | unresolved | none | `the group needs to get to the other side as quickly as possible` | session-15 | copying session-15 as occurrence would conflate plan urgency with a grounded event time | Supported |
| `assertion:5e1517e61c74aafb` | The migrating forest reached the fortifications when the plan succeeded and fires were lit | ambiguous | ambiguous | none | `As the forest finally reaches the fortifications, the fires are lit` | session-20 | choosing only occurrence or only valid-start would hide competing event vs plan-success readings | Supported |
| `assertion:c17a577a4291f915` | The dragon scale's origin and identity are uncertain | ambiguous-identity | ambiguous | none | `it was not of a dragon that currently exists` | session-1 | resolved occurrence or valid-start would force a single identity reading without unique-lane proof | Supported |

## Coverage checklist

- occurrence-only (session): yes (row 1)
- occurrence textual/relative forecast: yes (row 2)
- valid-start-only (session): yes (row 3)
- valid-start textual (reject source session): yes (row 4)
- valid-end-only: yes (row 5)
- historical textual occurrence: yes (row 6)
- restatement not-applicable: yes (row 7)
- non-temporal not-applicable: yes (row 8)
- unresolved future pledge: yes (row 9)
- unresolved plan without grounded value: yes (row 10)
- ambiguous competing readings: yes (row 11)
- ambiguous identity: yes (row 12)

## Rejected during authoring

* Session 23 L20 “Questionable Company in charge” span — same source fingerprint as row 1; replaced with Session 20 L26 forest/fortification ambiguity.
* Frank compromised as session-22 valid-start — historical-state phrasing in evidence favors textual start with `has been compromised`.
* Copying session-21 as storm arrival occurrence — explicit `in about seven hours` wins over provenance.

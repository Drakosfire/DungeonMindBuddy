# GOLD-AUDIT — temporal_shadow_holdout_v10

Independent TL01G promotion holdout. Sealed before first provider run. No gold changes after execution.

| Assertion ID | Assertion proposition | Gate B eligibility | Proposition class | Gold status | Gold lane | Supporting phrase | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:b1032ae92c80e8a6` | Baergrom pushed Morvian the Ashen out of the ring | eligible | occurrence | resolved | occurrence (session) | `pushes the monk out of the ring` | valid-start from session-2 provenance alone | Supported |
| `assertion:7bb98055a894cfe1` | The group will reach Mireward around ten o'clock | eligible | forecast | resolved | occurrence (textual) | `around 10 o'clock` | copying session-22 as occurrence without textual phrase | Supported |
| `assertion:8acef589e3c3449f` | Lysandra is addressed as Lieutenant Lysandra | eligible | valid-start-session | resolved | valid-start (session) | `Lieutenant Lysandra now` | occurrence-only without persistent-state start boundary | Supported |
| `assertion:b955e363ef90527e` | Guardhouses host a guards-only music festival that has not happened before | eligible | valid-start-textual | resolved | valid-start (textual) | `has not happened before` | session-5 source time as start boundary | Supported |
| `assertion:1afbc930bb497328` | The Mirathorn festival has been postponed | eligible | valid-end | resolved | valid-end (textual) | `has been postponed` | occurrence at session-15 travel beat | Supported |
| `assertion:5b61a772b50e37f7` | Lysandra left Delwen Rast about eight years ago | eligible | historical | resolved | occurrence (textual) | `~8 years ago` | session source time for historical departure | Supported |
| `assertion:25855c24db471810` | The town square still has a large hole in the ground | not | persistent-restatement | not_applicable | none | `still in the ground` | valid-start from mere still-state (V9 Lysandra-rest defect) | Supported |
| `assertion:9a891f57fd6f4649` | Ephanna's fossil is porcelain rather than a real fossil | not | identity/classification | not_applicable | none | `this fossil is a fake` | ambiguous identity fork (V9 scale-or-extant defect) | Supported |
| `assertion:1f40f6a3f97f3904` | The group must decide whether to continue to the swamp or turn back to Mirathorn | eligible | unresolved-plan | unresolved | none | `must decide: continue on their mission to the swamp, or turn back` | resolved occurrence from session-21 narration time | Supported |
| `assertion:1312c2e8676ea1e3` | The group must track down the bard Dustwalker for answers | eligible | unresolved-commitment | unresolved | none | `need to track down that bard, Dustwalker` | not_applicable restatement | Supported |
| `assertion:8d106dfb3664e9d2` | The tree migration holds its usual schedule or broke from its usual path | eligible | proposition-ambiguous | ambiguous | none | `this migration is following neither` | resolved schedule occurrence without proposition-level fork | Supported |
| `assertion:3cd2267165a887e5` | A hooded figure watched Bonogo from the Coliseum stands | eligible | occurrence | resolved | occurrence (session) | `feeling of being watched` | not_applicable observation without event | Supported |

## Coverage checklist

- occurrence-only (session): yes (rows 1, 12)
- occurrence textual/relative forecast: yes (row 2)
- valid-start-only (session): yes (row 3)
- valid-start textual (reject source session): yes (row 4)
- valid-end-only: yes (row 5)
- historical textual occurrence: yes (row 6)
- restatement not-applicable: yes (row 7)
- identity/classification not-applicable: yes (row 8)
- unresolved future/plan: yes (rows 9–10)
- proposition-level temporal ambiguous (`or` in label): yes (row 11)

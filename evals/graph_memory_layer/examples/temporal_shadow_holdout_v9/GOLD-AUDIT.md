# GOLD-AUDIT — temporal_shadow_holdout_v9

Independent TL01G promotion holdout. Sealed before first provider run. No gold changes after execution.

| Assertion ID | Assertion proposition | Proposition type | Gold status | Gold lane | Supporting phrase | Source time | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:55773972170d06dc` | A huge meteor crashed down into the arena | occurrence | resolved | see gold | `a huge meteor crashes down into the arena` | see gold | see diagnostics | Supported |
| `assertion:9d5330af5e3759ac` | The migrating forest trees will reach Mossford | forecast | resolved | see gold | `the trees would reach Mossford in a day and a half` | see gold | see diagnostics | Supported |
| `assertion:7069c33bb7dba633` | Lysandra agreed to deputize the adventurers | valid-start-session | resolved | see gold | `agrees to deputize the adventures` | see gold | see diagnostics | Supported |
| `assertion:eecb5985f067e703` | Lysandra has not been able to get any rest | valid-start-textual | resolved | see gold | `she has not been able to get any rest` | see gold | see diagnostics | Supported |
| `assertion:102e5a65f91f360b` | The crystal is neutral | valid-end | resolved | see gold | `The crystal is no longer neutral` | see gold | see diagnostics | Supported |
| `assertion:89e69b985a6e9c64` | The gods lost to the other things long ago | historical | resolved | see gold | `Long ago, the gods lost to the other things` | see gold | see diagnostics | Supported |
| `assertion:f14a35b4a2bccbd2` | Karsemine, Ephanna and Bonogo signed up for the costume contest | restatement-na | not_applicable | see gold | `head to Miss Thistlebottom’s Emporium to sign up for the costume contest` | see gold | see diagnostics | Supported |
| `assertion:f304db98b752c5e0` | The forest has an enormous web of roots acting as a bowl holding water | structure-na | not_applicable | see gold | `an enormous web of roots acting as a bowl holding water` | see gold | see diagnostics | Supported |
| `assertion:5f367431e38a0dc5` | Bonogo hopes to find answers about his cursed letter at the Gilded Fold | unresolved-future | unresolved | see gold | `Bonogo leaves the manor in search of the Gilded Fold` | see gold | see diagnostics | Supported |
| `assertion:d60eaab03fc3fafe` | The group must make a final decision on the next steps toward Mossford | unresolved-plan | unresolved | see gold | `The group must make a final decision on the next steps` | see gold | see diagnostics | Supported |
| `assertion:c46d76facdaf39c7` | The Apex of the Canopy has been tracking the party or emerges from the mist | proposition-ambiguous | ambiguous | see gold | `the wyvern that has been tracking them emerges from the mist` | see gold | see diagnostics | Supported |
| `assertion:602f7c788b16559f` | The dragon scale is from an extinct dragon or from a dragon that currently exists | ambiguous-identity | ambiguous | see gold | `it was not of a dragon that currently exists` | see gold | see diagnostics | Supported |

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
- proposition-level ambiguous (or in label): yes (row 11)
- ambiguous identity: yes (row 12)

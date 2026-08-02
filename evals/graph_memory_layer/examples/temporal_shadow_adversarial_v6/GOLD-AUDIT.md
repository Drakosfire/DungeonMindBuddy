# GOLD-AUDIT — temporal_shadow_adversarial_v6

Sealed before first TL01G provider run. No gold changes after execution.

Reserved vocabulary: `Kestrel Vale`, `Briarwick`, `Nymera`, `Ironreed Causeway`, `Saltglass Register`, `Dawnspine Compact`.

| Assertion ID | Assertion proposition | Proposition type | Gold status | Gold lane | Supporting phrase | Source time | Rejected alternative | Audit result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `assertion:f9c1ab0f287836b9` | Nymera promised to deliver the Saltglass Register to the Dawnspine Compact | future promise | unresolved | none | `promised to deliver the Saltglass Register to the Dawnspine Compact before the next moon` | session-14 | resolved occurrence at session-14 would invent execution time from commitment only | Supported |
| `assertion:22c520837a9412a0` | The storm rolling down the Ironreed Causeway will arrive | relative forecast | resolved | Occurrence (textual) | `will arrive in about three hours` | session-12 (rejected) | copying session-12 ignores explicit relative forecast phrase | Supported |
| `assertion:ebf11828bd139342` | Nymera holds the Saltglass Register for Kestrel Vale | eventive-evidence-on-state | not_applicable | none | `Nymera as she continues to hold the Saltglass Register` | session-12 | occurrence would follow the race verb instead of the stable-state assertion | Supported |
| `assertion:0da780f066aa0084` | The Dawnspine Compact envoy sealed Briarwick against Kestrel Vale raiders | stative-wording-on-event | resolved | Occurrence | `she seals Briarwick against Kestrel Vale raiders` | session-12 | not_applicable restatement would ignore the sealing event | Supported |
| `assertion:fc2d5410a9718cef` | Nymera reports to the Dawnspine Compact hall in Briarwick | state-start textual | resolved | valid-start (textual) | `Only since the Saltglass Register was opened last winter has Nymera reported` | session-9 (rejected) | occurrence-only would mis-lane a persistent reporting relationship | Supported |
| `assertion:02449b27060f145c` | Nymera controls the Ironreed Causeway seal | state-end | resolved | valid-end | `Nymera no longer controls the Ironreed Causeway seal` | session-11 | occurrence-only would convert an end boundary into an event lane | Supported |
| `assertion:9e0360f8db54db89` | Nymera serves with the Dawnspine Compact wardens along the Ironreed Causeway | still/remains | not_applicable | none | `Nymera still serves with the Dawnspine Compact wardens` | session-14 | copying session-14 as valid-start manufactures a boundary | Supported |
| `assertion:0961a0569de5e37c` | Nymera holds or recovered the Saltglass Register at the Briarwick fire | ambiguous lane | ambiguous | none | `has held the Saltglass Register since the Briarwick fire, or maybe she only recovered it then` | session-10 | choosing only valid-start or only occurrence would hide a genuine dual reading | Supported |
| `assertion:c8101a02448d4330` | Nymera left the Ironreed Causeway | source-different | resolved | Occurrence (textual) | `Nymera left the Ironreed Causeway about thirty years ago` | session-15 (rejected) | copying session-15 ignores the explicit historical phrase | Supported |
| `assertion:e3e1a47d21a94a23` | Nymera opened the Saltglass Register at Briarwick | grounding trap | resolved | Occurrence (textual) | `opened the Saltglass Register at Briarwick yesterday` | session-8 (rejected) | paraphrase without verbatim substring fails Gate F; session-8 provenance rejected for explicit yesterday phrase | Supported |

## Coverage checklist

- future promise unresolved: yes
- relative forecast resolved textual: yes
- eventive on stable state not_applicable: yes
- stative wording on event resolved occurrence: yes
- valid-start textual: yes
- valid-end: yes
- still/remains not_applicable: yes
- occurrence vs valid-start ambiguity: yes
- source-different textual occurrence: yes
- grounding trap (verbatim required): yes

## Rejected during authoring

* Paraphrase-only grounding for the Saltglass Register opening — gold requires verbatim `opened the Saltglass Register at Briarwick yesterday`.
* Session-14 as execution time for Nymera's delivery promise — commitment only, no grounded execution expression.

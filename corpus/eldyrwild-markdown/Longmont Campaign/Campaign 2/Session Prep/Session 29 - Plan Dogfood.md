# Session 29 Plan content dogfood

Operator authorized exact source import and Plan translation, with extensive node use.

## Saved result

- Buddy World: `elderwyld`; native lookup World: `eldyrwild`, campaign `longmont-c2`.
- Plan: `d96904d1-d20d-4b78-8d22-c2c84d81cdc3`, committed revision 5.
- Original earlier Plan `9811d105-b075-4674-8358-0111bd458ce2` preserved.
- Source SHA256: `7628ff052ebb87e2e3a074e9a11b3f96753aab50b16c20a93a284a5ec76fc8d5`.
- Derived Plan contains 72 links across eight verified node IDs. Removing only added links reproduces the source exactly; all 90 v2 markers remain unchanged.
- Read-only native projection revision: `rev:680c246047d67f9fe0293ee90526f670` (469 nodes). Lookup performed outside the Agent. No graph admission or played-canon publication.

## Agent exercises and gaps

1. Ordinary Saved Plan Ask rejected 45,888-character committed source before provider execution: “The committed Plan is too large to include in one Agent turn. Shorten the Plan and try again.”
2. Compose at the opening caret, requesting a <=180-word quick reference with five supplied verified node links, rejected before provider execution: “This Plan source cannot round-trip safely; resolve its Markdown warnings first.” The full source was retained rather than stripped to defeat the guard.
3. Ordinary Saved Plan Ask explicitly uses `graph_request.mode=none`; its UI explains ordinary Ask remains graphless. This does not establish absence of Hermes Graph capability elsewhere.
4. Runbook choices explicitly permit simultaneous player actions, while current choice selection is single-option. Preserve that authoring intention for owning-runtime follow-up.

Both Agent failures were surfaced to PRIME. The content writer prepare/commit path accepted the exact source and linked derivative; reload verification checks the committed result. Missing/ambiguous node identities remain unlinked, including Brin Holloway, Nera Coalstep, Reeve Salla Vey, Mayor Orric Tane, Delwen Rast, Witness Seed, Maelthor and Meat Mind. No IDs or mechanics invented.

## Bounded content authority

Direct operator request owns this serial content-only lane, `codex/dogfood-session29-plan-content`, from fetched `origin/main`. Expected write set is this Session Prep directory only. No product code, runtime configuration, migrations, graph mutations, or changes to other active leases. Final transport is one content PR; merge requires separate authority. UI runtime ports 5202/7866 and existing app state were preserved.

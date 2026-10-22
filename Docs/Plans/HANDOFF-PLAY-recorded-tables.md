# PLAY — native recorded rolls for prepared tables

ACTIVE design-only lease. PRIME owns this serial design slice from Buddy
390c3cb1f6b7b63f6144661f3f838ebe4b8663b7 in the existing buddy-context-loop checkout,
branch codex/play-recorded-table-contract. Open PR census has no overlapping
native Play/table implementation. Exclusive writes: this file, predecessor
HANDOFF-COMBAT-direct-accepted-mechanics.md, the status/first-slice distinction in
HANDOFF-J6-content-roll-table-resource-v1.md, and Docs/Roadmaps/ROADMAP-demo.md.
Bugbot reviews the cumulative design. No runtime implementation or migration is
activated by this design-only lease. PRIME activates one separately pinned serial
implementation lease after review, naming exact paths and disposable APP54329
resources; existing retained APP54331/native54330 and services remain untouched.

## First useful capability

In a World Play Run, open Prepared tables in the existing shared Surface tool
host, select a table authored in the Run's originally pinned Plan/Runbook, enter
a physical integer, and save its deterministic result. Reopen the receipt after
navigation/reload/API restart without rerolling. No Rules/Jev/provider/RNG call.
This is an authored-table outcome, not an attack, recharge, damage roll or Combat
state. Combat remains independently owned; no HP moves into Run progress.

Architecture's read-only critique confirms the existing immutable Content pin
can supply table authority for this bounded embedded-table use case. The older
blocked reusable Content-resource design is not a prerequisite. It remains
unselected for independent table lifecycle/reuse across Runbooks.

## Exact table authority

A new explicit fenced code language `dmb-roll-table-v1` is admitted inside normal
Plan/Runbook Markdown. Its JSON has exactly schema_version=dmb_roll_table_v1,
table_id, title, die_sides and rows. Each row has exactly row_id,min,max,outcome.
Table IDs match table:[a-z0-9][a-z0-9._-]{0,127}; row IDs use the same tail with
row:. Table IDs are unique in the document; row IDs are unique within each table.
Title
and outcome are nonblank plain text. Numeric fields are strict integers, not
booleans/coerced strings. die_sides is at least2; rows in ascending order cover
1..die_sides exactly once with no gaps, overlaps, reversed or out-of-range bounds.
Reject duplicate JSON keys, unknown fields/versions, duplicate table/row IDs and
unterminated typed fences. Other fenced examples are ignored, including apparent
typed fences inside a longer example fence. Ordinary numeric Markdown tables,
reference chips, corpus IDs and legacy session mappings confer no authority.

The server loads and verifies the exact same-World immutable Playable pin already
bound to this Run: WorkObject UUID, revision number, WorkRevision UUID and SHA256.
It checks the existing sealed manifest/run binding, then parses typed membership
from those pinned bytes. This strict source-membership check avoids inventing a
new manifest generation solely to repeat the whole-document immutable pin.
The selected table ID and canonical parsed-table SHA additionally bind each
command. Never read a working copy or floating current revision, nor silently
follow edits to the Play session copy. UI says these are tables prepared when the
session started. A later source advance/discard cannot change the Run's table or
its saved outcomes. Source titles are shown to users; technical pins stay in
inspection. No new Content kind, source registry API, Graph identity or adapter.

## Play-owned append-only receipts

Use a dedicated Play receipt ledger, not the strict whole-object progress JSON.
One new next-head APP migration and one Run-locked unit of work own the append.
A command binds World, Run, expected Run revision, exact Playable/table pins,
caller UUID idempotency key and submitted physical integer. Verify ownership,
active/not-ended session, pinned membership and domain; resolve the row from
server-loaded source, increment Run revision without altering progress, and
append the receipt atomically. The receipt records expected/resulting Run
revision, original request digest/key, exact source/table pins, table/source title,
submitted value, stable row ID, outcome snapshot and timestamp.

Same key/same payload replays the original receipt, even after other Run changes;
changed payload conflicts. Replay cannot run resolution again. Rebase never
rewrites historical receipts; old source pins stay visible as historical. Reads
render receipt snapshots and never regenerate/re-resolve outcomes. Prevent SQL
update/delete of receipts; downgrade refuses nonempty history. Concurrent/stale,
wrong-World/pin, absent/malformed table, unsupported/out-of-range input, ended or
trashed session and tampered proof leave both Run and ledger unchanged.

The native lazy Surface component coordinates with existing Play mutation and
unsaved-note/session-copy guards. It updates the host's admitted Run revision
from a verified response without losing notes/scene position. Persist the exact
pending command locally before sending; on unknown transport outcome retain and
freeze it, offering explicit retry of that same UUID/payload. Never auto-submit,
change its expected revision, mint a replacement key or reroll on reopen. Known
conflict preserves entered values for an explicit refresh/new submission. Scope
pending state to World+Run+source basis; ignore late results after navigation.
Page receipt history on demand and render plain outcome text safely. Shared
Surface hosting does not move persistence authority into the component. Server
restart/reload retention is required; disconnected-browser operation is not
claimed by server persistence.

## Verification and real acceptance

Owner tests cover strict grammar (including fenced examples), exact historical
source after advance/discard, wrong owner/pins, deterministic range endpoints,
request replay/payload conflict, concurrent/stale CAS, atomic failure, append-only
SQL/downgrade protection, old Run/progress writers preserving receipts, lifecycle
holds, pagination and no model/provider calls. UI tests cover pending recovery,
unknown retry with original identity, host revision handoff, note/session-copy
holds, route races, safe outcomes and no implicit reroll. Existing Play/Content
contracts remain green. Review exact cumulative diff; Bugbot; PRIME merge;
guarded migration/API/UI adoption with retained-state/source fingerprints.

Real source gate is met: permitted Of Conks & Cons PDF physical page18, Appendix C,
contains explicit1d12 villager-name and nickname tables. Licensed rows remain in
private source/product state, not Git fixtures. Import/review that source through
ordinary Build and author the selected table faithfully into a saved Plan; start
its Run and enter a physical value. Save/reopen/restart the same receipt and
independently verify source/table/result identity without console/SQL/manual-ID
repair. Synthetic parser fixtures cannot substitute for this connected witness.
Sheep encounter/recharge prose is not a random table; do not invent one from it.
Broader twice-through J1–J6 and operator acceptance remain open.

## Settled predecessor

#1595 merged390c3cb1f after Bugbot approved1556a256f (131backend/56UI independent
checks). Initial nested store-lock P1 was fixed: all external proofs finish before
one short owning batch lock through APP CAS. API/UI390c3cb1f runs8000/5202.
Ordinary direct two-copy selection/save/reload/restart proved sourceHP55 with
independent tracker7/55 vs55/55, no World identity; original Plan/scene retained.
Subsequent ordinary Sheep Workbench generation/review/revise/validate/accept
produced Bear, greatsword Ape and conditional Bed Dragon assets. Encounter rev5
retains Noke+three grouped Apes+Bear, round2/current Noke, trackerHP53/17/19/19/34;
source stats unchanged. Restart retained1563 APP rows/79 product files/frozen
sources and Plan revision11/hash. This is an opponent-roster/turn witness, not
recorded-roll or complete adventure acceptance. Its write lease is released.

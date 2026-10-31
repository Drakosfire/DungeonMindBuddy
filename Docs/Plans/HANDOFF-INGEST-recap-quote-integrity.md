# INGEST: enforce literal quote integrity for recap candidates

Status: DELIVERED — implementation lease closed after exact-head review,
merge, and guarded runtime adoption. The next checkpoint is read-only
Session 29 evidence diagnosis; it grants no implementation lease.

Merged base: `origin/main@ee00a1a4ebbaa5eddba0240b358d4beebbef191c`.
Implementation branch: `codex/ingest-recap-quote-integrity` (closed).
Settlement branch: `codex/ingest-recap-quote-integrity-settlement`.
Checkout: `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`.
Topology: serial, one quote-integrity implementation PR, now merged; no new
implementation PR or runtime change is authorized by this settlement. PR #1396
(`codex/ingest-recap-quote-integrity`) merged at
`ee00a1a4ebbaa5eddba0240b358d4beebbef191c` from exact head
`0e4ad4774c4d9ade4840f19d32cfcf021798546f`. ARCHITECTURE cycle 1 passed the
exact head after 43 checks: 19 quote-integrity tests, 23 runner tests, and one
injected-failure check. PRIME owns merge and runtime delivery; both are now
complete for this slice. PR #1395
(`codex/ingest-recap-quote-correction-ui`) is delivered and its lease is closed
in this base; its settled handoff identifies this host quote-integrity
helper/runner/test lane as parallel-independent. PR #1235 is a disjoint Graph
Review UI slice. PR #1244 and #1394 are merged predecessors, with their settled
handoffs already in this base. The Session 29 gold context-link evaluation
lane uses separate files and is not a code dependency or publication authority
for this slice. No concurrent path or runtime ownership is introduced.

The handoff-only settlement is being committed on the merged parent for
PRIME's guarded fast-forward to main; it does not change the implementation
head reviewed above.

## Invariant

For the recap profile `recap_category_v1@1.0`, validate positive candidate
items at the host boundary after extraction returns but before persisting the
candidate component or advancing to `EXTRACTED`. The current production controller
stores candidate, span-index and entity-mention JSON bytes through the existing APP
output owner without duplicate JSON files. Locators are opaque labels; exact
run/kind/digest bindings own reads. The historical artifact hashes below describe
retained evidence from the original run, not a current filesystem requirement.
Every source-bearing evidence quote must match the exact canonical paragraph
for the candidate's source span using the existing normalized literal matcher
from `graph_memory.anchor_quotes.find_anchor_quote_matches`. Preserve that
matcher’s case, whitespace, Unicode quote and dash normalization. A literal
match proves provenance only; it does not prove entailment, identity, location,
modality, or relation semantics.

The validator is bound to the exact normalized source bytes, SourceArtifact ID,
source digest, and host-built canonical SourceSpanIndex. Recompute/verify the
digest and index binding, require valid artifact/ref/span ownership and
in-bounds canonical spans, and derive paragraph text only from those frozen
source bytes. Never trust text copied into a model response, a candidate
`context_anchor`/`corpus_ref`, cached quote matches, or a forged span. A
source/index/digest/ownership mismatch is a run validation failure, not an
empty-but-ready candidate and not a quote-only disposition.

If any quote on a positive item is missing, malformed, or not a normalized
literal in its exact pinned paragraph, defer the whole item with its stable
existing ID and a fixed typed reason code. Do not retain the item’s label,
description, relationship, or other claims as positive by salvaging its other
references. Deferred evidence may retain only independently verified literal
references; the invalid quote and complete original provider payload remain in
the existing private response artifact, byte-for-byte unchanged. Use existing
typed `deferred_items`; do not add a schema or rewrite candidate prose.

Audit all candidate-ID consumers when a node is deferred: edge endpoints,
Beat `involved_node_ids` and `unresolved_thread_node_ids`, source-observation
subjects, proposed-write targets, and any standing-link shape. Defer dependent
items with stable IDs and typed reasons where the current schema permits it.
If a dependent ID consumer cannot be represented by an existing typed
disposition, fail the run rather than silently leave a dangling reference or
perform a semantic rewrite. Idempotent replay must not duplicate dispositions.
Non-recap profiles and the separate trusted registry context projection remain
unchanged; if handling a trusted context item requires a new authority path,
stop and return for a lease amendment.

During implementation, source snapshots, private model/raw responses, and
previous run files were preserved. This code slice made no prompt change, fuzzy
or nearest-match rewrite, provider retry, new Process call, or World write. The
post-merge runtime adoption was performed separately by PRIME and is recorded
below. A technically reviewable candidate with deferred semantic claims is not
full Session 29 acceptance.

## Implementation write lease (closed)

- `Docs/Plans/HANDOFF-INGEST-recap-quote-integrity.md`: this authority and
  implementation evidence.
- `src/graph_memory/extraction/graph_preview_runner.py`: recap-only host
  validation before candidate persistence/hash and `EXTRACTED` state.
- `src/graph_memory/extraction/recap_quote_integrity.py`: new pure helper for
  exact source/index validation, quote checking, and typed deferral.
- `tests/test_recap_quote_integrity.py`: new helper and real persistence/reopen
  regressions using fake extraction output only.
- `tests/test_graph_preview_runner.py`: fixture adaptation or additional owning
  persistence coverage only if the new focused test cannot exercise the
  required boundary.

The lease applied to the implementation period and is now closed. The current
settlement branch changes this handoff only. The first implementation commit
pinned the contract; predecessor settlement was already recorded on main. Use
existing project dependencies and the standard isolated APP database fixture
on port 54329 for any authorized verification; no provider call or World write
was needed for this delivered slice.

## Acceptance contract and verification results

- Unit matrix: literal and normalized-equivalent quotes; multiple quotes;
  mixed valid/invalid references; empty/malformed quotes; cross-artifact or
  cross-source-ref evidence; forged/unknown spans; out-of-bounds ranges;
  mismatched digest/index; candidate-controlled context-anchor bypass; and
  idempotent repeat processing.
- Cascade matrix: defer the whole invalid node; defer each dependent edge;
  detect references from Beats, source observations, proposed writes and any
  standing links; fail closed for unsupported ID consumers; preserve
  independent valid nodes/edges/Beats and exact recap Beat excerpts.
- Persistence boundary: run with a deterministic fake category client, read the
  saved ExtractionRun and candidate back through ordinary inspection, and
  independently confirm positive source quotes pass the publication literal
  checker. Verify private raw response bytes and source snapshot/index bytes
  remain unchanged. No external provider or World write.
- Profile boundary: non-recap behavior remains byte/behavior equivalent under
  owning controls; the recap-specific check cannot affect worldbuilding or
  other profiles.
- Offline retained-run replay: process the exact saved candidate/source/index
  without mutating them. The observed change should defer
  `loc:tunnel-under-field` plus its two endpoint edges
  `edge:flesh-monster-chamber-part-of-tunnel` and
  `edge:baergrom-bonogo-scout-tunnel`, yielding 65 positive nodes, 63 positive
  edges, 13 Beats, and 7 deferred items if those are the only dependencies.
  Counts alone are not acceptance. Record unchanged hashes, all preserved
  positive items, exact deferred IDs/reasons, and the gold proposition impact.
  The current gold concepts to audit include `north_tunnel`, `tunnel_descent`,
  and `scout_execution`; state which are positive, deferred, or uncovered, and
  label any candidate-to-gold mapping that is only a semantic hypothesis. Do
  not claim full gold coverage where the mapping cannot be established; record
  the exact gap. Remaining identity, location, action/modality, and relation
  errors stay separate acceptance gates.
- Implementation head `0e4ad4774c4d9ade4840f19d32cfcf021798546f` passed
  ARCHITECTURE exact-head review cycle 1 with 43 checks: 19 focused
  quote-integrity tests, 23 owning-runner tests, and one injected-failure
  check. The owning runner log is
  `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy/.pytest_cache/prime-quote-integrity-runner.log`.
- Scoped Ruff, in-memory Python compilation of the changed Python files, and
  `git diff --check` passed. The persistence test passed while PRIME's
  disposable PostgreSQL fixture was active; a subsequent non-database rerun
  passed 18 tests after the fixture was stopped. The code head did not change.
- PR #1396 was committed, pushed, reviewed, and merged. PRIME completed the
  guarded two-file runtime adoption; proof is recorded in the delivery section
  below. No new ingestion Process or World publication was performed by this
  implementation lane.

## Predecessor settlement

PR #1394 merged at
`a2778b5a18d9f20985d8ded96f8b9cf4a6ed2a50` from implementation head
`c6836bcf296d58a68e5dab16d42eb6b1bb8ba9e6`. PRIME reports one ARCHITECTURE
exact-head review cycle and six focused tests. Deployment proof is
`/home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016/failed-step-rollout.json`:
the runtime module SHA was
`d9fbac666ee1817972d1323ec48130da9c9e2c3c6f6f959d8f6076b431cfc6db`, API PID
355155, and retained state was unchanged. This closes the failed-step
projection lease; it does not establish Session 29 semantic acceptance.

## Offline retained-run replay evidence

Replay input was the immutable retained run
`feb54858-4f22-449f-a59b-82555618f47f` under
`out/graph_memory/runs/longmont-c2/session-29/20261018T005318Z/extraction_run/`.
No provider, Process, or World write was used. The source, index, and original
candidate files remained byte-identical at SHA-256:

- `source.md`: `2bfe3db6a204de5b8638a041027eb71e5d61159f80f8c209ece848e043d6ebbf`
- `source_span_index.json`: `fb2508cd17355ce12476f0f674d9e61db8b8265bdc58ca4834fd0cf9dcd8c8c5`
- `candidate_graph.json`: `834fe6987b02a144a54f60e074df872dffb0a1411b500043fc3942cf24cb41db`

The sanitized serialized candidate SHA-256 is
`620ce793d25ec11a6819159b61afa09331787815882b331134b0f6aec4b9a337`.
It preserves the source candidate's schema version `0.1` and does not add the
absent `source_observations` collection. The recap candidate integrity
classifier reported no document-integrity errors, and the recap profile
post-extraction validator returned no errors. The existing packaging literal
quote checker accepted all 215 positive evidence references (226 quotes); no
quote failed. The helper recomputed 232 verified quotes across positive and
existing deferred items, checked 222 refs and 144 positive items, and deferred
three new items. The retained run has no aggregate `RAW_RESPONSE` component,
but its parent `extraction_run/.private/generationengine_attempts/` directory
does retain the per-pass provider attempt files and normalized actor response.
Their hashes were recorded before and after this offline replay and were
unchanged:

| Retained provider artifact | SHA-256 |
| --- | --- |
| `01-actor_pass-attempt-01.json` | `9328c9a648f747da1c03482f0b48a8997edf83df667338e64988f1b225855d54` |
| `01-actor_pass-normalized.json` | `66c2ca3ac609e69720d4dcc4e004e8120f263c0046e499ca7178476e4998b5a6` |
| `02-location_pass-attempt-01.json` | `0107fe2e8717582d5039789599c095fd54b721a84f0daabacb07b40ecdd4e95c` |
| `03-collective_pass-attempt-01.json` | `5ab3c4899bee87c7e378c339e8c3f41c0c6aa5b4960edb960a74a0896a84cd3f` |
| `04-object_pass-attempt-01.json` | `4cefc29a25acf5a0546a0ae5ceec4da23b156682bfdfe40c4cf6b60c93b78c6b` |
| `05-thread_pass-attempt-01.json` | `e93887c871b5b752d5449c5555c86ff33bd419e2028bb7863ff32807fe7021e5` |
| `06-beat_pass-attempt-01.json` | `46611924f9d218a642b200d912505f62255db7adb53f028cb21ed46ce4199995` |
| `07-edge_pass-attempt-01.json` | `60d2642821480a7e3c7f6db57313bc272be9e1400eb7619c5315e14128ccd8ee` |
| `08-pc_claimed_fill_pass-attempt-01.json` | `ecb838d6b9bdd1be959112aecd04b1bc81086f49db82137454f875b367d84ffb` |

The separate deterministic persistence test verified that newly retained
aggregate raw-response bytes, source snapshot, and span index are unchanged.

New dispositions are exactly:

- `loc:tunnel-under-field` — `recap_nonliteral_anchor_quote`.
- `edge:flesh-monster-chamber-part-of-tunnel` —
  `recap_dependency_on_quote_deferred_item`.
- `edge:baergrom-bonogo-scout-tunnel` —
  `recap_dependency_on_quote_deferred_item`.

The output has 65 positive nodes, 63 positive edges, 13 Beats, and 7 total
deferred items (the four original deferred items plus the three above). The
preserved positive node IDs are:

```text
node:hesta, node:brin, node:fellinor, node:grobnok,
node:professor-cinderbranch, node:flesh-monster-mireward-tunnel,
node:edge-flesh-monster, node:ogonob, node:black-cat-familiar,
loc:mireward-reach, loc:edge, loc:south-gate, loc:north-gate,
loc:road-to-fin, loc:warehouse, loc:apothecary, loc:inn,
loc:lysandros-house, loc:flesh-monster-chamber, loc:swamp,
loc:bayou-north-road, loc:mossford, loc:mirathorn,
loc:fellinor-edge-house, loc:fellinor-edge-warehouse, loc:edge-cellar,
group:questionable-company, group:mireward-reach-townsfolk,
group:mireward-reach-refugees, group:edge-guards,
group:mireward-reach-defenders, node:witness-seed,
node:alchemists-fire, node:greater-healing-potions,
node:healing-potions, node:cure-potion, node:sleeping-potions,
node:fellinor-safe, node:flesh-monster-lump,
mystery:psychic_force_pull, mystery:witness_seed_burden,
mystery:flesh_monster_in_tunnel, mystery:tunnel_below_flesh_monster,
mystery:edge_fall_history, mystery:fellinor_edge_resources,
mystery:cinderbranch_gossip, mystery:corruption_along_bayou,
mystery:swamp_source_of_problem, clue:alchemists_fire_kills_flesh,
clue:monsters_ceased_when_mind_died, clue:cure_potion_misting,
event:flesh_monster_ambush_and_slain, event:thrin_seed_resolution,
warning:lysandra_stays_behind, warning:infected_refugees_and_hesta,
thread:journey_to_edge, thread:send_word_to_mossford,
node:baergrom, node:bonogo, node:caelynn, node:ephanna,
node:karsemine, node:stafl, node:thrin-branchborn,
node:captain-lysandra-ironveil
```

The preserved positive edge IDs are:

```text
edge:hesta-located-in-apothecary, edge:hesta-owns-apothecary,
edge:hesta-hands-sleeping-potions-lysandra,
edge:hesta-creates-cure-potions-for-refugees,
edge:hesta-hands-sleeping-potions-warehouse,
edge:witness-seed-carried-by-thrin, edge:thrin-feels-psychic-pull,
edge:ephanna-feels-psychic-pull, edge:caelynn-asks-thrin-shoulder,
edge:karsemine-spots-monsters-warehouse, edge:baergrom-attacks-monsters,
edge:bonogo-sneak-attacks-monsters, edge:stafl-asks-lysandro-supplies,
edge:lysandro-gives-alchemists-fire,
edge:lysandro-gives-greater-healing-potions,
edge:stafl-pours-alchemists-fire, edge:flesh-monster-in-tunnel-chamber,
edge:flesh-monster-causes-psychic-force,
edge:flesh-monster-charms-baergrom-bonogo,
edge:flesh-monster-charms-caelynn, edge:flesh-monster-created-town-monsters,
edge:thrin-attacks-flesh-monster, edge:karsemine-fire-bolt-tentacles,
edge:stafl-burns-flesh-monster, edge:ephanna-familiar-black-cat,
edge:black-cat-explores-tunnel, edge:brin-found-in-inn,
edge:party-asks-brin-about-edge, edge:bonogo-approaches-fellinor,
edge:fellinor-gives-bonogo-safe-details, edge:fellinor-owns-edge-house,
edge:fellinor-owns-edge-warehouse, edge:fellinor-edge-house-in-edge,
edge:fellinor-edge-warehouse-in-edge,
edge:mireward-reach-townsfolk-located-in-mireward,
edge:refugees-located-in-mireward, edge:warehouse-within-mireward,
edge:apothecary-within-mireward, edge:inn-within-mireward,
edge:south-gate-part-of-mireward, edge:north-gate-part-of-mireward,
edge:road-to-fin-near-south-gate, edge:edge-north-of-mireward,
edge:swamp-north-journey, edge:edge-cellar-within-edge,
edge:edge-flesh-monster-in-cellar, edge:edge-flesh-monster-attacks-edge,
edge:edge-guards-defend-edge, edge:caelynn-calls-grobnok-mirathorn,
edge:grobnok-at-mirathorn, edge:cinderbranch-with-grobnok-mirathorn,
edge:cinderbranch-mists-cure-potion, edge:grobnok-asks-about-swamp,
edge:send-word-to-mossford, edge:party-participates-journey-edge,
edge:party-travels-bayou, edge:ephanna-conceals-thrin,
edge:ephanna-present-with-ogonob, edge:thrin-feels-better-after-defeat,
edge:lysandra-stays-rebuild-mireward,
edge:mireward-defenders-kill-remaining-monsters,
edge:tunnel-below-flesh-at-chamber, edge:flesh-lump-located-in-chamber
```

The preserved Beat IDs are `beat:session29:01`, `beat:session29:02`,
`beat:session29:03`, `beat:session29:04`, `beat:session29:05`,
`beat:session29:06`, `beat:session29:07`, `beat:session29:08`,
`beat:session29:10`, `beat:session29:11`, `beat:session29:12`,
`beat:session29:13`, and `beat:session29:14`.

Gold impact is deliberately limited. The candidate tunnel location is deferred,
so gold `north_tunnel` has no positive one-to-one candidate representation.
Gold `tunnel_descent` is uncovered: the surviving `edge:tunnel-below-flesh-at-chamber`
only supports a tunnel below the monster after it burns away; it does not support
the gold `leads_to` proposition that the north tunnel slopes down past the first
chamber into a larger one. Gold `scout_execution` is also uncovered: the execution
quote appears as one verified quote on the deferred location node, but there is
no separate positive candidate relation for Baergrom and Bonogo actually scouting
together. The deferred `edge:baergrom-bonogo-scout-tunnel` is a planned
`travels_to` edge from Baergrom to the tunnel and does not establish either the
two-person plan relation or executed `scouts_with` relation. No gold proposition
is counted as accepted by this replay.

The retained-run replay is offline evidence for the host quote gate only. It is
not source-semantic acceptance or publication acceptance. After the exact-head
review, merge, and runtime delivery below, PRIME lifted the engineering hold on
regular operator Ingest dogfooding. This does not require or authorize an
automatic rerun of Session 10 or 29.

The retained inference ledger records 8 calls to
`deepseek/deepseek-v4.1-flash-1017`, 72,952 input tokens, 28,903 output tokens,
44,288 cached input tokens, 0 transport retries, and 0 conformance retries.
Summed provider latency is 113,734 ms and summed per-pass wall time is 116,389
ms; neither is end-to-end run latency. The ledger has no USD cost, so cost is
unknown, not zero. This gate and offline replay add no provider calls or token
spend.

The quote gate's gold-recall cost is not scored as a numeric recall delta because
the three deferred candidates do not establish one-to-one semantic matches to
gold propositions. At most, the deferred tunnel node is a hypothesis for the
gold `north_tunnel`, and the deferred Baergrom-to-tunnel edge is a partial
hypothesis for `scout_plan`; the former is now withheld and the latter omits
Bonogo as a relation endpoint and loses the intended modality. Gold
`tunnel_descent` was not fully represented even before this gate, and
`scout_execution` has no separate positive two-scout relation in the original
candidate; its source quote was on the deferred location item. Therefore no
candidate is counted as lost gold recall here. These are semantic coverage
gaps for the next extraction/evaluation work, separate from quote provenance.

## Post-merge review, runtime delivery, and operator boundary

PR #1396 merged at `ee00a1a4ebbaa5eddba0240b358d4beebbef191c` from reviewed
head `0e4ad4774c4d9ade4840f19d32cfcf021798546f`. The guarded two-file runtime
adoption was applied without a provider call. The rollout proof is
`/home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016/quote-integrity-rollout.json`.
It records `applied: true`, unchanged retained source/media/conversation/Plan/
run/artifact/attempt state, and unchanged Ingest UI serving SHA
`9f331e3f4912b6f480dd04ddc35738990a97719ef32e86ae1a96afe1c0c292e9`. Runtime
verification recorded API PID 411906, runner module SHA
`50ecc77718bf747f8c9c47526aa1ea9c1af38967838950541f726052cd063e3e`, and
quote-integrity helper SHA
`e8cc9858c326f32326eb6369492651404f1f4e9932c5c2fb0957a35adfeaac0e`.

The engineering hold on regular operator Ingest dogfooding is lifted. The
operator may use Process for an actual chosen recap, including Session 10 if
that is their choice, then inspect and review the candidate. This gate proves
literal quote provenance only; semantic identity, location, action/modality,
and relation acceptance remain pending, and no World publication is authorized
by this handoff. No Session 10 or Session 29 run was automatically repeated.

The saved Session 29 literal quote-correction preview remains available for
inspection. The operator may explicitly save its corrections as a separate
held child; that creates neither semantic acceptance nor publication.

## Next checkpoint: read-only Session 29 conflation diagnosis

PRIME authorized a bounded read-only investigation of two retained Session 29
endpoint conflations: the `Stafl asks Lysandro` edge targets Captain Lysandra
Ironveil's node, and supply edges labeled `Lysandro gives ...` use Captain
Lysandra's node as `from_node_id`.
Compare the frozen eight provider attempts, normalized actor response,
`identity_context.json`, retained candidate, and current connected gold/context
source. Identify the first stage where the names or endpoints conflate:
actor-pass omission, host identity resolution, or an edge-pass endpoint error.
Distinguish facts grounded directly in Session 29 from prior context. Preserve
Lysandro/Lysandra as distinct identities and inspect the actual supply claims.
Return the stage, evidence artifact hashes, and smallest proposed repair
contract/lease plus tests for ARCHITECTURE critique. This checkpoint authorizes
no edits, prompt changes, provider calls, new Process, or semantic fix. It does
not suspend the regular operator dogfooding boundary above.

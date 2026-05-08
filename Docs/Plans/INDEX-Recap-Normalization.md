# Index: Session recap originals → prepared `_normalized/` paths

**Schema:** `Docs/CONVENTION-Session-Recap-Normalization.md`
**Materializer:** `scripts/materialize_normalized_recaps.py` (re-run only for new sessions or after changing extraction rules)
**Last pass:** `normalized_on: 2026-05-08`

All prepared files live under `corpus/eldyrwild-markdown/Longmont Campaign/Campaign N/Session Recaps/_normalized/`.

| Campaign | Session | Status | Original (corpus-relative) | Prepared filename |
|----------|---------|--------|---------------------------|-------------------|
| C1 | 1 | done | `Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap 3-27-24.md` | `Session 01 - Stonebridge and Glowkindle Rats.md` |
| C1 | 2 | done | `.../Session 2 - Finishing the Job.md` | `Session 02 - Finishing the Job.md` |
| C1 | 3 | done | `.../Session 3 - The Stone Bridge Flood.md` | `Session 03 - The Stone Bridge Flood.md` |
| C1 | 4 | done | `.../Session 4 - The Grotesque Tree of Hempholm.md` | `Session 04 - The Grotesque Tree of Hempholm.md` |
| C1 | 5 | done | `.../Session 5 - Underneath Hempholm.md` | `Session 05 - Underneath Hempholm.md` |
| C1 | 6 | done | `.../Session 6 - The Road to Miraholm.md` | `Session 06 - The Road to Miraholm.md` |
| C1 | 7 | done | `.../Session 7 - Passing Mirathorn Gates.md` | `Session 07 - Passing Mirathorn Gates.md` |
| C1 | 8 | done | `.../Session 8 - Captain Lysandra Quest.md` | `Session 08 - Captain Lysandra Quest.md` |
| C1 | 9 | done | `.../Session 9 - Battle with the Meat Monsters.md` | `Session 09 - Battle with the Meat Monsters.md` |
| C1 | 10 | done | `.../Session 10 - Battle with the Meat Monsters.md` | `Session 10 - Thraxx and the Last Warehouse.md` |
| C1 | 11 | done | `.../Session 11 - Midnight Politics.md` | `Session 11 - Midnight Politics.md` |
| C1 | 12 | done | `.../Session 12 - One Persistent Bugbear or Sneaky Fucking Bugbear.md` | `Session 12 - The Persistent Bugbear.md` |
| C1 | 13 | done | `.../Session 13 - The Meaty and the Dead.md` | `Session 13 - The Meaty and the Dead.md` |
| C1 | 14 | done | `.../Session 14 - Into the Meat Grinder.md` | `Session 14 - Into the Meat Grinder.md` |
| C1 | 15 | done | `.../Session 15 - Into the Meat Grinder.md` | `Session 15 - Cult Tunnels and Captain Idris.md` |
| C1 | 16 | done | `.../Session 16 - Recap.md` | `Session 16 - Peacemaker Fiddle Meat Pile.md` |
| C1 | 17 | done | `.../Session 17 - Recap.md` | `Session 17 - Festival Aftermath Loose Ends.md` |
| C2 | 1 | done | `Longmont Campaign/Campaign 2/Session Recaps/Session 1 - Let the Games Begin.md` | `Session 01 - Let the Games Begin.md` |
| C2 | 2 | done | `.../Session 2 - Recap.md` | `Session 02 - Steel Fangs Colosseum.md` |
| C2 | 3 | done | `.../Session 3 - Recap.md` | `Session 03 - Storms Torbin and Shepherd.md` |
| C2 | 4 | done | `.../Session 4 - Recap.md` | `Session 04 - Wolf Manor Mage Duel.md` |
| C2 | 5 | done | `.../Session 5 - Recap.md` | `Session 05 - Lysandra Tea Guardhouse.md` |
| C2 | 6 | done | `.../Session 6 - Recap.md` | `Session 06 - Barn Fleshborn Shepherd Wake.md` |
| C2 | 7 | done | `.../Session 7 - Recap.md` | `Session 07 - Portals Tentacles Barn.md` |
| C2 | 8 | done | `.../Session 8 - Recap.md` | `Session 08 - Dustwalker Cellar Barin Party.md` |
| C2 | 9 | done | `.../Session 9 - Recap.md` | `Session 09 - Costume Contest Temple Aspitome.md` |
| C2 | 10 | done | `.../Session 10 - Recap.md` | `Session 10 - Festival Crafting Elementals.md` |
| C2 | 11 | done | `.../Session 11 - Recap.md` | `Session 11 - Coliseum Finals Tealeaf Tea.md` |
| C2 | 12 | done | `.../Session 12 - Recap.md` | `Session 12 - Dustwalker Globe Duel.md` |
| C2 | 13 | done | `.../Session 13 - Recap.md` | `Session 13 - Council Curfew Swamp March.md` |
| C2 | 14 | done | `.../Session 14 - Recap.md` | `Session 14 - Supplies Wolf Crypt Letter.md` |
| C2 | 15 | done | `.../Session 15 - Recap.md` | `Session 15 - Ride Out Mossford Ale.md` |
| C2 | 16 | done | `.../Session 16 - Recap.md` | `Session 16 - Thinking Tree Sneaking Forest.md` |
| C2 | 17 | done | `.../Session 17 - Migrating Forest and Thrin.md` | `Session 17 - Migrating Forest and Thrin.md` |
| C2 | 18 | done | `.../Session 18 - Recap.md` | `Session 18 - Wyvern Mother Fallen Spine.md` |
| C2 | 19 | done | `.../Session 19 - Recap.md` | `Session 19 - Mossford Plans Stuart Inn.md` |
| C2 | 20 | done | `.../Session 20 - Recap.md` | `Session 20 - Gnat Swarm Marla Lysandra.md` |

**Slug derivation:** sessions with non-generic titles reuse the title tail; generic `Session N - Recap` titles use curated slugs in `scripts/materialize_normalized_recaps.py` (`_SLUGS`).

**Note:** Breadcrumb artifacts under `evals/sentence_routing_retrieval_falsification/manual_labels/*.breadcrumbed.md` were built from **original** recaps; after switching ingest to `_normalized/` sources, regenerate those artifacts so tag-stripped text still matches.

## Retrieval-only smoke (2026-05-08)

Using existing manual breadcrumb artifacts (still aligned to **original** recap paths in YAML `source_recap_path`; body text unchanged vs. normalized siblings for S1–S3 / S20 narrative spans):

| Gold | Report artifact | `all_ok` |
|------|-----------------|----------|
| `gold/breadcrumb_query_natural_c1s1_v1.json` | `evals/sentence_routing_retrieval_falsification/artifacts/c1s1_norm_smoke.json` | true |
| `gold/breadcrumb_query_natural_c1s2_v1.json` | `artifacts/c1s2_norm_smoke.json` | true |
| `gold/breadcrumb_query_natural_c1s3_v1.json` | `artifacts/c1s3_norm_smoke.json` | true |
| `gold/breadcrumb_query_natural_v1.json` (C2S20) | `artifacts/c2s20_norm_smoke.json` | false |

C2S20 run: **Cost:** $0 (retrieval-only, no LLM). Failures are existing `missing_expected_route_hit` / route-gate scenarios (e.g. `q_lysandra_change_unresolved`), not evidence of corpus-path drift from `_normalized/` (breadcrumb file still references `Session 20 - Recap.md`).

C1S13: the normalized seed now exists at `evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.normalized.breadcrumbed.frontmatter_seed.md`; use `_normalized/Session 13 - The Meaty and the Dead.md` for routing-only refreshes.

## Routing-only refresh baseline (2026-05-08)

The current active breadcrumb baseline is the routing-only path, not the manual
breadcrumb smoke alone. C1S1-C1S3 still use the original recap paths because their
frontmatter seeds are aligned to those source paths. C1S13 uses the normalized recap
and normalized seed.

| Gold | Source recap mode | Report artifact | Result |
|------|-------------------|-----------------|--------|
| `gold/breadcrumb_query_natural_c1s1_v1.json` | original recap | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s1_routing_refresh_retrieval_only.json` | 14/16 |
| `gold/breadcrumb_query_natural_c1s2_v1.json` | original recap | `.../breadcrumb_query_natural_c1s2_routing_refresh_retrieval_only.json` | 15/15 |
| `gold/breadcrumb_query_natural_c1s3_v1.json` | original recap | `.../breadcrumb_query_natural_c1s3_routing_refresh_retrieval_only.json` | 12/13 |
| `gold/breadcrumb_query_natural_c1s13_v1.json` | `_normalized/` recap | `.../breadcrumb_query_natural_c1s13_routing_refresh_retrieval_only.json` | failing holdout |

**Cost:** four-run routing-refresh sum about `$0.136347`.

Baseline interpretation:

- C1S1 remaining failures are route-only under-tagging on explicit party-roster /
  PC-identity content; text evidence still retrieves.
- C1S2 is the clean control lane.
- C1S3 remaining failure is location hierarchy pressure: Grishna routes through
  `rivers_edge_pub`, not same-unit `stonebridge`.
- C1S13 remaining regression is alias/identity bridge loss: the refreshed artifact
  dropped `draven` from the necromancer kill unit relative to the prior routing-only
  sidecar.

Do not compare these routing-only reports directly against earlier LLM-synthesis
cohorts without separating retrieval-only gates from answer-synthesis gates.

# Of Conks & Cons end-to-end dogfood report

Status: IN PROGRESS — living evidence ledger
Branch: `dogfood/of-conks-end-to-end`
Current head: (recorded at each evidence milestone)
Dogfood date: 2026-08-31
Operator: Cursor agent (local operator machine)
World / campaign: `eldyrwild` / Hempholm (Longmont campaign canon); Plan WorkObject `bfbed067-30d8-486a-846b-824c713e6a49` (campaign_id `longmont-c2` from the live session packet — product-model context only; module content is graph-independent SOURCE)
Plan: `bfbed067-30d8-486a-846b-824c713e6a49` "Of Conks & Cons — Hempholm Adaptation" (kind=plan, target_session 23, content_status committed, WorkRevision 1 sha256 `4a6ba786…`)
Runbook: `3ae3eb70-6042-4d7a-be94-065045a6a45e` "Runbook — Of Conks & Cons: Hempholm" (kind=runbook, committed WorkRevision 2, 5040 bytes, v2 playable markers + dmb-node refs verified in APP-STATE)
Run: `fa299cd6-596a-448f-ba36-642b1d352983` (bound to Runbook WorkRevision 2, sealed content sha256 `660b8704…`, manifest 3098 bytes, active_run pointer `local`)

Canonical handoff: `Docs/Plans/HANDOFF-CON-READY-of-conks-end-to-end-dogfood.md`

## 0. Baseline

- Design base: `main` `24f7c25b49fdab8271b0d84d36e4a609b9832d69` (merge of PR #673, BF3B Scene-owned Decisions).
- Branch cut from `origin/main` at that exact SHA into worktree `DungeonMindBuddy-of-conks-end-to-end`.
- PR #674 `AGENT-INTERACTION: enable truthful Play Ask` is OPEN at head `c194c70947780d5248f938421615b28a262d7d37`. Its leased paths (union of §21 lease and changed files, including `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`, `apps/live-control-ui/src/api/liveApi.ts`, `apps/live-control-ui/src/api/types.ts`, `apps/live-control-ui/src/agentInteraction/**`, `apps/live_control_server/routes/agent.py`, `apps/live_control_server/services/agent_*`, `apps/live_control_server/services/hermes_graph_query.py`, `apps/live_control_server/services/live_agent_loop.py`, `apps/live_control_server/main.py`) are read-only to this branch until it merges.
- Runtime/state collision note (AGENTS.md invariant 5): this lane shares the operator-local APP-STATE PostgreSQL `dungeonbuddy_application_state` (127.0.0.1:54329) with other local worktrees. Lane servers use dedicated ports: API `127.0.0.1:8020`, Vite `127.0.0.1:5190`. The BF3B recut lane's servers (`8010`/`5180`) and the stale #670 servers (`8000`/`5173`) are not evidence for this branch.

### 0.1 Environment repair (operator-local, pre-journey)

- `dungeonmind-postgres-dev` Docker container had exited and lost its volumes' data. Restarted; APP-STATE `dungeonbuddy_application_state` recreated and migrated via `scripts/bootstrap_local_play.py apply` (all migrations applied).
- DungeonMind authority `dungeonmind_cutover_live` was absent. Restored from operator backup `/home/drakosfire/Projects/DungeonOverMind/.env-backup/eldyrwild-v4-repair-20260823T215423Z/dungeonmind_cutover_live.sql` (alembic `0006_existing_world_adoptions`). Restored content: 95 graph_contributions, 1 contribution_review, 1 finalized_review_publication, 83 source_artifacts / 83 source_revisions, 263 evidence_refs, 13 identity_decisions, 1 existing_world_adoption, 2 campaigns (`longmont-c1`, `longmont-c2`), 1 world_graph_head.
- Backup predated Buddy's pinned DungeonMind (`5ca5d688612349034f8ca490d465af166d883e6e`, whose tree carries `0007_reviewed_world_init`); projection failed closed with `authority_integrity` (missing reviewed-init receipt table). Migrated the restored DB `0006 → 0007` with DungeonMind's own alembic from a clean worktree at the pinned SHA (operator's dirty `cutover/adoption-source-classification-repair` checkout left untouched; temp worktree `DungeonMind-wt-dogfood-migrate`). Projection then served `isHead: true`, rev `rev:680c246047d67f9fe0293ee90526f670`.
- Vite initially failed with ENOSPC inotify exhaustion; stale lanes' servers had exited by recheck, freeing watchers (only `:8020` listening). Vite v6.4.2 up on `127.0.0.1:5190` with `VITE_LIVE_API_PROXY_TARGET=http://127.0.0.1:8020`.
- No product code changed for any of the above; environment-only repair, recorded per handoff §7.1.

### 0.2 Module world ingestion (user-directed 2026-08-31, supersedes c1 reliance)

User directive mid-journey: "We have the markdown and original pdf for of conks and cons. Ingest it. Then enhance the graph as needed. We are not relying on campaign 1." Confirmed by bundle provenance that the c1 Hempholm objects were play-outcome canon from past sessions 4–6 recaps (evidence refs `artifact:recap:longmont-c1:session-4/5`), **not** a module ingestion; zero source artifacts reference the module.

- Source package: local-only manufactured gold `~/Downloads/of-conks-cons-v21-gold` (purchased DMs Guild module; `MANIFEST.json` pins sha256 for every artifact; legal pin: never commit module prose — none committed here).
- Package carries a complete `dmb_graph_contribution_bundle_v1` (`of-conks-cons-gold-v0`, 24 nodes / 24 edges / 48 accepted assertions, all `created_new`, `worldbuilding_draft`, world_id `of-conks-cons`).
- Route chosen: **reviewed first-world initialization** on the DungeonMind Postgres authority — the same authority seam the product first-world confirm route calls (`WorldGraphInitializationAuthority.initialize` → `initialize_reviewed_world`). The extract→review UI pipeline was NOT run (gold NOTES: "Do not run production extract yet"); recorded as an omission.
- Driver: `evals/of_conks_end_to_end_dogfood/initialize_of_conks_world.py` (operator script; reads the gold package by path arg; no module bytes in git).
- Result: world `of-conks-cons` initialized, outcome `initialized`, published revision `rev:992079326dbd95778d70923808905758`, 48 accepted assertions, initialization_id `dmb:first-world:of-conks-cons:gold-v0`, initialized_at 2026-09-01T04:42:14Z. Eldyrwild untouched (separate world row/head).
- Verified through the product read path: `POST /api/live/world-graph/projection` `{worldId:"of-conks-cons", campaignId:"of-conks-cons", scopeMode:"campaign"}` → HTTP 200, snapshot echoes both ids, 24 nodes / 24 relationships (Hempholm, The Shacks, Jove's Home, The Marrow, …).
- One vocabulary normalization applied at ingestion and logged (OC-010).

## 1. Golden-path status

| Station | Status | Generic / dogfood-only | Evidence |
| --- | --- | --- | --- |
| Source | PASS | generic (Build "Import source" → paste markdown → New world destination `of-conks-cons`; document `9e7786d8-2253-4f8d-b37f-e0720feeaeda` "Hempholm — run packet") | screenshots 35–36 (local-only: module-derived prose); Build reader render 38 |
| Plan | PASS | generic (kind=plan WorkObject, ordinary save, immutable WorkRevision, hard reload); re-anchored to module-world references (WorkRevision 2) under `?campaign=of-conks-cons` | screenshots 28–31; 36 `recap-node-token` buttons on reload |
| Runbook | PASS | generic (blank Runbook create → authoring → native save; v2 Beat-first markers round-trip; stable semantic IDs); re-anchored to module-world references (WorkRevision 3) | screenshots 14–16, 32; 18 tokens on reload |
| Play | PASS | generic (exact-revision Run, sealed manifest, Decision select/change/clear/reselect, activates/suppresses, inspect-without-moving, Make Current, hard-reload resume) | screenshots 17–26; play.run revisions 1→6; play.run_manifest; play.active_run |
| World/object | PASS | generic (Build "Find existing object" → search → View → object sheet with kind/scope/revision pin; relationship traversal garden ↔ threat ↔ Hempholm `threatens`) | screenshots 41–44; projection capture worldId/campaignId `of-conks-cons`, rev `99207932…`, 24 nodes |
| Mechanics | PASS | dogfood-only boutique projection (no mechanics binding exists in the module world — gold is nodes+edges only, OC-014; encounter sheets project threat-card mechanics with provenance, caretakers bind to MM twig blight **by reference**) | screenshots 55–57 (local-only: module-derived stats/tactics) |
| Roll | PASS | dogfood-only boutique mechanism (no product roll seam exists — legacy `roll_stack` module is display-only over session-22 packet state, OC-015); Appendix C name tables render readable, Roll 1d12 selects+highlights one row, result ephemeral | screenshots 50–54 (local-only: module-derived table rows) |
| Encounter/Combat | PASS | dogfood-only boutique prepared encounter sheets (Grotesque Tree garden, Caretaker Rampage, Guardian/Marrow); existing Combat Tracker is a session-26-specific static page, not a composable runtime (OC-016) | screenshots 55–58 (local-only: module-derived mechanics) |
| Agent | NOT EXERCISED — PR #674 active | — | lease recheck 2026-08-31 |
| Reload | PASS | generic (run v3 hard reload preserves current scene + Decision selection; Plan/Runbook hard reloads preserve authored module-world content) | screenshots 63, 65 (run v3); 31–32 (documents) |

## 2. Learning ledger

| ID | Observation | Type | Severity | Evidence | Candidate disposition |
| --- | --- | --- | --- | --- | --- |
| OC-001 | Handoff §material map cites example graph identities `location:hempholm` / `location:the-grotesque`. Authority reality: Hempholm is `loc:hempholm`; the moving tree is `item:grotesque-arcane-moving-tree`; **no** `the-grotesque` location node exists in the adopted world graph. | docs/handoff drift | low | bundle.json grep; projection probe 2026-08-31 | Correct example IDs in any extraction of the handoff pattern; do not trust handoff examples over live authority. |
| OC-002 | Hempholm material is campaign-scoped to `longmont-c1` (390 nodes, 176 rels, 130 evidence, 15 source artifacts). `longmont-c2` projection is a different slice (80 nodes; Mireward/Mirathorn). Dogfood Plan must target campaign `longmont-c1` to see Hempholm. | product behavior | medium (journey-relevant) | projection probes for both campaigns 2026-08-31 | None — truthful authority scoping; record in journey. |
| OC-003 | Operator-local Docker postgres loses all data on container exit (no volume persistence); both APP-STATE and DungeonMind authority had to be rebuilt/restored before any journey step. | environment fragility | medium (dogfood blocker until repaired) | §0.1 | Operator runbook note; not a product change. |
| OC-004 | With the union lens (`?campaigns=longmont-c1,longmont-c2`), the AppChrome World status pill errors: "Projection campaign does not match requested campaign" — the pill's status probe (packet campaign, campaign scope) disagrees with the lens projection (world scope). Canvas chip resolution is unaffected. | UX/consistency | low | screenshot 10 (pill "Needs attention" while chips resolve) | Extraction: align status probe with active lens, or suppress mismatch when lens intentionally widens scope. |
| OC-005 | Prep-document rename is deliberately absent from the UI ("management (rename/archive) stays out of scope"), but the product API supports it (`PATCH /api/live/workspace-documents/{id}` with `title`). Used truthfully to fix the Plan title after the module-independence correction. | product gap (UI) | low | PATCH 200, revision 3→4 | Extraction candidate: minimal rename affordance; API already real. |
| OC-006 | Plan graph-chip resolution is scoped to the session packet's campaign projection by default (c2 slice, 80 nodes). Hempholm objects (`loc:hempholm`, `item:grotesque-arcane-moving-tree`, `npc:mark_jove`, `npc:guardian_tree_heart`) resolve only under the world-scope union lens (469 nodes). | product behavior | medium (journey-relevant) | network capture: projection request `scopeMode:"campaign"` vs `"world"`; screenshots 06 vs 10 | Document the lens requirement for cross-campaign reference; consider scope hint on unresolved chips. |
| OC-007 | Adopted graph carries near-duplicate identities for the same referents: `faction:caretakers` vs `npc:caretakers`; `node:root_like_beetles` vs `item:root-like-beetles`; `item:guardian` vs `npc:guardian_tree_heart`; `loc:shacks` vs `loc:town-shacks`. | world-data quality | low | c1 projection node list 2026-08-31 | Feed to DungeonMind identity-decision backlog; not a Buddy defect. |
| OC-008 | World-scope projection responses echo `campaignId: ""` in the snapshot; `verifyWorldGraphProjectionResponse` requires exact campaign match, so any request carrying a campaignId with `scopeMode:"world"` fails verification and chips silently never resolve (plain anchors). | contract mismatch | medium (silent feature loss) | network capture + verifier source 2026-08-31 | Extraction: backend should echo the requested campaignId (or verifier should accept empty on world scope). |
| OC-009 | `PlayGraphObjectSheet` exists but is not wired into the Play surface; chips in Play prose are non-interactive, so object-sheet inspection is unavailable from Play. | product gap | medium (Station 5 blocked from Play; worked around from Plan surface) | component grep + Play journey attempt 2026-08-31 | Extraction: wire sheet host into Play reference seam (handoff §7.3 names `playSurface/reference/**`). |
| OC-010 | Gold v0 contribution spells the Jove parent-child edge `child_of`; the mounted v4 predicate map intentionally never resolves `child_of` (only `parent_of`, direct). Ingestion normalized to reversed `parent_of` (`npc:mark-jove` → `npc:torbin-jove`) with loud log. | vocabulary drift (gold vs current map) | low | initialize script output 2026-09-01 | Regenerate gold with `parent_of` spelling, or add an explicit `child_of` reverse alias to the map; do not silently extend the map in product code. |
| OC-011 | `WORLD_ID_BY_CAMPAIGN` is a hardcoded frontend map; a newly initialized world is unqueryable from the UI until code is added (`of-conks-cons` entry added under §7.5). | architecture friction | medium (every new world needs a frontend deploy) | worldGraphSurfaceContext.ts; map tests 16/16 | Extraction: resolve campaign→world from the authority (worlds/campaigns tables) instead of a shipped constant. |
| OC-012 | The Plan-surface graph lens is closed over `REVIEW_CAMPAIGN_IDS = [longmont-c1, longmont-c2]`: `resolvePlanGraphLens` filters any other `?campaign=` value out and silently falls back to the session packet campaign. The module-world Plan lens therefore still projects Eldyrwild/c2; Plan tokens render from markdown identity but resolve against the wrong projection (click stays glance-only). Extending the registry breaks hard-enumerated union defaults in shared tests — not done. Build surface has no such gate (classifies scope from `WORLD_ID_BY_CAMPAIGN` only) and projects `of-conks-cons` correctly. | product behavior / lens closure | medium (Plan-surface inspection of non-Longmont worlds is silently wrong) | network capture: only eldyrwild/c2 request under `?campaign=of-conks-cons`; sessionCampaignContext.ts source | Extraction: data-driven campaign registry (with OC-011); until then, Plan-surface reference inspection is Eldyrwild-only by construction. |
| OC-013 | Build source reader renders `dmb-node:` references as plain text (no inline tokens); graph interaction lives in the separate Find/object-sheet tools. | product behavior | low (cosmetic; Find covers inspection) | DOM probe: 0 tokens/chips/anchors in `build-source-reader` | Extraction candidate: inline reference tokens in the Build reader, or deliberate read-only purity (decide). |
| OC-014 | Module-world object sheets show "No attribute rows" and "No source excerpt on file" — the gold contribution carries nodes+edges only, and the authority stores source digests/locators, not prose. Truthful, but a GM expects threat mechanics on the sheet. | content gap (world data) | medium (sheet is thin for table use) | screenshots 43–44 | Enhance graph with attribute assertions (mechanics summaries) via governed write; source excerpts need an excerpt-serving seam that respects the module's licensing. |
| OC-015 | No interactive roll seam exists in the product: the legacy `roll_stack` surface module is a display-only readout of session-22 packet state (`SESSION_22_TABLE_TITLES` hardcoded), and the c2 `roll-tables.html` packet page is a read-only corpus index (no Roll button, no result highlight). Station 6's "Roll → one result selected/highlighted" is therefore dogfood-only by construction. | product gap | medium (handoff Candidate C confirmed real) | RollStackModule.tsx + prep.js `initRollTableCorpusIndex` source read 2026-09-01 | MINE CANDIDATE: lightweight roll interaction (handoff §Candidate C) — recognized table → readable rows → Roll → ephemeral highlighted result. |
| OC-016 | The existing Combat Tracker (`/combat`, combat.html) is a session-26-specific static boutique page (hardcoded combatant rows, localStorage saves), not a composable combat runtime. Station 7 correctly used the same boutique pattern rather than fake generic integration. | product behavior | low (handoff already anticipated this) | combat.html source read 2026-09-01 | None for this branch; generic Combat completion stays out of scope per handoff. |
| OC-017 | Play cockpit renders a Decision's options only while its parent scene is current; the scenes panel open/closed state persists across page reloads, which confused early automation (toggled closed when expected open). Behavior is correct; automation must read panel state before toggling. | product behavior (automation note) | low | driver `play-v3-decision` step final form | None — correct scene-scoped decision gating; recorded for future driver authors. |
| OC-018 | Vite dev middleware already serves any repo file under `/evals/**` (vite.config.ts `mirewardPrepStaticPlugin`), so the dogfood boutique packet needed **zero product-code changes** to serve — pages + assets + local fixtures all resolve under `/evals/of_conks_end_to_end_dogfood/packet/`. | architecture observation | low (happy path) | vite.config.ts source; packet served 200 | Keep for future dogfoods: boutique packets need no vite changes. |

## 3. Dogfood-only mechanisms

| Mechanism | Why it exists | Generic seam missing | Safe to delete? | Disposition |
| --- | --- | --- | --- | --- |
| `evals/of_conks_end_to_end_dogfood/packet/of-conks-tables.html` + `assets/of-conks-packet.{js,css}` | Station 6 requires recognized table → readable rows → Roll → highlighted result | No interactive roll seam in product (OC-015) | Yes — single directory, no product imports | MINE CANDIDATE (handoff Candidate C: lightweight Roll interaction); the mechanism (fixture JSON → table cards → ephemeral roll/highlight) generalizes, the Of Conks data does not ship |
| `evals/of_conks_end_to_end_dogfood/packet/of-conks-encounters.html` (same assets) | Station 7 requires boutique prepared encounter projections with mechanics + graph links | No composable combat runtime (OC-016); no encounter projection seam | Yes — same directory | MINE CANDIDATE: prepared-encounter projection pattern (combatants/quantities/mechanics/tactics + graph node links) for a future encounter flow |
| `evals/of_conks_end_to_end_dogfood/packet/local/*.json` (gitignored) | Module-derived table rows and threat mechanics are licensed third-party content — local-only per legal boundary | — | Yes (already untracked) | DISCARD from git history permanently; regenerate from the licensed gold package |
| `evals/of_conks_end_to_end_dogfood/initialize_of_conks_world.py` | Operator script driving reviewed first-world initialization (DungeonMind PR #46 seam) for the module world | No operator-facing CLI for world initialization; product path is UI contribution review | Yes | KEEP AS PATTERN: candidate operator runbook for future module worlds (with OC-010 normalization logged) |

## 4. Product magic moments

- **Reviewed first-world initialization just worked.** The gold contribution (24 nodes / 24 edges) initialized the `of-conks-cons` world through the real DungeonMind authority seam, and the projection served it immediately — no c1/c2 entanglement, exactly the independence the module needed.
- **Build "Import source" → New world destination** accepted the module prep packet and filed it under `of-conks-cons` with zero schema drift — the source admission seam is genuinely world-agnostic.
- **Build "Find existing object" → View → relationship traversal** gave a real GM moment: search "grotesque", open the garden site, walk `threatens` edges to the Grotesque Tree threat and Hempholm — revision-pinned the whole way.
- **Run v3 bound the module-world Runbook at exact revision** (playable revision 3, sha `ff028801…`) and the cockpit rendered the full six-beat structure with scene-scoped Decisions; the selected option survived a hard reload.
- **Boutique packet roll moment**: Roll 1d12 → "Rolled 5 → Thorwald Dohna" with the row lighting up is exactly the table-feel the handoff asked for, at near-zero code cost.

## 5. Friction

- **Plan-surface lens closure (OC-012)** is the biggest silent-wrongness risk: `?campaign=of-conks-cons` on Plan renders tokens but resolves them against Eldyrwild/c2 with no user-visible signal. A GM would trust a wrong glance.
- **Every new world needs a frontend deploy** (OC-011 `WORLD_ID_BY_CAMPAIGN`) — world initialization is one script, but UI queryability is a code change.
- **Object sheets are thin without attribute assertions** (OC-014): kind/scope/revision/relationships render, but a GM wants the threat's mechanics on the sheet.
- **Play cockpit scene panel state persists across reloads** (OC-017) — correct behavior, but it surprised automation twice; a collapsed/expanded indicator is subtle.
- **Operator postgres has no volume persistence** (OC-003) — container exit wiped both APP-STATE and the authority mid-dogfood.

## 6. Authority/truth problems

- None introduced by this branch. Module world initialized through the reviewed-contribution seam with provenance (gold bundle id + digest) recorded on the source artifact; no Buddy graph publication/write architecture added; boutique packet reads no authority and writes nothing.
- Truthful omissions recorded rather than faked: no mechanics binding in-graph (OC-014), no source excerpts served (licensing), caretaker mechanics bound to MM by reference (not copied), rolled results ephemeral (not published to World).

## 7. Performance / table-speed observations

- Projection for the 24-node module world is effectively instant; Build Find search over it returns sub-second.
- Boutique packet pages are static + one small JSON fetch — instant at table speed.
- Play cockpit interactions (Make Current, option select, reload resume) all completed within the driver's 1.5–3.5s settle windows without timeouts once selectors were correct.

## 8. Extraction candidates

| Priority | Candidate capability | Owning flow | Why independently useful | Suggested handoff |
| --- | --- | --- | --- | --- |
| P1 | Data-driven campaign→world registry replacing `WORLD_ID_BY_CAMPAIGN` + `REVIEW_CAMPAIGN_IDS` closure (OC-011, OC-012) | Plan/Build graph lens | Any newly initialized world becomes UI-queryable without a deploy; fixes silent wrong-projection resolution on Plan | Buddy frontend + lens contract |
| P1 | Lightweight Roll interaction (handoff Candidate C): recognized table → readable rows → Roll → ephemeral highlighted result (OC-015) | Play surface table tools | Every GM improv moment (names, weather, loot) wants this; dogfood proved the interaction shape at boutique cost | Buddy Play surface (new seam; do not generalize into a RollTable schema prematurely) |
| P2 | Prepared-encounter projection pattern (OC-016): combatants/quantities/mechanics/tactics + graph links | Play/Build encounter prep | Known fights are runnable without claiming generic Combat completion | Buddy encounter flow (earns its own handoff) |
| P2 | Wire `PlayGraphObjectSheet` into the Play reference seam (OC-009) | Play surface | Object inspection from the cockpit without leaving Play | Buddy Play surface (`playSurface/reference/**` per handoff §7.3) |
| P2 | Graph attribute assertions for mechanics summaries (OC-014) via governed write | DungeonMind contribution pipeline | Object sheets become table-useful (AC/HP/actions) | DungeonMind + Buddy governed write path |
| P3 | Plan/Build document rename affordance (OC-005) | Plan surface | API already real; UI omission is deliberate but bites operators | Buddy product decision |
| P3 | Operator runbook for module-world initialization (initialize script + OC-010 normalization note) | DungeonMind ops | Repeatable module ingestion without rediscovery | DungeonOverMind operator docs |

## 9. Things to discard

- `packet/local/*.json` fixtures (licensed module bytes) — never commit; regenerate locally.
- The `child_of` → `parent_of` in-script normalization is a dogfood workaround (OC-010); the durable fix belongs in gold regeneration or the predicate map, not here.
- Nothing in product code is dogfood-specific: the only product-code change is the one-line `WORLD_ID_BY_CAMPAIGN` entry (bounded-discovery log), which is truthful to keep or trivially revertable.

## 10. Final disposition

DO NOT MERGE WHOLESALE.

(pending — final handback per handoff §13)

## Bounded-discovery path log (handoff §7.5)

| Path | Station | Owner / collision | Change class |
| --- | --- | --- | --- |
| `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` | Stations 2/5 (graph reference resolution for module world) | No active-PR collision (#674 leases `agentInteraction/agentSurfaceContextRequest.ts`, not this file); map tests 16/16 pass | EXISTING-SEAM WIRING (one-line campaign→world map entry; OC-011 records the durable follow-up) |
| `evals/of_conks_end_to_end_dogfood/packet/**` (html/js/css; `local/` gitignored) | Stations 6/7 (Roll, Encounter) | No collision — new dogfood-owned directory; served by existing `/evals/**` dev middleware (OC-018), zero product-code touch | DOGFOOD-ONLY COMPONENT (handoff §7.4); MINE CANDIDATES recorded in §3 |
| `evals/of_conks_end_to_end_dogfood/drive_journey.py` (steps `roll-station`, `encounter-station`, `start-run-v3`, `play-v3-decision`) | Stations 4/6/7 evidence | No collision — dogfood-owned driver | EVIDENCE TOOLING |
| `.gitignore` (`corpus/of-conks-cons-markdown/`, `packet/local/`) | Legal boundary | No collision | LEGAL PIN ENFORCEMENT (module bytes stay local) |

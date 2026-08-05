# Magic Moment Dogfood — MAGIC-D3 (Latchling)

**Date:** 2026-08-05  
**Operator:** Drakosfire (live Workbench + Plan + Hermes dogfood)  
**Steward:** Cursor dogfood steward (magic-d3 worktree)  
**Branch:** `feat/statblock-magic-d3-workbench-threat-publication`  
**Prior report:** `Docs/Reports/MAGIC-MOMENT-D3-2026-08-04.md` (ANything / missing-bridge → first durable publish)  
**World / campaign:** `eldyrwild` / `longmont-c2`  
**Live session host:** `evals/c2_live_prep/live/session_22`  
**Starting graph head (this session):** `rev:50f80a916d63a6ec68411810935023ab` (ANything)  
**Ending graph head:** `rev:3413bf6f5044cf2680233f5e37c90dcf`  
**Result:** PARTIAL — preferred Mireward threat published through Workbench; rediscovery works; campaign presentation + Plan/Hermes latency still FAIL_PRODUCT for GM feel

## Intent

Finish MAGIC-D3 on a real Mireward siege threat: accept mechanics → governed Workbench publish → Plan insert → hover glance → Hermes rediscovery, and judge whether the product feels like prep rather than ledger engineering.

## Environment

- Worktree: `DungeonMindBuddy-wt-magic-d3`
- Live API: `127.0.0.1:8000` with `DUNGEONMIND_WORLD_GRAPH_ROOT` → primary Buddy `out/`
- UI: Vite `127.0.0.1:5173`
- DungeonMindServer: available for mechanics locate/accept
- Publication ledgers: worktree `out/threat_publication_*` (draft store shared via symlink to primary)

## Starting exact mechanics

| Field | Value |
|---|---|
| ThreatDraft | `2169f965-6098-4287-9a0b-90adfdeb1b6e` (**Mireward Latchling**) |
| Candidate | `cand_duxkq64lhy6jj32y` |
| Statblock ID | `sb_7727dfeeb8074214a6a9cebf257691ff` |
| Mechanics revision | `rev_60b7bf03dd8d4a75a0a164ad73ce83b1` |
| Definition digest | `sha256:4c843b9e8672c20d94e2594a70a62b0496f009481ac69af64dee071171e2d722` |
| Workflow | `mechanics_saved` before publish |

## Publication path (product)

Workbench floating dock drove the chain: **Publish** → identity → proposal → **Confirm publish**.

### Friction before durable publish

1. **False identity candidate** — Tripod Null-Calf offered via place-token leakage (`token:mireward:attribute`). Fixed: advisory candidates require identity-surface reasons (label/alias/node_id), not attribute-only.
2. **Busy lock after refuse** — refuse cleared local session while server op stayed `ready` → `publication_busy`. Fixed: refuse cancels server op; busy envelope exposes active op + Cancel stuck publication.
3. **Uncommitted commit (silent)** — first Latchling confirm failed merge with unresolved `evidence:tpub:…` (assertions lacked embedded evidence/source-artifact payloads). UI said “Confirming…” / “not yet resolved” with null message. Fixed: embed provenance in proposal packaging (matches ANything contribution that worked); surface merge diagnostics; allow Cancel on terminal uncommitted.
4. **SBW13 append-revision copy** — “proposal not saved…” noise remains out of MAGIC-D3 scope.

### Durable publication (observed)

| Identity | Value |
|---|---|
| ThreatDraft | `2169f965-6098-4287-9a0b-90adfdeb1b6e` |
| Publication operation | `ca9fff4d-92f4-45ed-bb02-672b3b175e34` |
| Identity decision | `create_new` |
| Threat node | `threat:authored:d16d43d376833e38caf46dd19b1dd17f` (**Mireward Latchling**) |
| Binding | `threat-statblock-binding:07ab38b331085b426bb69474` |
| Bound locator | `sb_7727dfeeb8074214a6a9cebf257691ff` @ `rev_60b7bf03dd8d4a75a0a164ad73ce83b1` |
| Committed revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` (became graph head) |
| Commit state | `committed_unverified` |
| Verification status | `failed` |
| Verification codes | `rebuild_unavailable`, `projection_threat_source_domains_mismatch`, `projection_external_resource_source_domain_mismatch` |

Post-commit audit fails on projection source-domain shape (threat projects `['statblock','worldbuilding']` vs sealed `['worldbuilding']`; external resource projects `['statblock']` vs verifier expecting `['manual_seed']`) plus an unrelated pinned-contribution digest warning. **Store materialization and head advance succeeded** — same class as ANything `committed_unverified`.

## Rediscovery (Plan + Hermes)

| Surface | Result |
|---|---|
| Plan graph load | Latchling appears after load completes |
| Hover / glance | Still **useless metadata** — not campaign-useful |
| Hermes rediscovery | **Found** the Threat |
| Navigating away from Plan | Appears to **restart graph loading** (cold path again) |
| Plan graph load latency | **Too slow** for prep flow |
| Hermes / agent loop latency | **Too long**; needs honest UX feedback while working |

## What felt wrong (product)

1. **Hover glance** — metadata-only; still not a prep card (name / feel / AC·HP·CR when hydrated).
2. **Plan graph reload on navigate-away** — leaving Plan and returning restarts expensive graph loading; feels like no persistence/cache across surface switches.
3. **Agent loop silence + duration** — Hermes eventually works, but the wait needs progressive / elapsed feedback so the GM knows the loop is alive.
4. **Verification chrome** — “Published; verification needs attention” is honest but easy to misread as publish failure; GM-facing success should lead with “on the World Graph” and bury audit codes.

## What worked

- Preferred Mireward Latchling path through Workbench Publish (create_new).
- Dock-hosted CTAs / status (Publish → Confirm) instead of page-bottom only.
- Packaging fix unblocked merge after evidence-embedding.
- Durable Threat + binding on head; Plan sees the new statblock; Hermes finds it.

## Verdict

**PARTIAL.** MAGIC-D3 publication bridge is product-reachable for a real siege Threat. Unqualified PASS still blocked by:

- Campaign glance / hover presentation  
- Plan graph load latency + reload-on-navigate  
- Hermes agent-loop UX feedback (and underlying latency)  
- Post-commit verification domain mismatches (audit debt; not a missing Threat)

## Follow-ons (do not expand this PR)

Canonical backlog: `Backlog.md` → **MAGIC-D3: Threat glance/Hermes must be campaign-fun, not metadata** (enriched 2026-08-05).

Additional product cuts called out this session:

1. Plan projection cache / retain across surface navigation (do not cold-reload the whole graph on every return).
2. Hermes live-progress UX (elapsed + “working” truth; reuse existing READY live-progress / telemetry entries).
3. Verification expectation alignment for projection source-domains vs store / sealed proposal (so `committed_verified` is reachable without lying).

## Still false / next

- Unqualified MAGIC-D3 PASS (presentation + latency + agent-loop feel)
- Placement (`AOW03`/`AOW04`), exact embed (`SBW12`), Build insertion, combat activation
- Treat `committed_unverified` source-domain codes as release blockers only after GM surfaces feel good — they did not block rediscovery here

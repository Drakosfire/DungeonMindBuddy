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
**Publication bridge E10:** PASS — the governed Workbench path reached a durable World Graph revision and the exact-chain recovery/no-duplicate-confirm contract is covered by the Workbench component evidence below.

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
| Identity resolution | `c05f202f-2f94-4902-88a4-902bc9f91066` |
| Proposal | `5461a95b-11eb-40b2-b2b7-ecbdead35b2d` |
| Commit | `523e293c-02c8-41db-97bc-58db9e00891b` |
| Identity decision | `create_new` |
| Threat node | `threat:authored:d16d43d376833e38caf46dd19b1dd17f` (**Mireward Latchling**) |
| Binding | `threat-statblock-binding:07ab38b331085b426bb69474` |
| Bound locator | `sb_7727dfeeb8074214a6a9cebf257691ff` @ `rev_60b7bf03dd8d4a75a0a164ad73ce83b1` |
| Committed revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` (became graph head) |
| Commit state | `committed_unverified` |
| Verification status | `failed` |
| Verification codes | `rebuild_unavailable`, `projection_threat_source_domains_mismatch`, `projection_external_resource_source_domain_mismatch` |

Post-commit audit fails on projection source-domain shape (threat projects `['statblock','worldbuilding']` vs sealed `['worldbuilding']`; external resource projects `['statblock']` vs verifier expecting `['manual_seed']`) plus an unrelated pinned-contribution digest warning. **Store materialization and head advance succeeded** — same class as ANything `committed_unverified`.

The source-domain disagreement above is the observed pre-correction dogfood result, not a claim that the durable write failed. Cycle 4 promotes embedded provenance and source-domain aggregation to an explicit package/verification contract; it does not retroactively relabel this recorded commit.

## Exact-chain reload and duplicate-confirm proof

The browser recovery contract for this run is:

1. The accepted chain is pinned as `draft 2169f965… → operation ca9fff4d… → resolution c05f202f… → proposal 5461a95b… → commit 523e293c…`.
2. On reload/reopen of the same Workbench draft, the pointer-only session record rehydrates those IDs and the panel re-reads the exact operation, resolution, proposal, and commit endpoints. It does not query “latest” or mint a replacement ID.
3. The commit re-read returns the durable revision `rev:3413bf6f…` with `committed_unverified`; the UI shows “Published; verification needs attention,” keeps Confirm unavailable, and offers only exact commit re-read.
4. `ThreatPublicationPanel.test.tsx` proves the lost-confirm/remount path: `confirmThreatPublicationCommit` is called exactly once, `getThreatPublicationCommit` receives the exact `draft_id`, `operation_id`, and `commit_id`, and the call count remains one after recovery. The dock-driven lost-response test also proves the exact `commit_id` remains in session storage.

This is component-level reload evidence for the publication bridge. The live dogfood captured the durable IDs and rediscovery outcome, but did not retain a browser network HAR; the zero-additional-confirm claim is therefore test-backed rather than inferred from a missing log.

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

**Publication bridge: PASS.** E10 is satisfied: a real mechanics-saved Latchling reached durable publication through the normal Workbench path, exact IDs are recorded, rediscovery succeeded, and the recovery contract proves no duplicate confirm.

**Overall MAGIC-D3: PARTIAL.** The experience is not an unqualified pass because:

- Campaign glance / hover presentation  
- Plan graph load latency + reload-on-navigate  
- Hermes agent-loop UX feedback (and underlying latency)  
- Post-commit verification domain mismatches in the recorded dogfood result (audit debt; not a missing Threat)

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

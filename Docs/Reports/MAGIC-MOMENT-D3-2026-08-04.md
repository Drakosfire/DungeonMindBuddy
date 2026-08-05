# Magic Moment Dogfood — MAGIC-D3

**Date:** 2026-08-04  
**Operator:** Drakosfire (live Workbench + Plan dogfood)  
**Steward:** Cursor dogfood steward (this session)  
**Repository execution SHA:** `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e` (dispatch) + uncommitted Workbench publication chrome / packaging fixes exercised in timeline worktree during dogfood  
**Dispatch anchor:** `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e`  
**World / campaign:** `eldyrwild` / `longmont-c2`  
**Starting graph head:** `rev:480267555eda00356cdb6d843b08b93c`  
**Ending graph head:** `rev:50f80a916d63a6ec68411810935023ab`  
**Result:** PARTIAL — publication path reached durable Threat + exact hydration; FAIL_PRODUCT on campaign presentation + latency (see Design Agent brief below)

## Intent

Prove whether a GM can take one real accepted statblock revision through governed Threat publication, reload, Hermes discovery, exact hydration, and compact/full projection while retaining trustworthy identity.

Preferred material if the publication bridge existed: a Mireward siege threat (e.g. Latchling / Tripod Null-Calf / Under-Hymn Brood) with a real accepted `(statblock_id, revision_id, definition_digest)`.

## Reanchor and environment

- Current `origin/main` SHA: `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e` — merge of PR `#504` (`statblock: implement exact Threat projection`); **identical to dispatch anchor**
- Drift from dispatch anchor: **none** on owning paths
- Clean dogfood checkout: worktree `DungeonMindBuddy-timeline` at `main` @ `9fe0b026…` (`git status` clean after ff-only pull)
- Chat workspace remained on dirty feature branch `port/mc02b-build-graph-refs-on-main` (not used as execution authority); `move_agent_to_root` to timeline failed because Cursor tried to check out that feature branch into the timeline worktree
- Build PR `#506` (`BUILD: native World Graph search and inspect`): **OPEN**, not merged — no reanchor required
- Services at dispatch time: live-control API `:8000`, UI `:5173`, DungeonMindServer readiness — **not listening**
- Open shared-surface work that could affect later projection dogfood: PR `#506` (graph-reference / search-inspect); leave noted, not blocking this stop

### Product paths confirmed before mutation (code inventory)

| Required path | Observation | Owning boundary |
|---|---|---|
| Accepted mechanics reopen | UI + `liveApi` support ThreatDraft CRUD, candidate generate/revise, `mechanics:accept`, acceptance reconcile (not exercised live this session) | Workbench / acceptance |
| Publication entry | **No** `live-control-ui` references to `ThreatPublication*`, `publication-operations`, identity resolution, proposal prepare, or confirm commit. `liveApi.ts` stops at acceptance; zero client fetchers for publication routes | Product surface / publication bridge |
| Candidate / proposal / confirm UI | Backend routers mounted under `/api/live/threat-drafts/{draft_id}/publication-operations…` in `live_control_server`; **no matching UI** | SBW09b/c surfaces missing |
| Hermes / Projection Host / Threat Sheet | `ThreatSheetProjection` + view-model present (SBW10b); Hermes exact Threat query tools exist server-side from SBW10a — not reachable for MAGIC-D3 without a published Threat via product publication | SBW10a/b consumers |

**Stop condition hit (§4 / §10):** mandatory publication actions exist only as backend endpoints and tests. Primary gate stops with `FAIL_PRODUCT — missing user-facing publication bridge`. Direct API probe deferred unless operator requests boundary narrowing; it cannot convert the verdict to PASS.

## Starting exact mechanics

- Threat concept: not selected — publication entry unavailable  
- statblock ID / revision ID / definition digest: not recorded  
- later immutable revision: not applicable  

## Publication path

Not exercised. No user-facing publication action found in `apps/live-control-ui` against execution SHA.

Backend-only surface inventory (not a product pass):

1. `POST /api/live/threat-drafts/{draft_id}/publication-operations`
2. identity-resolution routes on the same draft/operation prefix
3. proposal prepare/read routes
4. confirm/commit routes

## Identity decision

NOT_EXERCISED — no product candidate review surface reached.

## Durable publication ledger

| Identity | Value |
|---|---|
| Repository execution SHA | `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e` |
| World ID | intended `eldyrwild` (not mutated) |
| Campaign ID | not bound this session |
| Starting graph head revision | `rev:480267555eda00356cdb6d843b08b93c` |
| Accepted statblock ID | — |
| Accepted statblock revision ID | — |
| Accepted definition digest | — |
| Publication operation ID | — |
| Identity resolution ID and decision | — |
| Publication proposal ID | — |
| Expected contribution ID | — |
| Commit record / receipt identity | — |
| Committed graph revision | — |
| Published Threat node ID | — |
| ThreatStatblockBinding ID | — |
| Bound statblock locator and digest | — |

## Reload proof

NOT_EXERCISED.

## Hermes probes

NOT_EXERCISED.

## Projection proof

NOT_EXERCISED in product. Compact/full Threat Sheet code exists under `apps/live-control-ui/src/statblocks/projection/` but MAGIC-D3 requires a product-published Threat first.

## Relationship navigation and exact scope

NOT_EXERCISED.

## Failure / stale / retry proof

NOT_EXERCISED.

## Mechanics revision pinning

NOT_EXERCISED.

## Replay / duplicate proof

NOT_EXERCISED.

## What felt magical

Nothing product-facing was exercised past path inventory. Backend publication/commit/recovery and Threat Sheet projection appear implemented in merged PRs `#491` / `#502` / `#504`, but the GM cannot enter publication from the Workbench.

## Friction and distrust

The named MAGIC-D3 experience is unreachable without scripting HTTP against `/api/live/threat-drafts/.../publication-operations`. That is exactly the falsification case the gate forbids counting as success.

## Invariant ledger

| Claim | PASS / FAIL / NOT_EXERCISED | Evidence |
|---|---|---|
| One explicit identity decision | NOT_EXERCISED | No UI |
| No duplicate mechanics or Threat identity | NOT_EXERCISED | No mutation |
| Exact binding survived reload | NOT_EXERCISED | No mutation |
| Hermes exact/alias discovery | NOT_EXERCISED | Stopped at publication entry |
| Hermes semantic discovery | NOT_EXERCISED | Stopped at publication entry |
| Exact mechanics hydration | NOT_EXERCISED | Stopped at publication entry |
| Compact projection useful | NOT_EXERCISED | Stopped at publication entry |
| Full projection complete and honest | NOT_EXERCISED | Stopped at publication entry |
| Relationship navigation retained exact scope | NOT_EXERCISED | Stopped at publication entry |
| Failure/retry remained honest | NOT_EXERCISED | Stopped at publication entry |
| Later mechanics did not move binding | NOT_EXERCISED | Stopped at publication entry |
| Replay did not duplicate publication | NOT_EXERCISED | Stopped at publication entry |
| User-facing publication bridge exists | FAIL | Zero UI/API-client references; backend routes only |

## Verdict

**Initial stop (same day):** FAIL_PRODUCT — missing user-facing publication bridge (see checkpoint notes).

**After Publish chrome + continued dogfood:** PARTIAL — durable Threat + Hermes hydrate reached; campaign presentation and latency fail the GM feel. See **Verdict (updated)** and **Design Agent brief** near the end of this report.

## Checkpoint note — ThreatDraft create blocked (2026-08-04 operator)

**Operator action:** attempted new ThreatDraft create from Workbench.
**Visible result:** create refused with World Graph bootstrap `state=invalid_bundle, bundleValid=false` due to stale `contribution_id` mismatches on Mirathorn / Mireward / Questionable Company hub contributions.
**Product-offered escapes:** exact `rev:…` under Optional & advanced, or freestanding without graph head.
**Trust impact:** reduced — automatic provenance path is not ready on current shared `out/` head; not a publication-bridge finding by itself.
**Steward direction (initial, withdrawn):** reopen an existing accepted draft.
**Operator correction:** rejected — if provenance-bound create is broken, loading existing is a soft-pass and is not valid MAGIC-D3 evidence.
**Revised steward direction:** do not repair contribution IDs in-session; do not load existing drafts to bypass create; classify this as a stoppable prerequisite failure or exercise only product-offered create escapes (exact `rev:…` pin), never freestanding as a silent substitute for graph-ready create.

## Checkpoint note — ThreatDraft create recovered (2026-08-04)

**Operator action:** hard-refresh after provenance/create-form fix; create + generate a new ThreatDraft.
**Visible result:** generated successfully without freestanding opt-in.
**Trust impact:** increased — live head provenance path usable again after contribution-ID hash stability + live-head status surfacing.
**Still open for MAGIC-D3:** user-facing publication bridge (identity → proposal → confirm) not yet observed.

## Checkpoint note — publication entry absent (2026-08-04)

**Operator action:** after successful create/generate on a new ThreatDraft, inspect Workbench for Publish / World Graph / publication controls.
**Visible result:** no publish button or equivalent user-facing publication action.
**Trust impact:** decisive for MAGIC-D3 — architecture may exist server-side (`/api/live/threat-drafts/.../publication-operations`), but the named GM publication experience is missing.
**Primary gate:** STOP. Verdict `FAIL_PRODUCT — missing user-facing publication bridge`. Direct API probe not used to convert the verdict.

## Follow-on — Publish chrome wired (2026-08-04)

After FAIL_PRODUCT on missing publication bridge, Workbench dock gained a **Publish** control that drives begin → identity → proposal → confirm against existing `/api/live/threat-drafts/.../publication-operations` routes.

## Continued dogfood — publication succeeded; presentation failed (2026-08-04 evening)

### Durable publication (observed)

| Identity | Value |
|---|---|
| ThreatDraft | `b6879631-ce31-4d10-bd21-830e2af1e047` |
| Threat node | `threat:authored:42bd2bd2a8a7e8870171cc90ac373108` (label **ANything**) |
| Committed revision | `rev:50f80a916d63a6ec68411810935023ab` |
| Binding | `threat-statblock-binding:5a173880167df31df00d763e` |
| Statblock locator | `sb_2b18b746b47c46599809fa69d1a075ce` @ `rev_c869932e95774f7f8368e4316aea5189` |
| Commit state | `committed_unverified` (post-commit verification codes included source-domain mismatches; graph merge still advanced head) |

### Path friction before durable publish

1. Proposal assertions declared `evidence:tpub:…` without embedded evidence/source-artifact payloads → merge `publication_commit_uncommitted` / unresolved evidence.
2. Failed attempt left an active publication operation → subsequent begin returned `publication_busy` until cancel.
3. Surfaces stayed pinned to pre-publish projection (`rev:480267…`, Head: no) until hard refresh; Hermes abstained until Plan reloaded at head.
4. Timeline worktree `out/` symlink into primary checkout trips Ingest with `unsafe graph-ingest runs root` (path containment).

### Rediscovery / hydration / Plan insert (after refresh)

- Plan Edit search found **ANything**; insert + hover worked.
- Hermes found the Threat and hydrated mechanics (CR 5, AC 16, HP 75, kit).
- Exact binding hydration status: `available`.

### What felt wrong (product)

- Hover glance was **metadata-only** — not useful for prep.
- Hermes answer **led with IDs, digests, and revision pins** before campaign-useful shape.
- Threat Sheet / hydrate open felt **very slow**.
- End-to-end graph write + read for statblocks felt **far too slow**.
- Operator: presentation must be made **fun**; statblock should render as an **embeddable agent node/card**, not prose dumping locators.
- Styling already exists — mine Statblock Generator + `.md-theme-statblock` / DnD-page TipTap demo; do not invent a new look.
- **Do not test presentation on Build** — Build Markdown/canvas is not ready; host dogfood on Plan + TipTap/ThreatSheet spike.

## Verdict (updated)

**PARTIAL.** Governed publish → durable Threat → Hermes rediscovery → exact hydrate is reachable after Workbench Publish chrome + packaging fixes. MAGIC-D3 is **not** an unqualified pass: campaign presentation and latency fail the GM feel even when contracts succeed.

## Design Agent brief (read this)

Design the campaign-facing Threat presentation layer for Plan (and Hermes embeds). Implementation/port follows; design owns composition and interaction.

1. **Threat glance / hover** — one fun compact card: name, kind/role, one-line threat feel, key AC/HP/CR/speed when exactly one binding hydrates, binding count. No digests, contribution IDs, or evidence internals by default.
2. **Hermes Threat answer** — campaign voice first. Emit Threat/statblock as a **structured UI node/card** (ties to dynamic Hermes artifact + graph-chips backlog). Provenance lives in chips/trace, not in the spoken answer.
3. **Visual grammar** — port, do not redesign: LandingPage Statblock Generator (`StatblockComponents.css`, `canvas-dnd-theme.css`) and Command Board / TipTap DnD-page theme (`.md-theme-statblock` in `prep-markdown-themes.css`; see `PLAN-configurable-markdown-rendering-and-tiptap-styling.md`).
4. **Test host** — Plan insert/hover + Hermes Ask, or ThreatSheetProjection / TipTap theme spike. **Build is out of scope** until Markdown is ready.
5. **Latency is in-scope for the product cut** — cold Threat Sheet / `query-hydration` and post-publish projection refresh must feel usable; design should assume progressive disclosure (glance first, full sheet on demand) so slow full hydrate is not the default path.
6. **Out of scope for this design pass** — redoing publication ledgers, placement/combat activation, Build canvas, inventing a new visual brand.

Canonical backlog entry: `Backlog.md` → **MAGIC-D3: Threat glance/Hermes must be campaign-fun, not metadata**.

## Still false / next

- Unqualified MAGIC-D3 PASS (presentation + latency)
- Placement (`AOW03`/`AOW04`), exact embed (`SBW12`), Build insertion, combat activation
- Worktree-safe shared `out/` / durable store (Ingest symlink guard)


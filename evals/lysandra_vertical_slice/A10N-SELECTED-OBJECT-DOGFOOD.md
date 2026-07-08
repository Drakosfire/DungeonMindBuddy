# A10n selected-object dogfood — Session 23 Lysandra survivor card

**Date:** 2026-07-08  
**Branch:** `codex/a10n-selected-object-identity-polish` (base: `main` after A10m PR #302)  
**Feature:** GM-facing merged identity note on `GraphReviewNodeGameCard`

## Environment

- Backend: `PYTHONPATH=src:apps/live_control_server uv run uvicorn apps.live_control_server.main:app`
- Frontend tests: `npm test -- GraphReviewNodeGameCard graphReviewSelectionUtils` (live-control-ui)
- Pipeline harness: `uv run python evals/lysandra_vertical_slice/a10m_durable_identity_dogfood.py`
- Applied store for API spot-check: generated via `test_a10m_lysandra_durable_identity_dogfood` helpers → `apply_union_supergraph_merge_plan_to_file` (repo-relative `store_path` query)

## Steps performed

1. Ran A10m Lysandra pipeline dogfood script and pytest harness — survivor `party:captain_lysandra_ironveil`, merged-away `node:lysandra` absent from projection.
2. Queried union projection API with an applied Lysandra store (`store_path=evals/lysandra_vertical_slice/fixtures/applied_union_lysandra_dogfood.json` during session; file not committed).
3. Verified API survivor payload includes `merged_away_ids`, `merge_assertion_ids`, Mireward adjacency, and 2 evidence badges; `node:lysandra` not in `node_views`.
4. Exercised selected-object card via `GraphReviewNodeGameCard` tests with the same provenance shape — merged identity note, relationship chip, collapsed evidence/technical details.

**Not performed:** Full live Graph Review UI click-through on the applied store. Default `/ingest?session=session-23` fixture does not include durable merge apply; surfacing the card in-browser requires a custom `store_path` or ingest-run preview path not yet documented as a one-command dev workflow.

## Dogfood questions

| # | Question | Result |
|---|----------|--------|
| 1 | Can I tell this is the survivor/canonical Lysandra without raw ids? | **Pass** — card header shows Captain Lysandra Ironveil; merged note names folded identity "Lysandra". |
| 2 | Can I tell a duplicate was folded in? | **Pass** — "Folded in 1 prior identity: Lysandra." |
| 3 | Game context before technical metadata? | **Pass** — summary, aliases, merged note, relationship chips precede collapsed panels. |
| 4 | Relationships easy to discover/click? | **Pass with concern** — Mireward chip present (`travels_to` predicate still reads technical). |
| 5 | Evidence available but not noisy? | **Pass** — count in merged note; Evidence / Source stays collapsed; no evidence ref ids in primary flow. |
| 6 | Raw ids only in technical details? | **Pass** — `redirect:lysandra`, `node:lysandra`, etc. only after opening Technical details. |
| 7 | Any implementation-metadata primary copy? | **Pass** — primary copy is GM-facing; predicate wording on chips is the remaining rough edge. |
| 8 | Would this help running Mireward at the table? | **Pass with follow-ups** — survivor + Mireward relationship + folded Lysandra context is usable; chip predicate polish and a faster UI dogfood path would help. |

## What felt useful

- Compact "Merged identity" note explains why the card is richer after reconcile.
- Evidence badge count without opening raw evidence ids.
- Mireward relationship chip survives on the survivor card.

## What felt noisy

- Relationship chip uses `travels_to` instead of table-facing wording.
- No direct affordance from merged identity note to Evidence / Source panel.

## What failed

- Nothing blocking. Live UI dogfood on applied store not completed end-to-end (workflow gap, not card regression).

## Follow-ups created

- `Backlog.md` — Graph Review relationship chips GM-facing predicate copy
- `Backlog.md` — selected object "View merged evidence" affordance from identity note

## Verdict

**Pass with follow-ups**

Card behavior meets A10n acceptance for merged survivor payloads. Ship after review; queue narrow UX follow-ups above and a dev-store path for easier repeat UI dogfood.

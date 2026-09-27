---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J1 imported-adventure rehearsal
  - Handoff: Docs/Plans/HANDOFF-DEMO-invalid-candidate-evidence-inspection-v1.md
  - PR topology: serial

  ## Review contract
  An exact reviewable ExtractionRun with false anchor quotes remains inspectable
  in Graph Review, but no invalid evidence can enter prepare, initialization, or
  publication. Review the ACTIVE handoff, cumulative diff, and owning-boundary
  tests; the PR body is transport metadata.
---

# HANDOFF — DEMO: inspect invalid candidate evidence without publishing it

**Created:** 2026-09-27  
**Status:** ACTIVE — bounded J1 repair, not a full-demo acceptance  
**Flow / owner:** DEMO / Buddy extraction-review boundary  
**PR topology:** serial; one assigned implementation PR, no successor until review/merge/sync  
**Base:** Buddy `main@2733a2a41558257f86577e57cd4bdeb606258ef8`; activation commit is this handoff's guarded landing on `main`  
**Review authority:** PRIME, then merge under the user's explicit DEMO merge authorization  
**Runtime/state lease:** isolated Of Conks witness on API `8813`, UI `5194`, World DB `dungeonmind_demo_ofconks_v1`, APP-STATE DB `dungeonbuddy_application_state_demo_ofconks_v1`; do not touch C1/C2 or the older Of Conks ghost run.

## §1 Mission and invariant

The fresh Of Conks J1 rehearsal imported an exact committed source and produced
one immutable, reviewable candidate. Graph Review currently shows only an
error because its review-package endpoint rejects the first nonliteral anchor
quote. The candidate has 25 nodes, 23 edges, 70 evidence refs, and 106 quotes;
the production matcher finds 103 literal and 3 nonliteral quotes. The source
and candidate remain valuable inspection evidence, but the graph has not been
published.

**One merge-ready invariant:** Graph Review can inspect every assertion and its
exact frozen source paragraph, including explicitly invalid evidence, while
all prepare/first-World/confirm paths continue to reject a candidate containing
any invalid evidence. `reviewable` remains the extraction lifecycle status,
not proof of publication eligibility. Inspection must not mutate the source,
candidate, span index, or World head.

The observed source is local licensed material. It is never copied into Git or
test fixtures. Product evidence may identify its IDs, hashes, counts, and
failure codes. Test fixtures use newly authored synthetic prose.

## §2 Exact witness and authority

- World: `of-conks-j1-fresh-rehearsal`, new disposable managed World with no
  published graph head.
- Source document: `a775e748-b9f7-4d7e-b03d-abffcc62223d`, revision 2,
  48,778 bytes, SHA-256
  `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
- SourceArtifact:
  `artifact:worldbuilding:a775e748-b9f7-4d7e-b03d-abffcc62223d:r2:7a379fc90256`.
- Run: `124b2191-a493-40d5-a915-c9170848cc67`, `reviewable`, profile
  `worldbuilding_shepherds_flock_v0@0.1`, model lineage `gpt-5.4-mini`.
- Candidate SHA-256:
  `3f945649d4b2830accd3d53ecab999ae0f5a703a5bd46e2c78b7eed153b7cab7`.
- Full read-only audit with the production `find_anchor_quote_matches`: 48
  assertions, 70 refs, 106 quotes, 103 valid, 3 invalid, zero missing quotes,
  zero unknown spans, zero wrong SourceArtifact refs. Invalid assertions are
  `npc_torbin_jove` (span 205), `faction_baldurs_gate_mages_guild` (span 363),
  and `edge_22` (span 145). The current endpoint returns `422` on the first.
- The exact Markdown was seeded through Buddy's supported local source-import
  API after browser `file://` access was blocked. This proves exact source
  commit/reopen, **not** a long-file UI paste witness. No model cost/usage
  telemetry was persisted for this run; do not invent a dollar figure.

Predecessor state is already synchronized in the #776 post-merge guarded
transaction: #776 merged at `4f341eb5ca5edc6c81d5dd956bcea70ff9d9be85`,
and handoff/roadmap mirrors are at `2733a2a...`. This PR must keep both DEMO
roadmap copies byte-identical if it records this observed J1 blocker; it must
not mark J1 or full DEMO complete before its own merge.

## §3 Behavior contract

| Case | Required result |
|---|---|
| All evidence literal | Existing exact review package and publication eligibility unchanged. |
| One or more false quotes | `200` inspectable exact-run package; retain exact candidate assertion IDs, raw quoted strings, canonical paragraph/span identity, and explicit per-quote/per-assertion invalid status. Surface a visible blocked-publication reason. Do not rewrite quotes, substitute nearby text, or silently drop assertions. |
| Invalid evidence in first-World or ordinary prepare | Existing strict verification rejects before any plan/confirm. A UI package flag must never be accepted as publication authority. |
| Unknown span, wrong artifact, unreadable source, invalid candidate document | Fail closed with existing structured error; do not launder an unprovable binding into a merely inspectable paragraph. |
| Reload exact run | Same inspection classification from frozen candidate/source/index; no model call, no new run, no World mutation. |

The narrow implementation may add additive inspection fields to the exact-run
review DTO. It must not weaken the strict prepare validator or change the
SourceArtifact, DungeonMind, WorldKeeper, extraction prompt/model/schema,
candidate-document integrity, or source-span contract. If making an invalid
candidate inspectable requires a second publication contract or changes to an
external repo, stop and return to PRIME.

## §4 ACTIVE write lease

Expected production paths:

- `apps/live_control_server/services/extract_promote.py` — separate
  inspection classification from strict publication validation.
- `apps/live_control_server/models/extract_promote.py` — additive exact review
  DTO fields only.
- `apps/live-control-ui/src/api/types.ts` — matching additive DTO types.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
  — do not render preparation/first-World controls for invalid evidence.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExactRunProjection.tsx`
  — render invalid evidence beside the exact assertion/paragraph.

Focused tests in existing adjacent test files and one new owning-boundary
Python test module under `tests/` are leased. Backward-looking DEMO state
authority updates, only if needed, are limited to
`Docs/Roadmaps/ROADMAP-demo.md` and its byte-identical mirror
`Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md`.

No other production path is leased. If the API route or other component truly
must change, stop and state the exact missing path/contract to PRIME before
editing. No licensed source content, `.env`, runtime artifact, or output root
enters the PR.

## §5 Proof and stop conditions

1. Synthetic service test: one valid and one invalid quote in a coherent
   candidate; exact review returns all assertions and flags the invalid one.
   Strict first-World and ordinary prepare remain non-mutating failures.
2. Frontend integration test: invalid package visibly marks the affected
   assertion, shows canonical evidence, and cannot expose prepare/confirm;
   valid package stays presentation-compatible.
3. Live exact-run replay against the frozen J1 run returns inspectable package
   with the same 3 invalid anchors, same candidate/source digests, no model
   call, and no World head. Browser Graph Review must show this state.
4. Focused Python/UI tests, Ruff, frontend typecheck/build where applicable,
   and `git diff --check`. Distinguish inherited baseline failures from new
   failures; report exact head and commands to PRIME.

Stop if the repair silently corrects a quote, drops an assertion, makes an
invalid package publication-eligible, requires changing DungeonMind or a
model prompt, or exceeds this one inspection capability. Product planning and
projection remain STOP-gated until a qualified candidate can be published;
this PR alone does not promise a green World head.

## §6 Handback and state

Open one `DEMO: inspect invalid candidate evidence safely` PR from an isolated
implementation worktree after this handoff lands on `main`. Review each
distinct head with PRIME. Report the exact artifact/run/source IDs, API
inspection classification, invalid-quote count, UI witness, test evidence,
no-mutation proof, and any residual extraction-quality follow-up. Merge only
after PRIME approves the exact head. Post-merge, synchronize this handoff and
both DEMO roadmap copies atomically; do not claim full J1 completed.

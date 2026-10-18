# DOGFOOD: durable Plan autosave

Status: ACTIVE — bounded implementation lease, 2026-10-18.

Branch: `codex/plan-durable-autosave`.

Base: fetched `origin/main@d50b0d9b8509c52930eb443aa568161f04a749b9`.

Topology: serial, one PR. PRIME retains merge and serving-runtime authority;
ARCHITECTURE reviews the exact cumulative implementation head.

## Mission

Make ordinary edits to an existing World Plan durable automatically, with a
clear navbar status and a timestamp sourced only from the server's committed
record. The existing CAS prepare/commit protocol remains the write boundary.
An edited new blank Plan may use the existing guarded create-and-commit flow;
never create a Plan merely because it was opened. Build adoption, card editing,
document separators, graph publication, and Play behavior are outside this
first independently useful slice and remain follow-up work.

## Authority and supersession

The operator authorized execution of the Plan autosave dogfood slice on
2026-10-18; PRIME explicitly delegated design/stewardship and implementation.
That assignment supersedes the stale Plan authoring lease carried by open PR
#1188, whose base is `3a890b9e` and whose exact source head
`3d6733a5e34026a52306f155917adf9c29dddf47` is preserved unchanged. PRIME
recorded the lease transfer on [PR #1188](https://github.com/Drakosfire/DungeonMindBuddy/pull/1188#issuecomment-6252347788).
Do not merge, rebase, or edit PR #1188 as part of this slice. This handoff is
the active exclusive write lease against current `origin/main`.

## Exclusive write set

- `Docs/Plans/HANDOFF-DOGFOOD-plan-durable-autosave.md`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `apps/live-control-ui/src/planSurface/planSurface.css`
- `apps/live-control-ui/src/components/DurableSaveStatus.tsx`
- `apps/live-control-ui/src/components/DurableSaveStatus.css`
- `apps/live-control-ui/src/components/DurableSaveStatus.test.tsx`

No shared shell/style entrypoint, Build, Play, Ingest, server, database, schema,
Graph, conversation, environment, or runtime paths. Do not mutate live Plan
content. The new presenter must remain Plan-only in this slice; Build may adopt
it in a later authorized lease.

## Invariants

- Snapshot exact World, document/local-draft identity, title, Markdown, and edit
  generation for every save. Serialize writes per selected target.
- Preserve selection-epoch, editor-generation, local recovery, uncertain-create,
  and saved-basis fencing. Late results never affect a newly selected target.
- Typing or title edits during a save stay dirty after the older commit and
  trigger a subsequent autosave. Never mark a newer draft clean using an older
  receipt.
- Commit only through `prepareTiptapMarkdownWrite` and
  `commitWorldOwnedPlanMarkdownWrite`. Never auto-rebase on CAS conflict.
- Retain local recovery for failure, conflict, and uncertain create/commit;
  never silently discard or replay an uncertain create.
- Report “Saved” and a timestamp only from a validated durable server record
  (`committed_record.updated_at`, or the verified record on open). No browser
  clock, prepare receipt, or localStorage time may be presented as a durable
  save time. While dirty/saving, keep the prior durable timestamp distinct.
- Autosave does not publish Graph data, send conversation messages, or start
  Play. Preserve Markdown fidelity, media, and playable marker identities.
- No persistence is created by opening an empty surface; the first authored
  change is the intent signal that can invoke the existing guarded creation
  path.

## Verification

Add owning tests for debounce, an older delayed save followed by typing/title
edit, target switch while a save is pending, durable timestamp provenance,
failure/conflict/unknown recovery, saved Plan reopen, empty Plan non-creation,
and no Graph/Play calls. Run focused suites, UI typecheck/build, and inspect the
exact cumulative base-to-head diff. Record inherited failures and rendered
limits honestly. Commit and push the implementation and open one PR; no merge or
5202 rollout is authorized here.

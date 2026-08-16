# Backlog Hygiene — 2026-08-16

**Scope:** first aggressive cleanup of root `Backlog.md` only.  
**Goal:** restore the file as a small queue of independently actionable follow-ups rather than a historical workstream ledger.

## Why this cleanup exists

Before this pass, `Backlog.md` had **74 active status headings** and about **322 KB** of content. It mixed:

- current product follow-ups;
- already-shipped work still marked `READY`;
- completed experiments still marked `DOING`;
- superseded pre-World-Supergraph architecture;
- active workstream sequencing already owned by roadmaps / PR trackers;
- standing engineering/process rules;
- long research narratives whose durable value is historical context, not dispatchability.

That conflicts with the repository's current authority model. `ARCHITECTURE-campaign-supergraph.md` says the project is forward-only, preserves experiment lessons rather than obsolete ownership models, and delegates Campaign Supergraph sequencing to `PR-TRACKER-campaign-supergraph.md`. The tracker itself says completed narrative belongs in merged PRs, archived handoffs, and acceptance reports.

## Disposition rules used

1. **Do not duplicate an active sequence.** If a roadmap/tracker already owns ordering and status, remove the duplicate backlog ticket rather than let it drift.
2. **Archive by removal when the item is historical research, not a terminal ticket.** Git history preserves the full prior text. `Backlog-DONE.md` remains useful for intentionally archived completion records; this pass does not bulk-copy dozens of obsolete research notes into it.
3. **Split shipped core from genuine residual.** If an entry says “resolved,” “shipped,” “graduated,” or “proven,” remove the completed core and retain only a separately actionable residual when one exists.
4. **Drop obsolete architecture literally.** Pre-supergraph/session-preview/old recap-pipeline tickets are not executable specifications. Reproduce a defect against current `main` before resurrecting it.
5. **Move process lessons out of the active queue.** A rule like “live provider schema changes need a live provider test” is valuable, but it is process law rather than a product backlog item.
6. **Prefer one capability per entry.** Compound entries were split where the parts have different owners or failure models.

## Representative removals

### Already done / core resolved

- `CUTOVER Case C Buddy EVIDENCE_PROVENANCE after identity-lifecycle history` — PR #587 completed Captain/Thrin alias packaging and remeasured `EVIDENCE_PROVENANCE` to 0.
- `Statblock generation guidance v3` — its own entry records the core as resolved in DMS PR #26; residual validator/prompt questions are separate.
- `Descriptive references need a first-class home` — `explains` shipped in DMS PR #28 and the targeted wrapper pattern was eliminated in the measured probe.
- `Server owns derived math` — core authority change shipped in DMS PR #27.
- `No UI path to promote session extract into World Graph head` — the entry itself later records the human UI promote path as proven.
- `Hermes backend = in-process agent LLM (not CLI oneshot)` — current architecture/tracker already treats graph-first Hermes reads/continuity as landed capability.
- `Live UI dogfood always starts at /` — operating convention, not implementation work.

### Completed investigations incorrectly left `DOING`

- Graph-memory vocabulary ablation dogfood.
- Graph-memory encounter/job extraction spike.

Both had already reached investigation verdicts and spawned narrower successor work. Keeping them `DOING` made the active queue lie about current ownership.

### Superseded experiment-era work

The April–May recap-ingest Stage A/B/C/D, NPC-registry, timeline-writer, breadcrumb/session-memory, FactStore, lexical-routing, and Extraction Lab blocks were removed from the active queue. Their results remain useful historical evidence, but their ticket shapes predate the persistent World Supergraph authority model and should not be dispatched literally.

Likewise, old Graph Review entries tied to preview-union/session-local product models were removed unless they still map cleanly onto the current exact-run / World Graph architecture.

### Process / engineering law removed from product backlog

Examples include:

- live provider schema changes require a real provider-path verification;
- generated artifacts must be refreshed when dependency emission changes;
- contract-freeze / transition-table discipline for stateful durability slices;
- deterministic discovery should replace LLM discovery when the operation is mechanical.

These are valuable lessons, but they belong in repository process authority rather than competing with product capabilities in `Backlog.md`.

## Retained shape

The rewritten active backlog keeps only independently actionable product/debt items, including:

- Plan/Hermes document-switch continuity;
- Build campaign creation and source lifecycle gaps;
- shared Threat / Statblock cross-surface capability gaps;
- Hermes authoring/composer/progress/telemetry/chip UX;
- bounded Statblock Workbench/editor/generation validation gaps;
- worldbuilding draft elevation and exact-run review inspectability;
- Ingest primary-path simplification;
- world-anchor and ecology/resource extraction follow-ups;
- a small set of still-relevant longer-horizon design ideas.

The first pass reduces the active queue from **74 headings to 29**.

## Future hygiene

- Treat entries older than **30 days** as requiring re-verification before dispatch.
- Keep active workstream sequencing in the owning tracker/roadmap.
- When a ticket's core ships, archive it and create a new residual ticket rather than appending months of updates under the old heading.
- Prefer a backlog of roughly **20–30** independent capabilities over an exhaustive history of everything ever learned.

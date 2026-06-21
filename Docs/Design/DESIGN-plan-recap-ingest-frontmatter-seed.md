# DESIGN — Plan Recap Ingest Frontmatter Seed

**Status:** Active v1 design, implemented as deterministic seed skeleton builder  
**Surface:** Command Board / Plan anchor pane / recap ingest  
**Created:** 2026-06-20

---

## 1. Decision

Plan recap ingest now treats `frontmatter_seed.md` as a **deterministic skeleton plus human/LLM review boundary**, not as a fully hand-authored artifact.

The workflow is:

```text
raw notes
→ _ingest_staging
→ canonical Session Recaps
→ _normalized
→ deterministic frontmatter seed skeleton
→ reviewed/blessed route allowlist
→ breadcrumb_query_run --ingest-routing-only
→ _breadcrumbed
→ _session_memory
```

The deterministic builder is:

```bash
uv run python scripts/build_recap_frontmatter_seed.py --campaign 2 --session 23
```

It reads the normalized recap and existing corpus vocabulary, then writes the default
`Session Recaps/_breadcrumbed/Session N - <slug>.frontmatter_seed.md` path. Use `--stdout`
for review without writing.

---

## 2. Why This Is the Right Boundary

The seed has two classes of information.

**Deterministic vocabulary** is already available from project state:

- Campaign/session identity and normalized recap path.
- Party name and PC roster from `_party_registry.json`.
- PC hub routes from `PCs/<slug>/README.md`.
- Known NPC route vocabulary from `_npc_registry.json`.
- Mentioned NPC/location hubs from current-campaign and setting README frontmatter.
- Existing aliases already curated into the registry.

This should not require operator memory or ad hoc copy-adaptation from prior sessions.

**Judgment-bearing content** still needs review:

- New hub candidates for events, factions, creatures, or durable objects.
- Open questions.
- Whether a mere mention is important enough to tag.
- Aliases/spellings not already in a registry or hub.
- Ambiguous route ownership when registry/corpus cannot decide.

Landing here keeps Plan useful without pretending Build exists yet. Plan can prepare and expose the route allowlist; Build will eventually own durable world-object creation and richer vocabulary maintenance.

---

## 3. User State as Narrowing Context

Initial user state can provide a lot of narrowing signal if it says:

- Active campaign.
- Current live session.
- Last fully ingested or last worked session.
- Intended surface: Plan or Play.
- Current task shape: ingest, planning, live query, combat, runbook edit.

For **Plan**, this is high-value. It narrows corpus work to a campaign folder, a session range, the current descriptor/runbook target, and the ingest stack for the immediately prior session. It is enough to choose default paths, prior-session roster, likely recap family, and status checks without the user restating them.

For **Play**, it is also high-value but should be used differently. It narrows the active runbook, session memory, combat state, and overlay return target. Play should not expose the whole ingest pipeline by default; it should consume the activated memory and surface only table-useful failures.

For **Build**, the same state is weaker. It tells Build where pressure came from, but not enough to create durable world objects automatically. Build decisions need subject ownership, canon layer, promotion rules, and GM review.

That is why the deterministic seed skeleton belongs in Plan: it uses narrow state to assemble known vocabulary, then stops before durable-world judgment.

---

## 4. Workflow Signals

`dmb_raw_recap_ingest_status_v1` now includes:

- `paths.frontmatter_seed`
- authority lane `frontmatter_seed: reviewable_route_allowlist`
- state `frontmatter_seed_required` when normalized recap exists but seed does not
- state `frontmatter_seed_found` when the seed is present
- `next_actions[]` pointing first to `scripts/build_recap_frontmatter_seed.py`, then to `breadcrumb_query_run --ingest-routing-only`

`breadcrumb_required` remains expected, not a failed job. The session is not retrieval-ready until breadcrumb and session-memory records exist.

---

## 5. Non-Goals

- No automatic new hub creation.
- No automatic `new_hub_candidates` judgment.
- No in-pane LLM breadcrumb execution in this slice.
- No Build-surface object editing.
- No claim that the deterministic skeleton is final; it is a reviewable starting point.

---

## 6. Verification

Focused verification:

```bash
uv run pytest tests/test_recap_frontmatter_seed.py tests/test_live_recap_ingest_pipeline.py tests/test_live_recap_ingest_api.py tests/test_recap_ingest_helpers.py -q
```

Dry-run a live session seed without overwriting:

```bash
uv run python scripts/build_recap_frontmatter_seed.py --campaign 2 --session 23 --stdout
```

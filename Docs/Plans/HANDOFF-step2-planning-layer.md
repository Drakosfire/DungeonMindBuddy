# Handoff: Step 2 — Planning Layer Boundary

## Read First

- `Docs/Design/DESIGN-layered-canon-vertical-slice.md` — the canonical design doc. Read the whole thing. It captures the three-layer model, architecture decisions, CLI chat loop target, two-pass extraction architecture, two-granularity model, blind A/B eval split, and all findings from Step 1.

## What's Done

**Step 1 is complete.** 8 evidence units and 10 facts hand-authored from the City of Mirathorn doc, run through the existing reducer, producing a world canon projection. Schema extended with location/faction attributes (`geography`, `history`, `demographics`, `defenses`, `economy`, `governance`, `atmosphere`, `goals`). All 18 existing tests pass. Committed as `b1cdf23` and `368259d`.

Key artifacts:
- `evals/mirathorn_vertical_slice/input/` — evidence units, facts, empty conflicts/decisions
- `evals/mirathorn_vertical_slice/run_step1.py` — runner that validates, projects, renders
- `evals/mirathorn_vertical_slice/output/world_projection.json` — the projection output
- `schemas/v0.1/common.schema.json` — attribute enum now shared via `$defs/attribute`

## What's Next: Step 2

Prove the planning layer boundary holds with real Mirathorn content.

### Do This

1. **Author 2–3 planning-layer evidence units** as new entries in the existing `evidence_units.json`. These represent GM planning notes — things like "the protest will escalate into a riot," "the merchant guild has planted a spy in the guard," "Brother Ashwood will attempt to poison the water supply." Tag them:
   - `canon_layer: "campaign"`
   - `campaign_id: "longmont_01"`
   - `source_class: "planning_document"`

2. **Author 2–3 planning-layer facts** linked to those evidence units. Use `truth_state: "PREP"` and `source_authority: "planning_prep"`. These should overlay or extend the world canon — e.g., a new `operational_status` for Shepherd's Flock that says they're about to escalate, or a new entity (Brother Ashwood) with `goals`.

3. **Extend `run_step1.py` (or create `run_step2.py`)** to run two projections:
   - World projection: `campaign_id=None` — should show only the original world canon facts
   - Campaign projection: `campaign_id="longmont_01"` — should show world canon + planning overlay
   
4. **Verify the gate:** World projection is unchanged from Step 1. Campaign projection adds the planning facts without mutating world canon. The provenance on each fact clearly shows which layer it came from.

### What to Watch For

- **Conflicts:** If a planning fact asserts something about an entity that world canon also has a fact for (e.g., a new `operational_status` for the Shepherd's Flock), the reducer should detect a conflict. The planning fact should win in the campaign projection but the world fact must remain in the world projection.
- **New entities:** Brother Ashwood doesn't exist in world canon. He should appear only in the campaign projection.
- **`truth_state` handling:** The reducer's `ACTIVE_TRUTH_STATES` includes `PREP`, so planning facts should be included in campaign projections. Verify this.

### Acceptance

- World projection output identical to Step 1 output
- Campaign projection includes all world canon facts + planning overlay facts
- At least one conflict detected (world vs. planning operational_status for Shepherd's Flock)
- New entity (Brother Ashwood) appears only in campaign projection
- All schemas validate
- All existing tests pass

## Architecture Decisions Made (Don't Revisit)

- The projection is agent context, not GM output. The LLM renders prose from it.
- Evidence units are light provenance records. Facts are the retrieval surface.
- Entity extraction is recall-oriented (wide net, prune later).
- The GM declares canon_layer in frontmatter. The system never guesses it.
- CLI chat loop is the success target. Frontend is wiring after that.

## Verification Commands

- `uv run ruff check .`
- `uv run pytest tests/ --maxfail=1`
- `uv run python evals/mirathorn_vertical_slice/run_step1.py` (or `run_step2.py`)

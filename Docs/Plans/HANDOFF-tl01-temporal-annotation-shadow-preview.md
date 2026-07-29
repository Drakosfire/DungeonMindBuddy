# HANDOFF — TL01: Temporal Annotation Overlay and Shadow Preview

**Created:** 2026-07-29
**Project:** DungeonBuddy / DungeonMindBuddy
**Repository:** `Drakosfire/DungeonMindBuddy`
**Status:** ACTIVE — next Timeline preparatory coding slice
**Required dependency:** PR `#448`, merged as `79f57da0e4fa1666484b13fc4643499bca717384`
**Required implementation base:** current clean `origin/main` containing that merge; record the exact SHA before coding
**Suggested branch:** `feat/tl01-temporal-shadow-preview`
**Suggested worktree:** existing isolated Timeline worktree
**Expected PR count:** one
**Mode:** Strict sidecar contract, deterministic transformation, and evaluation tooling
**No Timeline UI:** explicit
**No authoritative graph writes:** explicit

---

## §0 Mission

Introduce a strict, evidence-bound temporal annotation sidecar and deterministic shadow-preview builder that can show how existing candidate assertions would look with `TemporalEnvelopeV1` without changing:

* the existing candidate graph schema;
* the existing candidate-to-contribution mapper;
* the existing promotion path;
* any accepted assertion;
* any contribution ledger;
* any world graph revision;
* or any product surface.

The result must let later agents evaluate:

```text
existing candidate assertion
+ deterministic source-time derivation
+ optional source-grounded occurrence or valid time
→ shadow temporal assertion identity
→ inspectable before/after report
```

The output is an evaluation artifact.

It is not a `GraphContribution` and must not be consumable by merge or publication code.

Full specification for this slice lives in the conversation that authored this handoff (TL01 sections §1–§33). Implementation follows that contract verbatim.

---
pr_body_template: |
  ## Summary

  Materialize the first representative Eldyrwild World Supergraph from the named Longmont Campaign 2 acceptance corpus and prove coverage, provenance, reconstruction, health, and runtime graph-head availability.

  ## Verification

  Paste the verbatim output from every command in §7.

  ## `git diff --stat` (§4 paths only)

  ```text
  Paste the filtered diff stat here.
  ```

  ## What stayed unchanged

  Confirm that Agent Interaction runtime, tool registry, preview-confirm UX, Projection Engine, Plan migration, content-pack runtime, and silent/autonomous writes to the graph were out of scope and not landed.
---

# HANDOFF — PR006: Initial World Supergraph Materialization

**Created:** 2026-07-11 (UTC)  
**Updated:** 2026-07-11 — made dispatchable (enumerated §4 / §7; post-merge ownership clarified)  
**Status:** READY after PR005B merges — do not dispatch until tracker marks PR006 `READY`.  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Expected GitHub PR:** `#330`  
**Target base branch:** `main`  
**Suggested branch:** `campaign-supergraph/pr006-initial-world-supergraph-materialization`  
**Suggested PR title:** `feat(graph-memory): materialize Eldyrwild C2 acceptance World Supergraph`  
**Roadmap slice:** `PR006 — Initial World Supergraph Materialization`  
**Tracker anchor:** `Docs/Plans/PR-TRACKER-campaign-supergraph.md`  
**Architecture anchor:** `Docs/Design/ARCHITECTURE-campaign-supergraph.md`  
**Predecessor:** GitHub PR `#329` (PR005B — Agent Tool Contract + Authored Prep Contributions)  
**Successor:** `PR007 — Projection Engine`  
**Mode:** Runtime materialization of the named acceptance corpus. Not agent tooling. Not Projection Engine.

> Expected PR number assumes `#329` is the latest at authoring time. Rename if another PR takes `#330` before dispatch.

---

## §1 Mission

Materialize the first representative Eldyrwild World Supergraph from the named Longmont Campaign 2 acceptance corpus and prove coverage, provenance, reconstruction, health, and runtime graph-head availability without implementing projection or agent tooling.

---

## §2 Why this slice

PR002–PR005 established world storage, Kernel boundary, identity decisions, and durable `GraphContribution` merge/rebuild. PR005A/PR005B re-anchored docs and defined agent/tool contracts so materialization is not blocked by stale authority or agent-runtime scope creep.

**Current seams (inspected 2026-07-11):**

- Kernel public APIs exist: `create_graph_contribution`, `merge_contribution_to_revision`, `rebuild_from_contributions`, `build_contribution_integrity_report`, `publish_world_graph_revision`, `open_world_graph_head`, `open_current_world_graph`, `build_world_integrity_report`.
- On-disk world layout: `<root>/graph_memory/worlds/<worldId>/head.json` (+ revisions, contributions, identity_decisions).
- **No** operator CLI yet converts the named acceptance corpus into world-head contributions. Preview-union materialization (`preview_run_materialize.py`, Graph Review adapters) is the wrong object.
- Live control still defaults to preview union / fixture via `union_supergraph_projection_adapter.py` when no selectors are set — quarantine target for this slice (backend only; not Plan UI).

This slice converts:

```text
Kernel + contribution contracts
→ first representative world graph head (worldId=eldyrwild)
→ coverage / health / reconstruction proof
→ Plan trust boundary statement
→ backend runtime prefers world head when present
```

This slice explicitly does **not** include:

```text
Agent Interaction runtime
tool registry
preview-confirm UX
Projection Engine
Plan migration
content-pack runtime
silent / autonomous writes to the graph
Hermes runtime
```

---

## §3 Authoritative inputs

Read in order. GitHub `main` is canonical.

1. `Docs/Plans/PR-TRACKER-campaign-supergraph.md` — PR006 section (sole sequence authority).
2. `Docs/Design/ARCHITECTURE-campaign-supergraph.md` — tenancy, dual authority, contribution, graph head.
3. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` — Phase 3.
4. `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md` — know what **not** to land (PR011).
5. `Docs/Design/CONTRACT-graph-kernel-boundary.md` — apps use Kernel only.
6. `Docs/Anchors/CORPUS-ANCHOR.md` — corpus path conventions (not sequencing).
7. `.cursor/rules/external-agent-pr-loop.mdc` and `.cursor/skills/external-agent-pr-loop/SKILL.md`.
8. Kernel: `src/graph_memory/kernel/` (public).
9. Storage internals (read-only context; do not import from apps): `src/graph_memory/world_supergraph/`.
10. Quarantine target: `apps/live_control_server/services/union_supergraph_projection_adapter.py`.

### Corpus path conventions (no corpus mutation)

| Anchor | Repo-relative path |
|---|---|
| Corpus root | `corpus/eldyrwild-markdown/` |
| C2 recaps | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session {1..23}*.md` |
| Mirathorn | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/` |
| Mireward | `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mireward/` |
| C2 hubs | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/{PCs,NPCs,Factions,Statblocks,...}/` |
| `worldId` | `eldyrwild` |

---

## §4 Files in scope (allowlist)

The expected diff must be expressible entirely from this table. Do not broaden without explaining in the PR body before opening the PR.

| Action | Path | Purpose |
|---|---|---|
| Create | `scripts/materialize_world_supergraph.py` | Operator CLI: inventory → contributions → Kernel merge/publish → reports |
| Create | `src/graph_memory/world_materialization/__init__.py` | Package marker |
| Create | `src/graph_memory/world_materialization/inventory.py` | Requested / ingested / skipped source inventory for named acceptance corpus |
| Create | `src/graph_memory/world_materialization/run.py` | Orchestration calling **only** `graph_memory.kernel` for merge/publish/rebuild |
| Create | `src/graph_memory/world_materialization/health_report.py` | Machine-readable coverage / health / Plan-trust payload |
| Create | `tests/test_world_supergraph_materialization.py` | Acceptance inventory + reconstruction + hub requirements |
| Modify | `apps/live_control_server/services/union_supergraph_projection_adapter.py` | When world head exists for `eldyrwild`, prefer Kernel world graph over `DEFAULT_FIXTURE_PATH`; retain preview selectors with explicit quarantine / retain note |
| Modify | `tests/test_live_union_supergraph_projection_adapter.py` | Prove world-head preference when head is present; preview path still documented as transitional |
| Create | `Docs/Reports/PR006-eldyrwild-c2-materialization-summary.md` | Human summary of inventory, counts, identity diagnostics, Plan trust, head revision id |
| Modify last | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Record PR006 as `DOING` (#330) only after §7 proofs pass — **never** `DONE` on this branch |

> Generated machine-readable JSON under `out/graph_memory/worlds/eldyrwild/reports/` is required by §7 but is gitignored (`out/`). Do not commit `out/**`. Commit the human summary under `Docs/Reports/` instead.

### Tracker / status ownership (normative)

```text
On the PR006 implementation branch:
  - After proofs land, tracker may set PR006 to DOING (GitHub #330).
  - The branch MUST NOT set PR006 to DONE.
  - The branch MUST NOT set PR007 to READY.

Only the post-merge atomic doc-sync (dispatcher) may:
  - set PR006 → DONE (merge date/hash)
  - set PR007 → READY
  - archive/update this handoff status
```

---

## §5 Files explicitly out of scope (denylist)

| Path | Why |
|---|---|
| `integrations/hermes/**`, `.hermes.md` | Agent/Hermes runtime is PR011 |
| `apps/live-control-ui/src/planSurface/**` | Plan migration is PR008 |
| `src/graph_memory/projection/**` (if present) / PR007 projection APIs | Projection Engine is PR007 |
| Agent tool registry / confirm UX / Agent Interaction provider | PR011 |
| Content-pack storage runtime | Deferred |
| `corpus/**` content mutation | Inventory/read only; do not rewrite campaign prose |
| Unrelated eval gold / benchmark rewrites | Not this slice |
| `src/graph_memory/world_supergraph/storage.py` imports from apps | Apps must use Kernel |
| Silent / autonomous write policy changes | Forbidden |
| Broad deletion of all preview loaders without retain notes | Quarantine with named consumers; full cleanup is PR012 safety net |

If a denied path seems necessary, stop and explain in the PR description rather than editing it.

---

## §6 Implementation contract

### 6.1 Named acceptance corpus (required)

| Family | Scope |
|---|---|
| World | `worldId=eldyrwild` |
| Campaign scope | Longmont Campaign 2 |
| Recaps | Canonical C2 Sessions **1–23** |
| PCs | All approved C2 PC hub packages |
| Worldbuilding | **Required:** Mirathorn + Mireward under `Elderwyld/Cities and Towns/` — skip of either **fails acceptance** |
| Campaign hubs | C2 NPC/faction/location hubs needed for Session 23–adjacent Plan dogfood (enumerate in inventory) |
| Mechanical | Statblocks/encounters required by initial Plan dogfood |
| Authored | Approved Graph Review assertions / identity decisions in scope at run time |

### 6.2 Required deliverables

1. **Requested / ingested / skipped inventory** with reasons for skips.
2. **Entity/edge counts by source domain.**
3. **Identity diagnostics** (unresolved / provisional / ambiguous / decided).
4. **Evidence coverage** for durable claims.
5. **Unsupported projection requirements** list (what PR007 will need that this graph does not yet support).
6. Explicit **what Plan can and cannot trust** after this materialization.
7. **Graph-head advancement** to the published acceptance revision under `out/graph_memory/worlds/eldyrwild/` (CLI `--root out`).
8. **Reconstruction / replay proof** via Kernel `rebuild_from_contributions` / integrity report (not preview stores).
9. **Removal or quarantine** of production dependence on preview runtime availability when world head exists (`union_supergraph_projection_adapter.py`).

### 6.3 CLI contract (must implement)

```bash
uv run python scripts/materialize_world_supergraph.py \
  --root out \
  --world-id eldyrwild \
  --campaign-id longmont-c2 \
  --sessions 1-23 \
  --require-hubs mirathorn,mireward \
  --corpus-root corpus/eldyrwild-markdown \
  --report-json out/graph_memory/worlds/eldyrwild/reports/materialization_report.json \
  --report-md Docs/Reports/PR006-eldyrwild-c2-materialization-summary.md \
  --publish
```

Orchestration must call Kernel only (`merge_contribution_to_revision`, `rebuild_from_contributions`, integrity reports). Do not import `graph_memory.world_supergraph.storage` / `paths` from the CLI or from `apps/`.

### 6.4 Adapter quarantine contract

In `union_supergraph_projection_adapter.py`:

- If an `eldyrwild` world head exists at the configured root, load via Kernel (`open_current_world_graph` / equivalent) instead of `DEFAULT_FIXTURE_PATH`.
- Preview-union / manifest / explicit store-path selectors may remain for named remaining consumers with a retain block naming the required deletion PR (PR007/PR008/PR012 as appropriate).
- Do not migrate Plan UI selectors in this PR.

### 6.5 Non-goals (hard)

Out of scope: Projection Engine (PR007), Agent Interaction runtime, tool registry, preview-confirm UX, Plan migration, content-pack runtime, Hermes runtime, and silent / autonomous writes to the graph.

---

## §7 Verification commands

The worker must run **every** command and paste verbatim output into the PR body. The reviewer reruns them.

```bash
# 1. Kernel contribution merge / rebuild / integrity / public API still green.
# Owns §9: reconstruction independence from preview stores (baseline Kernel proof).
uv run pytest \
  tests/test_graph_kernel_contribution_rebuild.py \
  tests/test_graph_kernel_contribution_integrity.py \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_kernel_public_api.py \
  tests/test_graph_kernel_identity_decisions.py \
  -q
```

```bash
# 2. Exact allowlist enforcement (no Hermes / Plan UI / Projection Engine paths).
# Owns §9: no agent tooling / Plan migration / Projection Engine landed.
uv run python -c '
import subprocess
allowed = {
    "scripts/materialize_world_supergraph.py",
    "src/graph_memory/world_materialization/__init__.py",
    "src/graph_memory/world_materialization/inventory.py",
    "src/graph_memory/world_materialization/run.py",
    "src/graph_memory/world_materialization/health_report.py",
    "tests/test_world_supergraph_materialization.py",
    "apps/live_control_server/services/union_supergraph_projection_adapter.py",
    "tests/test_live_union_supergraph_projection_adapter.py",
    "Docs/Reports/PR006-eldyrwild-c2-materialization-summary.md",
    "Docs/Plans/PR-TRACKER-campaign-supergraph.md",
}
changed = set(subprocess.check_output(
    ["git", "diff", "--name-only", "origin/main...HEAD"],
    text=True,
).splitlines())
extra = sorted(changed - allowed)
assert not extra, f"Files outside §4 allowlist: {extra}"
forbidden = [p for p in changed if (
    p.startswith("integrations/hermes/")
    or "planSurface/" in p
    or "/projection/" in p
    or p.startswith("corpus/")
)]
assert not forbidden, f"Denylist hits: {forbidden}"
print("allowlist ok")
print("\n".join(sorted(changed)))
'
```

```bash
# 3. Materialization CLI smoke (named acceptance corpus → publish head + reports).
# Owns §9: head exists; Sessions 1–23 inventory; Mirathorn/Mireward required;
# PC/NPC/faction/location/statblock inventory; coverage report fields.
uv run python scripts/materialize_world_supergraph.py \
  --root out \
  --world-id eldyrwild \
  --campaign-id longmont-c2 \
  --sessions 1-23 \
  --require-hubs mirathorn,mireward \
  --corpus-root corpus/eldyrwild-markdown \
  --report-json out/graph_memory/worlds/eldyrwild/reports/materialization_report.json \
  --report-md Docs/Reports/PR006-eldyrwild-c2-materialization-summary.md \
  --publish
```

```bash
# 4. Reconstruction / replay proof against published head (Kernel only; no preview stores).
# Owns §9: reconstruction proof; approved corrections/identity decisions survive rebuild.
uv run python - <<'PY'
from pathlib import Path
import graph_memory.kernel as kernel

root = Path("out")
world_id = "eldyrwild"

head = kernel.open_world_graph_head(root, world_id)
print("head_revision_id:", head.head_revision_id)

rebuild = kernel.rebuild_from_contributions(root, world_id=world_id, publish=False)
assert "rebuild_equivalent_to_head" in rebuild.diagnostics, rebuild.diagnostics

integrity = kernel.build_contribution_integrity_report(
    root, world_id=world_id, check_rebuild=True
)
assert integrity.rebuild_equivalent_to_head is True, integrity

world_health = kernel.build_world_integrity_report(root, world_id)
assert world_health.load_ok and world_health.validation_ok, world_health
print("rebuild_equivalent_to_head: OK")
print("world_integrity: OK")
PY
```

```bash
# 5. Materialization acceptance tests.
# Owns §9: representative corpus inventory; provenance linkage; hub requirements.
uv run pytest tests/test_world_supergraph_materialization.py -q
```

```bash
# 6. Adapter quarantine: world head preferred when present; boundary guards still green.
# Owns §9: production runtime availability no longer depends on preview selectors
# when world head exists (preview paths retained only with named consumers).
uv run pytest \
  tests/test_live_union_supergraph_projection_adapter.py \
  tests/test_graph_kernel_boundaries.py \
  -q
```

```bash
# 7. Inventory / coverage artifacts exist with required keys.
# Owns §9: machine-readable coverage + health + Plan trust boundaries.
test -f out/graph_memory/worlds/eldyrwild/head.json
test -f out/graph_memory/worlds/eldyrwild/reports/materialization_report.json
test -f Docs/Reports/PR006-eldyrwild-c2-materialization-summary.md
uv run python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path("out/graph_memory/worlds/eldyrwild/reports/materialization_report.json").read_text())
required = [
    "inventory",
    "counts_by_source_domain",
    "identity_diagnostics",
    "evidence_coverage",
    "unsupported_projection_requirements",
    "plan_trust_boundary",
    "head_revision_id",
]
missing = [k for k in required if k not in r]
assert not missing, missing
inv = r["inventory"]
assert "requested" in inv and "ingested" in inv and "skipped" in inv
print("report keys OK")
print("head_revision_id:", r["head_revision_id"])
PY
```

```bash
# 8. Tracker final-state check (implementation branch).
# Owns §9: tracker may be DOING; must not mark PR006 DONE or PR007 READY on this branch.
uv run python - <<'PY'
from pathlib import Path
text = Path("Docs/Plans/PR-TRACKER-campaign-supergraph.md").read_text()
section_6 = text.split("## PR006 — Initial World Supergraph Materialization", 1)[1].split("---", 1)[0]
section_7 = text.split("## PR007 — Projection Engine", 1)[1].split("---", 1)[0]
assert "`DONE`" not in section_6, "PR006 must not be DONE on the implementation branch"
assert "`READY`" not in section_7 or "BLOCKED" in section_7.split("**Status:**", 1)[1][:80]
# Prefer explicit DOING once proofs land; READY-before-start is only pre-dispatch.
assert ("`DOING`" in section_6 and "#330" in section_6) or "`READY`" in section_6 or "`BLOCKED`" in section_6
print("tracker ownership ok")
PY
```

```bash
# 9. Reviewer-facing diff.
git diff --stat origin/main...HEAD -- \
  scripts/materialize_world_supergraph.py \
  src/graph_memory/world_materialization/__init__.py \
  src/graph_memory/world_materialization/inventory.py \
  src/graph_memory/world_materialization/run.py \
  src/graph_memory/world_materialization/health_report.py \
  tests/test_world_supergraph_materialization.py \
  apps/live_control_server/services/union_supergraph_projection_adapter.py \
  tests/test_live_union_supergraph_projection_adapter.py \
  Docs/Reports/PR006-eldyrwild-c2-materialization-summary.md \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md
```

---

## §8 Reporting contract

PR body must include:

1. Predecessor verification (PR005B merged).
2. Inventory summary (requested / ingested / skipped).
3. Entity/edge counts by source domain.
4. Identity diagnostics.
5. Evidence coverage highlights.
6. Unsupported projection requirements.
7. What Plan can / cannot trust.
8. Graph head revision id + reconstruction proof (§7 cmd 4).
9. Preview-runtime quarantine notes (adapter retain/delete plan).
10. `git diff --stat` and verbatim §7 outputs.
11. Explicit confirmation that agent tooling and Projection Engine were out of scope and not landed.
12. Tracker state: PR006 `DOING` (#330) only; **not** `DONE`; PR007 still blocked/not READY.

---

## §9 Acceptance rubric

Every behavioral guarantee is paired with a §7 command.

- [ ] Eldyrwild world graph head exists for Longmont Campaign 2 scope — §7 cmds 3, 7.
- [ ] Canonical C2 Sessions 1–23 are in the requested inventory with ingest/skip outcomes — §7 cmds 3, 5, 7.
- [ ] Required Mirathorn and Mireward world hubs are present (skip of required hubs fails acceptance) — §7 cmds 3, 5.
- [ ] Approved C2 PC hubs and needed NPC/faction/location hubs are inventoried — §7 cmds 3, 5, 7.
- [ ] Required statblocks/encounters for initial Plan dogfood are inventoried — §7 cmds 3, 5, 7.
- [ ] Approved Graph Review assertions / identity decisions in scope survive reconstruction — §7 cmds 1, 4, 5.
- [ ] Coverage + health report includes counts, identity diagnostics, evidence coverage, unsupported projection requirements, and Plan trust boundaries — §7 cmd 7 (+ human summary in Docs/Reports).
- [ ] Reconstruction/replay proof does not depend on preview union stores as the source of truth — §7 cmds 1, 4.
- [ ] Production runtime availability for this world no longer depends on preview graph selectors when world head exists (deleted or quarantined with retain note) — §7 cmd 6.
- [ ] No Agent Interaction runtime, tool registry, preview-confirm UX, Projection Engine, Plan migration, content-pack runtime, Hermes runtime, or silent / autonomous writes to the graph landed — §7 cmd 2.
- [ ] Tracker on this branch does **not** mark PR006 `DONE` or PR007 `READY`; at most PR006 `DOING` (#330) after proofs — §7 cmd 8.
- [ ] Every changed file is inside the §4 allowlist — §7 cmd 2.

---

## §10 Out-of-band notes

- PR005B defined agent/tool contracts; this PR must not expand into PR011.
- A multi-source fixture is not a substitute for the named acceptance corpus.
- “Real” is not the same as “representative” — required worldbuilding hubs must ingest.
- Preview-union materialization remains a transitional Graph Review path with named consumers until PR007/PR008/PR012 deletion.
- **Post-merge dispatcher** (not the worker) performs atomic doc-sync: PR006 → `DONE`, PR007 → `READY`, archive/update this handoff.

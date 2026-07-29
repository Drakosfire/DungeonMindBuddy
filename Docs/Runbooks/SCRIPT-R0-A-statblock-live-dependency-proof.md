# Script — R0-A Statblock live dependency proof

**Gate:** `R0-A`  
**Authority:** [`RUNBOOK-authored-world-object-magic-moment-dogfood.md`](RUNBOOK-authored-world-object-magic-moment-dogfood.md) §4  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Result file:** `Docs/Reports/MAGIC-MOMENT-R0-A-<YYYY-MM-DD>.md`

This is an **operator script**, not an automated substitute for the Workbench.
Every pass/fail judgment must come from the user-facing path. Shell checks
below are preflight and identity capture only.

## 0. Pass rule (do not soft-pass)

Pass only when:

```text
real provider generate
→ edit a complete mechanic
→ validate working copy
→ revise once
→ accept exact revision
→ browser reload
→ reopen the same (statblock_id, revision_id, digest)
```

Mocks, corpus-promotion Statblock View, or “generate failed but draft exists”
do **not** count. Unavailable DungeonMind / provider → `BLOCKED_DEPENDENCY`.

## 1. Preflight — three processes

R0-A needs:

| Process | Default | Role |
|---|---|---|
| DungeonMindServer | `http://127.0.0.1:7860` (Buddy `.env` `DUNGEONMIND_STATBLOCKS_BASE_URL`) | Real generate / validate / accept downstream |
| Buddy live-control API | `http://127.0.0.1:8000` | ThreatDraft, candidates, revise, accept orchestration |
| Live Control UI | `http://127.0.0.1:5173` | Workbench surface |

### 1.1 DungeonMindServer

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindServer
uv run uvicorn app:app --host 127.0.0.1 --port 7860
```

Health (no secret in the URL):

```bash
curl -fsS http://127.0.0.1:7860/api/internal/dungeonbuddy/v1/statblocks/health/live
```

### 1.2 Buddy live-control API

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22
uv run uvicorn apps.live_control_server.main:app --reload --host 127.0.0.1 --port 8000
```

Confirm surface + readiness:

```bash
curl -fsS http://127.0.0.1:8000/api/live/surface | head -c 80
curl -fsS http://127.0.0.1:8000/api/live/statblocks/v1/readiness | python3 -m json.tool
```

Required readiness shape for a real attempt:

```text
configured: true
available: true
downstream_status: not downstream_unavailable
```

If `available: false` with `downstream_unavailable`, stop and record
`BLOCKED_DEPENDENCY` — do not invent a mock path.

### 1.3 Live Control UI

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/apps/live-control-ui
npm run dev -- --host 127.0.0.1 --port 5173
```

Confirm:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5173/
```

### 1.4 Record repository SHA

```bash
cd /home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
git rev-parse HEAD
git show -s --format='%h %s' HEAD
```

Paste into the report as **Repository SHA**.

## 2. Open the product door

1. Open **http://127.0.0.1:5173/** (launcher). Do not start on a deep link.
2. Open the full Live Control board: **http://127.0.0.1:5173/surface**
   (URL-reachable; not primary nav — acceptable for this Workbench gate).
3. In surface layout controls, **enable** module `statblock_workbench`
   (**Statblock Workbench**). It is catalogued but `enabled_by_default: false`.
4. Expand the Statblock Workbench panel.

Do **not** use **Statblock View** (corpus-promotion path) for this gate.

## 3. Choose a real nontrivial Threat

Use a Campaign 2 / Eldyrwild concept you actually care about — not “Test Goblin”.

Suggested description shape (first line = name):

```text
Mireward Latchling
A reed-choked latching scavenger from the Mireward verge that clamps onto
boots and hitching posts, then sings a thin under-hymn to call siblings.
Prefer grapples and damp-terrain ambush over fair fights.
```

Optional controls (only if needed):

- Target CR / party level / party size for a believable generate
- Exact graph revision (`rev:…`) only if bootstrap head resolution fails

Record: concept name, why it is nontrivial, graph revision shown at create.

## 4. Create & generate (real provider)

1. Paste the description into **Description**.
2. Click **Create & generate**.
3. Wait until a candidate loads (not a silent draft-only success).

Capture immediately:

- draft ID / version (created-draft identity)
- candidate ID
- any provider / contract / parse error text exactly

If generate fails with downstream/auth/timeout: classify honestly
(`BLOCKED_DEPENDENCY` vs product miss). Use **Retry generation (same draft)**
only for the same attempt — do not mint a second draft to hide the failure.

## 5. Edit a complete mechanic

In the loaded candidate editor, change at least one **mechanical** field, e.g.:

- an action’s attack bonus, damage, or save DC; or
- HP / AC / speed; or
- a trait that alters combat behavior

Do **not** count rename-only or flavor-only edits.

Capture: field(s) changed and before/after values.

## 6. Validate working copy

1. Click **Validate working copy** in the edit dock.
2. Require a successful preview receipt with no blocking field/global errors.
3. If validation fails, fix the definition and re-validate.
4. Note: validation is **not** graph publish and **not** mechanics accept.

Capture: validation request outcome / issue counts if any.

## 7. Revise once

1. Open **Revise with AI**.
2. Enter explicit instruction lines (one per line), e.g.:

```text
Increase hit points modestly for a sticky ambusher
Add one latching reaction that uses the edited grapple fiction
Keep element keys where possible
```

3. Leave **Preserve element keys where possible** checked unless you are
   intentionally testing key churn.
4. Click **Create revised proposal**.
5. On success: confirm Proposal history shows **source + new** refs, source
   status unchanged, new lineage is edited-working-copy.
6. If transport fails: hard reload, confirm **Resume same revise** keeps the
   same request ID (do not Start new unless terminal).

Capture: revise `request_id`, result label, new candidate ID.

## 8. Accept exact revision

1. Ensure the candidate you want saved is active and re-validated if needed.
2. Click **Accept/Save mechanics**.
3. Wait for a durable success that shows exact locator:

```text
statblock_id
revision_id
digest
```

4. Confirm UI does **not** claim World Graph publish.

Capture the locator triple exactly.

## 9. Reload proof (hard gate)

1. Hard-reload the browser (or close tab and reopen).
2. Return to `/surface` → Statblock Workbench.
3. Reopen the accepted revision by the exact locator (Advanced recovery /
   draft+candidate restore as the product currently requires — note friction).
4. Confirm the same `(statblock_id, revision_id, digest)` is still the
   accepted identity for that draft.

If you cannot reopen without inventing IDs outside the UI, record
`PASS_WITH_FRICTION` or `FAIL_PRODUCT` and name **AUTHORING-LIBRARY** as the
smallest next slice — do not fake reopen via raw filesystem edits.

## 10. Report

Copy the runbook template into:

```text
Docs/Reports/MAGIC-MOMENT-R0-A-<YYYY-MM-DD>.md
```

Minimum durable identities to fill:

- draft ID/version
- candidate ID(s) (source + revised)
- revise request_id / result
- accepted `statblock_id` / `revision_id` / `digest`
- graph revision used at create
- readiness snapshot (`available`, `downstream_status`)

## 11. Verdict cheat-sheet

| Observation | Result |
|---|---|
| Full path + exact locator survives reload | `PASS` |
| Path works but reopen/browse is painful | `PASS_WITH_FRICTION` |
| Workbench/UI/contract wrong while provider is up | `FAIL_PRODUCT` or `FAIL_ARCHITECTURE` |
| DM `:7860` down / auth / provider unavailable | `BLOCKED_DEPENDENCY` |

## 12. After the report

Update the tracker dogfood ledger pointer to the report path.
Dispatch only the **smallest** enabling slice implied by friction — do not
auto-start `SBW06d` or `SBW08`.

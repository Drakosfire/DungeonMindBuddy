# C2 Session 27 native Play dogfood — operator runbook

Operational instructions for D3. This file is not architecture, roadmap, or dispatch authority.

Authority:

- `Docs/Plans/HANDOFF-PLAY-c2s27-native-dogfood.md`
- `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`

Product rule: use shipped `/play` Start Run. Do not curl or Python-create a Play Run or manifest. Do not patch product code when friction appears; record it in the report.

Runtime ownership: this checkout's `out/` is the lane's workspace/runtime state. Do not run another agent's destructive dogfood reset against the same workspace while the session is active.

---

## Phase A — prepare exact Runbook

From repository root on the PR head:

```bash
uv run python scripts/c2s27_native_play_dogfood.py
uv run python scripts/c2s27_native_play_dogfood.py --apply
uv run python scripts/c2s27_native_play_dogfood.py --apply
```

Expected:

- first command is read-only;
- first `--apply` yields one exact active committed Session 27 Runbook titled `C2 Session 27 — Mireward Climax`;
- second `--apply` is a no-op on the **same document ID and revision**.

Capture:

```text
Runbook document ID:
Runbook revision:
Runbook SHA:
Target path:
```

Pinned SHA is the helper constant `EXPECTED_ARTIFACT_SHA256`. Re-run Phase A after any artifact edit.

Do not use Markdown `>` blockquotes in this Runbook. Native Play P1 admission treats them as blocking warnings even when Start Run itself succeeds.

Target path:

```text
evals/c2_live_prep/mireward-prep/content/tiptap/c2s27-mireward-climax-runbook.md
```

---

## Phase B — prove shipped Start Run

Start the existing backend/frontend normally from repository root:

```bash
uv run uvicorn apps.live_control_server.main:app --reload
```

```bash
cd apps/live-control-ui && pnpm dev
```

Then:

1. Open `/play` with **no** `run` query.
2. Confirm no existing Run or Runbook is auto-selected.
3. In `Start a Run`, deliberately choose `C2 Session 27 — Mireward Climax`.
4. Start it through the UI.
5. If a previous attempt already created a Run against an older SHA, start a **new** Run. Do not reopen the failed `/play?run=` route.
6. Capture the exact resulting Run UUID.
7. Confirm browser route is `/play?run=<that UUID>`.
8. Confirm native Play reaches READY.

Do not use curl/Python/service calls to create the Run or manifest.

Capture:

```text
Run UUID:
Observed route:
Runbook document ID/revision/SHA shown/verified:
READY result:
```

---

## Phase C — pre-session structural smoke

In Table mode verify:

- one Scene: Mireward Siege Climax;
- five Beats in authored order;
- no authored Choice/Option controls for strategic directions;
- the opening Beat represents the active breach rather than a fresh setup scene.

Focus a non-first Beat locally, then switch:

```text
Table → Runbook → Table
```

Verify:

- Runbook mode shows global session intent/current state/enemy intent;
- Runbook mode shows `Strategic directions`, `Exit ramps`, and `Open questions`;
- those global sections are not included in the final Beat body in Table mode;
- returning to Table restores local focus;
- mode switching alone writes no Runtime state.

---

## Phase D — real Runtime smoke before/at table

Using shipped controls only:

1. set/focus the appropriate current Scene/Beat when the session starts;
2. resolve or unresolve at least one Beat when true;
3. write at least one scratch note if useful;
4. hard reload the exact `/play?run=<uuid>` route;
5. confirm persisted authoritative progress remains.

Do not mutate a Beat merely to satisfy evidence if it would make the real session state false.

---

## Phase E — actual Session 27 dogfood

Run the actual session from this Runbook if practical.

Capture **moments of friction**, not every click.

Record when any of these occurs:

- needed information is not discoverable quickly enough;
- Runbook mode is too dense to scan;
- Table mode hides essential global context;
- Beat granularity fights the real session;
- a Beat is useful but the current Runtime controls are awkward;
- the GM needs a graph object/reference and leaving Play breaks flow;
- the GM needs exact mechanics/Combat and the handoff is awkward;
- authoring/setup overhead dominates the value of Play;
- the party takes an unexpected direction and the Runbook handles it well or poorly;
- a product error blocks continued use.

For each meaningful event record:

```text
Moment:
What I was trying to do:
What Play showed / required:
Impact at table:
Workaround used:
Candidate capability, if any:
```

Do not implement the workaround in this PR. Write observations into
`Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`.

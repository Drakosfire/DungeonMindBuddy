# Report — Play readability + active-Run dogfood

## Status

**READABILITY PASS / CONTINUITY PASS**

The Play-local readability implementation passed the normal-viewport rehearsal
and the active-Run continuity scenarios required by Lane A2. The corrected
replacement attempt was made through the actual StartRunPanel flow while the
backend was unavailable: it reached the styled blocked state before allocating
a Run UUID, and the previous active U1 remained active. A later U3 was created
through the normal StartRunPanel flow and reached READY before replacing U1.
No structural Play, Run lifecycle, or chooser-status repair was made here.

## Implementation head

- Candidate implementation evidence head: `58e1e7bc42e687672c39b454fa401111602cc8be`
- Candidate UI: `apps/live-control-ui` from the A2 worktree, served at `127.0.0.1:5175`
- Changed production path: `apps/live-control-ui/src/playSurface/playSurface.css`

## Base / predecessor merge

- Base: `d4c6fb365b1e8958f6a1989a9f88fcde1b844e73` (PR #625 merge)
- Predecessor: PR #625 / Lane A1 active-Run continuity
- Backend: merged-main-equivalent A1 checkout, `127.0.0.1:8001`, same
  checkout-local Play state store; restarted once during this rehearsal
- No second backend or state migration was used

## Environment / viewport / zoom

- Browser: Cursor IDE Browser, Cursor `3.16.29`, Chrome `144.0.7559.236`
- Native keyboard verification: isolated Chromium `136.0.0.0` through direct CDP
- OS: Linux `7.0.0-28-generic`
- Candidate viewport measured by CDP: `1220 × 945` CSS pixels
- Native focus audit viewport: `780 × 388` CSS pixels
- Browser zoom: 100%
- Candidate frontend: `http://127.0.0.1:5175`
- State-owning backend: `http://127.0.0.1:8001`

## Exact Run identities U1/U2/U3

- U1: `11111111-1111-4111-8111-111111111111`
  - previous active READY baseline; it remained active through the failed replacement
- U2: **no UUID allocated**
  - corrected failed replacement attempt through Start New → StartRunPanel
  - the selected Runbook reached the styled blocked state while the backend was
    intentionally paused; the attempt stopped before `putPlayRun`, so no U2
    file was created and U1 remained active
- U3: `2487dd8f-df0f-4a4b-abd1-ae4df44dc4ad`
  - successful explicit replacement created through StartRunPanel and READY
  - final active Run after the rehearsal

Runbook under test: **Lane A1 Dogfood Runbook**, artifact
`77aa2879-77c7-4787-8267-b36f895235d7`, committed revision `2`.

The existing `22222222-2222-4222-8222-222222222222` incomplete Run and
`7ae97d9a-9dc0-46a9-bdfd-6362708785b8` READY Run are retained as historical
artifacts from the superseded Cycle 1 rehearsal; they are not the corrected
U2/U3 identities above.

## Before/after Run-store inventory

The inventory captured immediately before the corrected U2 attempt contained
the historical artifacts already present from Cycle 1:

```text
11111111-1111-4111-8111-111111111111.json
22222222-2222-4222-8222-222222222222.json
7ae97d9a-9dc0-46a9-bdfd-6362708785b8.json
```

The corrected U2 attempt created no file. After the successful U3:

```text
11111111-1111-4111-8111-111111111111.json
22222222-2222-4222-8222-222222222222.json
2487dd8f-df0f-4a4b-abd1-ae4df44dc4ad.json
7ae97d9a-9dc0-46a9-bdfd-6362708785b8.json
```

The final `GET /api/live/play-active-run` returned:

```json
{
  "schema_version": "dmb_play_active_run_v1",
  "run_id": "2487dd8f-df0f-4a4b-abd1-ae4df44dc4ad"
}
```

The corrected failed U2 attempt created no Run UUID. Navigation, reload,
chooser entry, and the backend restart likewise created no Run UUID.

## Screenshot evidence

All listed artifacts were captured from the repaired candidate UI at
implementation head `58e1e7bc42e687672c39b454fa401111602cc8be`, at 100% zoom,
with the shared AppChrome visible where applicable:

1. READY Table primary scan: `a2-cycle2-ready-table-primary-u3.png`
   - local capture: `/tmp/cursor/screenshots/a2-cycle2-ready-table-primary-u3.png`
   - PR attachment: https://github.com/user-attachments/assets/9ada7af2-b4e8-443a-ab74-1f29fa6d9ce3
2. READY Table interaction density: `a2-cycle2-table-interaction-density-u3.png`
   - local capture: `/tmp/cursor/screenshots/a2-cycle2-table-interaction-density-u3.png`
   - PR attachment: https://github.com/user-attachments/assets/c442089f-2fa5-4a25-b069-01cd3fac0dc0
3. Runbook mode: `a2-cycle2-runbook-u3.png`
   - local capture: `/tmp/cursor/screenshots/a2-cycle2-runbook-u3.png`
   - PR attachment: https://github.com/user-attachments/assets/fe4f972c-8158-4d02-9b77-29d20ffe7341
4. Chooser / Start New with corrected U3 and retained historical Runs:
   `a2-cycle2-chooser-start-new-u3.png`
   - local capture: `/tmp/cursor/screenshots/a2-cycle2-chooser-start-new-u3.png`
   - PR attachment: https://github.com/user-attachments/assets/40ae01a5-87af-4602-896c-033dbf59f2d2

These are the exact repaired-implementation browser artifacts attached to the
PR conversation and linked from the PR review comment.

## Continuity result

**PASS**

Observed sequence:

1. U1 opened at the exact Run URL and reached READY; this explicitly set the
   active pointer to U1.
2. Start New → chooser opened without changing the active pointer or creating
   a Run.
3. The Runbook was selected through StartRunPanel. The backend was paused,
   then Start exact Run was clicked through the real UI workflow.
4. StartRunPanel displayed the repaired Play-local blocked warning. The
   attempt stopped before Run UUID allocation; the active pointer remained U1.
5. The backend was restarted against the same state store. Bare `/play`
   redirected to and resumed exact U1.
6. Start New → chooser → selected committed Runbook → Start exact Run created
   corrected U3 `2487dd8f-df0f-4a4b-abd1-ae4df44dc4ad`; it reached READY before
   the active pointer changed.
7. Resolved was toggled safely on U3; the saved note
   `Corrected U1 failure then U3 continuity rehearsal note.` was saved and
   remained present after a hard reload.
8. Table → Runbook → Table was exercised on U3. Bare Play and chooser entry
   did not allocate another Run.

The active pointer remained U1 until successful U3 admission, then remained
U3 across the backend restart, reload, and chooser re-entry.

## Readability result

**PASS**

| Question | Result |
|---|---|
| Can body prose be read comfortably at 100% zoom? | PASS — 16px body text, 25.28px line height, no squinting required |
| Can control labels be read and clicked at table speed? | PASS — controls measured at 44px minimum height |
| Is current/selected state obvious? | PASS — selected/current controls use a distinct blue surface, border, and inset marker |
| Is muted/secondary text still readable? | PASS — metadata remained legible against the dark shell |
| Are headings enough to scan quickly? | PASS — Run, Scene, Beat, and focused content hierarchy was immediate |
| Does authored content have comfortable line-height/measure? | PASS — body max measure and Runbook max width are bounded |
| Does the layout avoid horizontal page scroll? | PASS at the measured normal viewport |
| Is Runbook mode equally legible? | PASS — read-only ProseMirror is 16px with 1.62 line-height and readable measure |
| Is shared AppChrome still the only chrome? | PASS — no nested Play navigation was added |
| Did styling hide a structural product problem? | NO — incomplete-Run chooser ambiguity remains visible and recorded below |
| Keyboard Tab/focus rehearsal | PASS — native Tab sequence reached Start New, Table, Runbook, Scene/Beat, Resolved, Note, and Save note; Play controls exposed a 3px `#b8d3ff` focus ring |
| Safe resolved toggle | PASS — U3 Approach changed to resolved and remained resolved after save |
| Note save/persistence | PASS — note save completed and the exact text survived reload |
| Table → Runbook → Table | PASS — both projections remained readable at the same normal viewport |
| Browser version | Recorded above: Cursor `3.16.29` / Chrome `144.0.7559.236`; native focus audit used HeadlessChrome `136.0.0.0` |

### Contrast spot checks

Values are computed browser foreground/background pairs and WCAG-style contrast
ratios from the exact candidate page:

| State | Foreground | Background | Ratio |
|---|---|---|---:|
| Authored body | `rgb(241,245,251)` | `rgb(27,32,42)` | 14.92 |
| Secondary metadata | `rgb(192,202,216)` | `rgb(18,20,26)` | 11.12 |
| Normal control | `rgb(241,245,251)` | `rgb(27,32,42)` | 14.92 |
| Current Scene control | `rgb(255,255,255)` | `rgb(45,59,84)` | 11.26 |
| Warning banner | `rgb(255,228,168)` | `rgb(58,45,31)` | 10.74 |
| Read-only Runbook body | `rgb(241,245,251)` | `rgb(27,32,42)` | 14.92 |

The native focus audit traversed AppChrome, Start New, Table, Runbook,
Scene/Beat selectors, Resolved, Note, and Save note. Each Play-local control
exposed a `3px solid` `#b8d3ff` ring with `3px` offset when focused.

## Friction found

### Presentation defects repaired in this PR

- Play inherited an unsuitable dark-shell presentation for light controls and
  authored content.
- Play-local typography was too small and secondary text was too faint.
- Controls lacked consistent table-speed sizing and focus treatment.
- The three-column surface needed a wider region and a responsive collapse
  before text became cramped.
- Read-only Runbook prose needed its own readable dark surface and measure.
- StartRunPanel blocked/incomplete/replay-needed alerts were visually plain;
  the repaired `.play-start-run > p[role="alert"]` warning treatment was
  exercised by the corrected blocked U2 flow.

### Structural/product defects deferred

- The chooser lists an incomplete Run record like a normal selectable Run and
  does not expose its missing manifest state. This is Run lifecycle/status
  policy, not a readability fix.
- The fixture had no Choice/Option material, so choice consequence behavior was
  not manufactured for this pass.
- Beat-first hierarchy, Plan→Playable fidelity, durable Combat, and
  cross-worktree persistence remain the previously recorded product/design
  work and remain false where the roadmap says they are false.

## Roadmap consequence

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
```

The live readability and same-store continuity evidence does not change the
Beat/Scene/Decision redesign, persistence sequencing, ownership, or P3B/P4
deferral. It selects the Play-local A2 readability/dogfood slice as the current
bounded implementation while keeping CR-U17 false overall.

## Recommendation

It is now safe to continue Play dogfood with readable Table and Runbook
projections and the merged A1 active-Run semantics. The chooser's treatment of
incomplete Runs, Beat-first structural redesign, Plan→Playable repair, durable
Combat, and cross-worktree authority remain explicit follow-up work.

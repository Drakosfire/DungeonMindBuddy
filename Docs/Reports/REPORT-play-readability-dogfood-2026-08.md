# Report — Play readability + active-Run dogfood

## Status

**READABILITY PASS / CONTINUITY PASS WITH RECORDED LIMITS**

The Play-local readability implementation passed the normal-viewport rehearsal
and the active-Run continuity scenarios required by Lane A2. The incomplete
U2 replacement was intentionally created through the existing Run API without
sealing its manifest; U3 was created through the normal StartRunPanel flow.
No structural Play, Run lifecycle, or chooser-status repair was made here.

## Implementation head

- Candidate implementation evidence head: `07865ee8903fc533ff3b328af3025cdf246bafda`
- Candidate UI: `apps/live-control-ui` from the A2 worktree, served at `127.0.0.1:5175`
- Changed production path: `apps/live-control-ui/src/playSurface/playSurface.css`

## Base / predecessor merge

- Base: `d4c6fb365b1e8958f6a1989a9f88fcde1b844e73` (PR #625 merge)
- Predecessor: PR #625 / Lane A1 active-Run continuity
- Backend: merged-main-equivalent A1 checkout, `127.0.0.1:8001`, same
  checkout-local Play state store; restarted once during this rehearsal
- No second backend or state migration was used

## Environment / viewport / zoom

- Browser: Chromium through Cursor IDE Browser
- OS: Linux `7.0.0-28-generic`
- Candidate viewport measured by CDP: `1220 × 945` CSS pixels
- Browser zoom: 100%
- Candidate frontend: `http://127.0.0.1:5175`
- State-owning backend: `http://127.0.0.1:8001`

## Exact Run identities U1/U2/U3

- U1: `11111111-1111-4111-8111-111111111111`
  - existing READY baseline; note and current Scene/Beat were safely exercised
- U2: `22222222-2222-4222-8222-222222222222`
  - controlled incomplete replacement; Run record created, manifest deliberately
    not sealed; manifest GET returned HTTP 404
- U3: `7ae97d9a-9dc0-46a9-bdfd-6362708785b8`
  - successful explicit replacement created through StartRunPanel and READY
  - final active Run after the rehearsal

Runbook under test: **Lane A1 Dogfood Runbook**, artifact
`77aa2879-77c7-4787-8267-b36f895235d7`, committed revision `2`.

## Before/after Run-store inventory

The inventory captured immediately before the controlled U2 attempt contained:

```text
11111111-1111-4111-8111-111111111111.json
7ae97d9a-9dc0-46a9-bdfd-6362708785b8.json
```

After U2 was created without a manifest:

```text
11111111-1111-4111-8111-111111111111.json
22222222-2222-4222-8222-222222222222.json
7ae97d9a-9dc0-46a9-bdfd-6362708785b8.json
```

The final `GET /api/live/play-active-run` returned:

```json
{
  "schema_version": "dmb_play_active_run_v1",
  "run_id": "7ae97d9a-9dc0-46a9-bdfd-6362708785b8"
}
```

No navigation, reload, chooser entry, or backend restart created a Run UUID.

## Screenshot evidence

All listed artifacts were captured from the candidate UI after commit
`07865ee8903fc533ff3b328af3025cdf246bafda`, with the shared AppChrome visible
where applicable:

1. READY Table primary scan: `a2-ready-table-u3.png`
   - local capture: `/tmp/cursor/screenshots/a2-ready-table-u3.png`
2. READY Runbook mode: `a2-runbook-u3.png`
   - local capture: `/tmp/cursor/screenshots/a2-runbook-u3.png`
3. Chooser / Start New with U2, U3, and U1 listed:
   `a2-chooser-u2-u3-u1.png`
   - local capture: `/tmp/cursor/screenshots/a2-chooser-u2-u3-u1.png`

These are the exact-head browser artifacts to attach to the PR conversation.

## Continuity result

**PASS**

Observed sequence:

1. U1 opened at the exact Run URL and reached READY.
2. Plan → Play resumed exact U1 through shared AppChrome.
3. Hard refresh and bare `/play` resumed exact U1 without chooser or Run creation.
4. A fresh browser tab at bare `/play` resumed U1 from the server-side pointer.
5. U3 was started explicitly from Start New → chooser → selected committed
   Runbook → Start exact Run. It reached READY before becoming active.
6. Plan → Play and bare `/play` resumed exact U3.
7. U2 was created as a controlled incomplete attempt without sealing a
   reference manifest. Bare `/play` bypassed U2 and resumed active U3.
8. The backend was restarted against the same state store. Bare `/play`
   resumed U3 in READY state.

The active pointer remained U1 until successful U3 admission, then remained
U3 across U2 incompleteness, backend restart, and fresh-browser re-entry.

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
| Did styling hide a structural product problem? | NO — the existing incomplete-Run chooser ambiguity remains visible and recorded below |

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

The focused Table control exposed a `3px solid` `#b8d3ff` focus ring with
`3px` offset.

## Friction found

### Presentation defects repaired in this PR

- Play inherited an unsuitable dark-shell presentation for light controls and
  authored content.
- Play-local typography was too small and secondary text was too faint.
- Controls lacked consistent table-speed sizing and focus treatment.
- The three-column surface needed a wider region and a responsive collapse
  before text became cramped.
- Read-only Runbook prose needed its own readable dark surface and measure.

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

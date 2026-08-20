# Report — C2 Session 27 native Play dogfood

## Result

NOT RUN

Phase A succeeded. First Phase B Start Run created a Run then blocked READY on P1 admission
(plain Markdown blockquotes). Artifact flattened and recommitted as revision 3. Second Start Run
reached READY. First table impression: Scene/Beat/mode controls were unreadable because Play painted
light button backgrounds over globally inherited light text. Steward authorized a one-file CSS
contrast patch so Session 27 can continue.

## Exact identities

- PR head: not yet a reviewed/merge head; working branch `agent/play-c2s27-native-dogfood`
- Runbook document ID: `8235ce04-5023-485c-92f0-2d8d81d64f50`
- Runbook revision: `3`
- Runbook SHA: `2b7f74177d340031b0148893badd46872f8d41b43499593f068b3a483a85c521`
- Failed first Run UUID (do not reuse): `d71541f1-e1d0-4a1e-8a26-60654ef6dd9b`
- Replacement Run UUID: `07225b19-7df3-4335-ae14-22e4b133eac4`
- exact `/play` route: `/play?run=07225b19-7df3-4335-ae14-22e4b133eac4`

## What was actually used

- Phase A helper dry-run / `--apply` / second `--apply` no-op
- shipped `/play` Start Run for `C2 Session 27 — Mireward Climax` (twice)
- existing Markdown writer to recommit flattened artifact (revision 2 → 3)
- native READY Table deck on Run `07225b19-7df3-4335-ae14-22e4b133eac4`

## What worked

Second Start Run allocated Run `07225b19-7df3-4335-ae14-22e4b133eac4`, sealed the manifest, and
reached READY against revision 3. Run creation/admission is no longer the blocker.

## Friction, ranked

| Severity | Moment | Cost at table | Workaround | Candidate owner |
|---|---|---|---|---|
| High | Native Table deck vs Of Conks / Hempholm prototype | GM cannot use Play as a refined table instrument; attention stays on chrome and lists instead of the next few minutes | Keep using the shipped three-column deck / Runbook toggle. Do not restore #578 HTML or redesign Play in this PR. | Play surface projection. DESIGN-play-surface-projection.md already names the Of Conks family (current Beat card, at-table / read-aloud / tools, return to the same moment). Shipped D2/D3 native Play proved exact Run+manifest identity, not that table UX. |
| High | READY Table/Runbook + Scene/Beat nav: text color on button background | GM cannot read which control is which; Play is unnavigable as a table surface | Steward authorized a one-file CSS patch: those light-background buttons now set `color: #1c1814`. | Play surface chrome vs global dark `button` / `:root` color. `.play-mode-toggle button` and `.play-nav-list button` had set cream/white `background` and inherited `#e8eaef` text. |
| High | First READY: `bound Runbook Markdown failed P1 admission` | Session cannot start | Flattened two `>` blockquotes in the artifact; recommitted. Did not patch Play. | Playable Markdown admission / authoring UX. Play UI collapsed two line-level warnings into one generic READY error. |
| Medium | First Run remains bound to rejected SHA/revision | Reloading `/play?run=d71541f1-...` will not recover | Started replacement Run `07225b19-...` | Runtime/start recovery is out of this dogfood PR |

P1 diagnostics on the rejected Markdown:

```text
line 33: Plain blockquotes are not supported yet.
line 43: Plain blockquotes are not supported yet.
```

Contrast mechanism (observed, not patched):

```text
:root { color: #e8eaef; }          /* global light text */
button { background: #232b3c; color: inherit; }
.play-mode-toggle button,
.play-nav-list button { background: #fff; }   /* no color reset */
```

Light text on white/cream Scene, Beat, and Table/Runbook buttons.

## Unexpected-player-path behavior

Not run.

## Table vs Runbook mode

READY defaults to Table. After the contrast patch, labels are readable.

The GM judgment is that this Table is still not the Of Conks table surface. Native Play shows:

```text
Scene list | Beat list | focused body + a few runtime buttons
```

plus a full-document Runbook toggle.

Of Conks / Hempholm showed a current-moment instrument: Beat as a card (at the table, read aloud,
GM note, rules now, consequences, reference chips, tool actions) with Play as a dedicated table
contract rather than Plan-with-fewer-controls. Mining report: `Docs/Reports/REPORT-pr578-play-dogfood-mining.md`.
Product design already agrees: `Docs/Design/DESIGN-play-surface-projection.md`.

This dogfood did not restore that instrument. Exact identity admission worked; table UX did not
graduate with it.

## Runtime continuity / reload

Not run. The failed first Run is not a valid continue target. Current dogfood Run is
`07225b19-7df3-4335-ae14-22e4b133eac4`.

## Authoring/setup cost

Getting accepted prep into a P1-admitted Runbook was already sharper than using Play at the table.
Ordinary GM `>` quotes are legal Markdown and illegal for native Play. The helper/manifest scan
accepted the same file because they do not share the TipTap P1 warning gate.

Once READY, chrome contrast was the next wall. After the contrast patch, the GM judgment is that
the native Table deck is not a table instrument: it is a three-column identity browser beside a
body dump, coarser than the Of Conks / Hempholm prototype.

## Decision questions

Answer from observed use, not roadmap inertia:

1. **P3B / exact graph-reference opening:** unanswered; navigation failed before references mattered.
2. **Plan → Runbook authoring:** still a real first blocker (P1 quotes). Not the only one.
3. **Playable authoring controls:** unanswered for Scene/Beat promotion; admission feedback remains a gap.
4. **Runbook storage policy:** unanswered.
5. **Combat / P4:** unanswered.
6. **Runtime ergonomics:** yes. Contrast was one symptom. The deeper finding is that native Table UX
   is an identity navigator, not the Of Conks current-moment deck.
7. **No new capability:** no. Re-anchor must weigh Play table UX (Of Conks keepers, not #578 HTML),
   chrome contrast, and P1 admission feedback. This report still does not select that slice or make
   P3B dispatchable.

## Recommendation for re-anchor

None yet. Continue Session 27 on Run `07225b19-...` with the shipped deck. Do not restore #578 or
redesign Play in this PR.

Design follow-up (not this PR's CODE successor):
`Docs/Design/DESIGN-play-native-current-moment-deck.md` (steward-accepted 2026-08-19).
Brief that requested it: `Docs/Dogfood/BRIEF-PLAY-native-table-ux-from-c2s27-dogfood.md`.

Post-dogfood re-anchor should write one implementation handoff:
`HANDOFF — make the current Beat the native Play table stage`.
Do not make P3B dispatchable from that design.

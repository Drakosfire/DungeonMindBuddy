# DEMO-READY basic presentation dogfood — provisional STOP record

**Date:** 2026-09-26
**Authority:** `HANDOFF-DEMO-READY-basic-presentation-design-pass-v1.md`
**Exact product base:** Buddy `main@f1087dcb45c805f5be6146b7b466b5280471f8c2` (#774 merged)
**Status:** Evidence gathered; product-owner decision pending
**Recommendation:** `RESUME_NON_UI`; do not dispatch a presentation implementation slice yet.

## Real-product witness

The current merged product ran against the existing local durable World and Buddy APP-STATE authorities. The existing database containers were started; no restore, migration, source publication, Runbook creation, or model call was performed. The UI and API ran from an isolated checkout on ports 5190 and 8811.

- Ingest loaded the published Campaign 2 Session 22 recap with interactive World references.
- Ingest loaded the published Campaign 1 Session 17 recap with interactive World references.
- Opened `Mireward` (Location) and `ANything` (Threat) from the C2 Session 22 prose. `Mireward` showed two related events; `ANything` was a real but content-empty Threat card triggered by the ordinary word “anything.”
- Plan opened committed `C2 Session 28 Prep — The Meat Mind` with substantive session intent and campaign-memory material.
- Build opened, but no source was selected; no Build workflow was exercised.
- Play showed **no durable Runs** and **no active Runbooks**. Its create/edit/start controls were disabled. The read-only local play-readiness check independently reported zero active startable Runbooks and `PLAY READINESS: NOT READY`.
- After selecting C1 Session 17 and navigating Ingest → Plan → Play → Ingest, Ingest returned to C2 Session 22, rather than the selected C1 Session 17. This is observed context loss; the mechanism has not been diagnosed.

The D0 path could not reach a playable current moment or complete a meaningful Build-to-Play pass. No fixture was substituted for that missing capability.

## Stage 4 and Stage 5 observations

Stage 4 is **partial, not passed**. Both recaps are readable and richly projected. However, the World-reference layer links ordinary prose as objects: C2 Session 22 exposes `anything` as a Threat, and C1 Session 17 links words including `water` and `floor`. This affects whether the product appears to remember campaign meaning; presentation work alone cannot establish that these are truthful references. `Mireward` is inspectable, but its sparse card does not yet create a compelling memory moment. A visual hierarchy critique is premature while the reference set itself is suspect.

Stage 5 is **partial, not passed**. The top-level links reached Plan, Play, Build, and Ingest without an observed document-reload failure. The selected Ingest campaign/session did not survive the round trip. More importantly, Play has no active Runbook or Run, preventing the planned demo flow. No claim about Play current-moment presentation is possible.

## First visible-defect ledger

| Defect | Path | Basic-demo severity | Primarily presentation? | Disposition |
|---|---|---|---|---|
| No active Runbook or durable Run; Plan's committed Session 28 prep cannot reach Play | Plan → Play | High | No — product state/workflow readiness | `NON_UI` |
| Ordinary recap word “anything” opens a real, empty `ANything` Threat; generic words are linked in C1 too | C2 S22 / C1 S17 Ingest | High | No — reference/graph semantic quality | `NON_UI` |
| C1 Session 17 selection returns as C2 Session 22 after surface navigation | Ingest → Plan → Play → Ingest | Medium/high | No — navigation/context correctness | `NON_UI` / diagnose |
| `Mireward` object is sparse and duplicate close affordances appear in the secondary panel | C2 S22 object Peek | Medium | Yes, partly | `HOLD` behind the above |

The initial UI candidates (`ObjectSheet` adoption, recap/Peek composition, shell balance, Play hierarchy, Build first impression) were **not retained for prototype**. The first serious blocker is not primarily composition, and Play's missing live path would make a Ladle comparison misleading. No static story, baseline, production component, UI dependency, Canvas work, spatial work, or theme system was changed.

## Product-owner STOP

**Recommended disposition:** `RESUME_NON_UI` before choosing a presentation successor. This is a recommendation, not a recorded product-owner approval.

The narrow next questions are: what exact current Runbook/Run should make C2 Session 28 playable, why the current durable APP-STATE exposes none, whether false-positive World references are extraction data or linking logic, and why the selected Ingest context was lost on return. Resolve or explicitly waive those demo-path blockers, then re-run D0 before selecting one visual candidate. UI-F5 Canvas, UI-F6, spatial work, and theme packs remain deferred.

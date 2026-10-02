# DEMO-READY basic-presentation design pass — D0 checkpoint

**Status:** INCOMPLETE — D0 blocked; no successor selected
**Buddy main:** `4466c77ad9db716aaa266d672e8faa860255f3b0`
**Design authority:** `Docs/Plans/HANDOFF-DEMO-READY-basic-presentation-design-pass-v1.md`
**Checkpoint date:** 2026-10-02

## D0 — Required real C1/C2 path

The active handoff requires: open C1/C2 → choose a prior session → read its recap → inspect two World references/objects → navigate Ingest → Plan → Build → Play → return to the original recap/session.

That real path was unavailable in the current in-app browser surfaces:

- Tab 1 at `http://127.0.0.1:5178/play` displayed “This site can't be reached.”
- Tab 5 at `http://127.0.0.1:5202/plan?world=demo-j2-plan-apply-witness-2026-10-01&documentId=46e2e8fe-6d91-4552-be31-e69c818e77c6` displayed “World selection unavailable” and “workspace document not found: 46e2e8fe-6d91-4552-be31-e69c818e77c6.”

The second tab is not C1/C2. The roadmap at this main pin identifies that exact World and Plan as the synthetic J2 Apply witness. It records that the original APP-STATE environment was auto-removed, the witness was reconstituted in an isolated database, and its API/UI processes and PostgreSQL container were stopped afterward. Its current unavailable-World/document message is consistent with that teardown; it is not evidence of a source regression or a new J2 visual defect.

A read-only `rtk ss -ltnp` listener check returned `Cannot open netlink socket: Operation not permitted`. This report does not claim no local service exists; it records only the visible browser state and the denied listener inspection.

## Work not performed

Because D0 could not run against real C1/C2 material, D1 Stage 4 reading, D2 Stage 5 navigation, D3 defect ledger, D4 candidate selection, D5 UI-lab prototypes, and D6 real-product comparison remain unperformed. No static fixture was substituted; no visual successor was selected. No product code, service, database, provider, or persistent product state was accessed or changed.

## Gate

Resume D0 only with a designated read-only C1/C2 app/API and corpus/session pin, plus its runtime owner and port/service/database boundaries. PRIME has been asked for that exact assignment. No service was started or target changed.

After D0 is available, complete D0–D6 in order, then request the D7 product-owner decision: `ACCEPT_ONE`, `RECONNAISSANCE`, `RESUME_NON_UI`, or `HOLD`. The basic-presentation decision STOP remains active. This is an incomplete checkpoint, not an implementation authorization or J2/J1–J6 acceptance.

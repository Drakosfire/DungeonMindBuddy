# Guest citation previews

Status: ACTIVE. Authorized by the Sizzek demo delivery goal and the observed signed-out experience on 2026-11-23. Base: Buddy main 843e1ddf35b774310697bd194d76c5d58c552f24; independent serial serving integration follows main merge and the current serving branch.

Outcome: replace anonymous numbered guest citation controls with short, readable previews of the exact released excerpt so visitors can choose a source with context. Keep evidence-role labeling, release-local navigation, guest isolation, and the stable published manifest unchanged.

Write scope: this handoff and GuestReleasePage.tsx, GuestReleasePage.test.tsx, guestReleasePage.css under apps/live-control-ui/src/guestRelease. No API, release publication, data, model, or auth changes. Do not infer source titles or claim context proves a statement. Fallback safely when an excerpt is missing or blank.

Validation: exercise source and context controls, released excerpt navigation and long/unusual text in focused UI tests; run exact-head hosted frontend and compare full discovered failure identities with current baseline; inspect desktop/mobile rendering. Independent Bugbot review and user-authorized merge, followed by a serial serving PR based on the then-current serving head; deploy only after integration checks.

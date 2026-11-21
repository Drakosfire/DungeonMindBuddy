# RETRIEVAL · Render a retained benchmark waterfall

Status ACTIVE. Serial benchmark-only slice after #4265, on Buddy main f126b6a5a.
Branch codex/buddy-benchmark-trace-report in its isolated checkout. The write set
is the benchmark workflow and report module, existing workflow tests, the lab
guide, and this handoff. Runtime authority, packet composition and providers
are outside the change.

Keep report generation local, provider-free and keyed by case ID. Validate the
retained request, evidence receipt and trace identity before accounting for
elapsed time. Do not render captured content. Run the existing workflow tests
and exercise the CLI on the retained exact browser and host-only captures.
Independent review precedes merge.

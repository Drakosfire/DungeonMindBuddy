# Trace crawler tab

ACTIVE: user requested saved suggestions stop appearing on every Trace tab and the graph crawler have its own tab. Serial single PR, branch `codex/trace-crawler-tab` based on `origin/main` at `099b13eab45c256ca57949c6ebfc3943b44fe3ec`; no open Trace PRs were found.

Scope: conversation reply Trace tab integration, graph replay presentation, corresponding focused UI tests, this brief. Saved suggestion review remains available in Evidence. Preserve replay state and pause playback when another tab is active; show an honest empty state when no replay was recorded. Do not change evidence, storage, schema, or provider calls.

Verify saved suggestion isolation, keyboard tab navigation, crawler replay and no-replay cases, recorded activity, and historical conversations. Qualify exact head under the repo frontend verification standard, review independently, then deploy per the user-authorized Actions procedure.

# AGENT — Replay node details popup

Status: ACTIVE under the browser comment requesting an out-of-flow popup.
One serial UI PR based on Buddy main `a705bb4bf` in the graph timeline
checkout on `codex/buddy-replay-node-popup`.

Scope is the replay component, dialog styles, and focused tests. Use the
browser dialog top layer within the existing Buddy interface. Opening pauses
playback. Escape and the close control dismiss it. Node inspection uses
existing saved replay data. Verify readable visit buttons, no layout shift,
focus return, and the exact cumulative frontend diff.

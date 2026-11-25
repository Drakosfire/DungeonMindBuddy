#!/usr/bin/env bash
# A selected release must actually include both the UI build switch and hosted route.
set -euo pipefail
root=${1:?expected source root}
build=${2:-0}
plan=${3:-0}
play=${4:-0}
media=${5:-0}
buddy=${6:-0}
[[ "$build" == 0 || "$build" == 1 ]] || { printf '%s\n' 'Invalid guest Build flag.' >&2; exit 1; }
[[ "$plan" == 0 || "$plan" == 1 ]] && [[ "$plan" == 0 || "$build" == 1 ]] || { printf '%s\n' 'Invalid guest Plan flag.' >&2; exit 1; }
[[ "$play" == 0 || ( "$play" == 1 && "$plan" == 1 ) ]] || { printf '%s\n' 'Invalid guest Play flag.' >&2; exit 1; }
[[ "$media" == 0 || ( "$media" == 1 && "$build" == 1 ) ]] || { printf '%s\n' 'Invalid guest media flag.' >&2; exit 1; }
[[ "$buddy" == 0 || ( "$buddy" == 1 && "$play" == 1 && "$media" == 1 ) ]] || { printf '%s\n' 'Invalid guest Buddy flag.' >&2; exit 1; }
fail() { printf '%s\n' 'Selected revision does not support the hosted guest Graph.' >&2; exit 1; }
grep -Fxq 'ARG VITE_HOSTED_GUEST_GRAPH=0' "$root/Dockerfile.production" || fail
grep -Fq 'VITE_HOSTED_GUEST_GRAPH' "$root/apps/live-control-ui/src/App.tsx" || fail
grep -Fq 'DMB_HOSTED_GUEST_GRAPH_ENABLED' "$root/src/application_state/index_graph/sessions.py" || fail
grep -Fq 'DMB_HOSTED_GUEST_GRAPH_ENABLED' "$root/apps/live_control_server/services/hosted_auth.py" || fail

if [[ "$build" == 1 ]]; then
  grep -Fxq 'ARG VITE_HOSTED_GUEST_BUILD=0' "$root/Dockerfile.production" || fail
  grep -Fq 'VITE_HOSTED_GUEST_BUILD' "$root/apps/live-control-ui/src/App.tsx" || fail
  grep -Fq 'DMB_HOSTED_GUEST_BUILD_ENABLED' "$root/src/application_state/index_graph/sessions.py" || fail
  grep -Fq 'admit_guest_build_request' "$root/apps/live_control_server/services/hosted_auth.py" || fail
  test -f "$root/apps/live_control_server/services/guest_build_access.py" || fail
fi
if [[ "$plan" == 1 ]]; then
  grep -Fxq 'ARG VITE_HOSTED_GUEST_PLAN=0' "$root/Dockerfile.production" || fail
  grep -Fq 'VITE_HOSTED_GUEST_PLAN' "$root/apps/live-control-ui/src/App.tsx" || fail
  grep -Fq 'DMB_HOSTED_GUEST_PLAN_ENABLED' "$root/apps/live_control_server/services/guest_build_access.py" || fail
fi

if [[ "$play" == 1 ]]; then
  grep -Fxq 'ARG VITE_HOSTED_GUEST_PLAY=0' "$root/Dockerfile.production" || fail
  grep -Fq 'VITE_HOSTED_GUEST_PLAY' "$root/apps/live-control-ui/src/App.tsx" || fail
  grep -Fq 'DMB_HOSTED_GUEST_PLAY_ENABLED' "$root/apps/live_control_server/services/guest_build_access.py" || fail
fi
if [[ "$media" == 1 ]]; then
  grep -Fxq 'ARG VITE_HOSTED_GUEST_MEDIA=0' "$root/Dockerfile.production" || fail
  grep -Fq 'VITE_HOSTED_GUEST_MEDIA' "$root/apps/live-control-ui/src/guestWorld/guestBuildSession.ts" || fail
  grep -Fq 'DMB_HOSTED_GUEST_MEDIA_ENABLED' "$root/apps/live_control_server/services/guest_build_access.py" || fail
fi

if [[ "$buddy" == 1 ]]; then
  grep -Fxq 'ARG VITE_HOSTED_GUEST_BUDDY=0' "$root/Dockerfile.production" || fail
  grep -Fxq 'ARG VITE_HOSTED_GUEST_BUILD_BUDDY=0' "$root/Dockerfile.production" || fail
  grep -Fq 'VITE_HOSTED_GUEST_BUILD_BUDDY' "$root/apps/live-control-ui/src/LocalWorkspace.tsx" || fail
  grep -Fq 'DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED' "$root/apps/live_control_server/services/guest_build_access.py" || fail
fi

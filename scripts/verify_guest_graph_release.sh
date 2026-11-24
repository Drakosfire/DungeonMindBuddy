#!/usr/bin/env bash
# A selected release must actually include both the UI build switch and hosted route.
set -euo pipefail
root=${1:?expected source root}
build=${2:-0}
[[ "$build" == 0 || "$build" == 1 ]] || { printf '%s\n' 'Invalid guest Build flag.' >&2; exit 1; }
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

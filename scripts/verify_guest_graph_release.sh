#!/usr/bin/env bash
# A selected release must actually include both the UI build switch and hosted route.
set -euo pipefail
root=${1:?expected source root}
fail() { printf '%s\n' 'Selected revision does not support the hosted guest Graph.' >&2; exit 1; }
grep -Fxq 'ARG VITE_HOSTED_GUEST_GRAPH=0' "$root/Dockerfile.production" || fail
grep -Fq 'VITE_HOSTED_GUEST_GRAPH' "$root/apps/live-control-ui/src/App.tsx" || fail
grep -Fq 'DMB_HOSTED_GUEST_GRAPH_ENABLED' "$root/src/application_state/index_graph/sessions.py" || fail
grep -Fq 'DMB_HOSTED_GUEST_GRAPH_ENABLED' "$root/apps/live_control_server/services/hosted_auth.py" || fail

#!/usr/bin/env bash
# Read-only local host inventory for the DungeonMindBuddy hosting review.
# Run on the target host only after the operator chooses to do so. This script
# does not use sudo, contact remote hosts, inspect service environments,
# read application data, open database connections, or print credentials.

set -uo pipefail

section() {
  printf '\n## %s\n' "$1"
}

show_command() {
  local label="$1"
  shift
  if command -v "$1" >/dev/null 2>&1; then
    printf '%s: ' "$label"
    "$@" 2>&1 || printf '[unavailable]\n'
  else
    printf '%s: [not installed]\n' "$label"
  fi
}

section 'Collection boundary'
printf '%s\n' 'Read-only local metadata only; no remote network requests are made.'
printf '%s\n' 'Output may include IP addresses, service/container names, image tags, and mount names or paths.'
printf '%s\n' 'The operator must review and redact the output before sharing it.'
printf '%s\n' 'Do not add environment dumps, service config files, logs, DB URLs, cookies, or secret values.'
printf 'Collected at (UTC): '
date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || printf '[unavailable]\n'

section 'Host and capacity'
show_command 'Kernel' uname -srmo
if [[ -r /etc/os-release ]]; then
  awk -F= '$1 == "PRETTY_NAME" {gsub(/^"|"$/, "", $2); print "OS: " $2; exit}' /etc/os-release
fi
show_command 'CPU count' nproc
show_command 'Memory' free -h
show_command 'Load' uptime

section 'Installed runtimes'
show_command 'Python' python3 --version
show_command 'Node' node --version
show_command 'Docker client' docker --version

section 'Listening TCP sockets'
if command -v ss >/dev/null 2>&1; then
  ss -ltnH 2>/dev/null | awk '{print $4}' | sort -u || printf '[unavailable]\n'
else
  printf '%s\n' '[ss not installed]'
fi

section 'Running system services'
if command -v systemctl >/dev/null 2>&1; then
  systemctl list-units --type=service --state=running --no-legend --plain 2>/dev/null \
    | awk '{print $1}' | sort || printf '[unavailable]\n'
else
  printf '%s\n' '[systemctl not installed]'
fi

section 'Container inventory (local Docker context only)'
if command -v docker >/dev/null 2>&1 \
  && [[ -z "${DOCKER_HOST:-}" && -z "${DOCKER_CONTEXT:-}" ]]; then
  docker_endpoint="$(docker context inspect --format '{{.Endpoints.docker.Host}}' default 2>/dev/null || true)"
  case "$docker_endpoint" in
    unix://*)
      docker --context default ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' 2>/dev/null \
        || printf '[Docker query unavailable]\n'
      ;;
    *)
      printf '%s\n' '[skipped: default Docker endpoint is not a local Unix socket]'
      ;;
  esac
else
  printf '%s\n' '[skipped: Docker is absent or a remote Docker endpoint is configured]'
fi

section 'Filesystem capacity'
if command -v df >/dev/null 2>&1; then
  df -hT -x tmpfs -x devtmpfs 2>/dev/null \
    | awk 'NR == 1 {print "TYPE SIZE USED AVAIL USE% MOUNT"; next} {print $2, $3, $4, $5, $6, $7}' \
    || printf '[unavailable]\n'
else
  printf '%s\n' '[df not installed]'
fi

section 'Operator-supplied facts (not read by this script)'
cat <<'EOF'
Report only redacted identifiers or yes/no facts:
- Exact Buddy, DungeonMindServer, DungeonMind, and LandingPage release/image pins.
- Which process serves Buddy and its private API bind address/port.
- Whether the two logical Postgres authorities are distinct (Buddy application state and DungeonMind WorldGraph).
- Whether media, artifacts, recaps, session state, and each DB backup reside outside replaceable containers/checkouts.
- Latest verified backup and restore-rehearsal dates, migration heads, and available capacity.
- Reverse-proxy stream buffering/read-timeout behavior and the SPA/API route split.

Redact internal hostnames, mount paths, account names, World names, and any value that could identify a user or campaign before sharing.
EOF

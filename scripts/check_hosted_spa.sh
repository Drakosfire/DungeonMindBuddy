#!/usr/bin/env bash
set -euo pipefail

origin=${1:?Pass the Buddy origin without a trailing slash}

for path in / /graph; do
  html=$(curl -fsS -H 'Accept: text/html' "$origin$path")
  if [[ "$html" != *'<title>DungeonMind — Live Control</title>'* ]]; then
    printf 'Buddy shell marker missing at %s\n' "$path" >&2
    exit 1
  fi
  asset=$(sed -nE 's/.*<script[^>]*src="(\/assets\/[A-Za-z0-9_.-]+\.js)".*/\1/p' <<< "$html")
  asset=${asset%%$'\n'*}
  if [[ -z "$asset" ]]; then
    printf 'Built JavaScript entry missing at %s\n' "$path" >&2
    exit 1
  fi
  result=$(curl -fsS -o /dev/null -w '%{http_code} %{content_type}' "$origin$asset")
  case "$result" in
    '200 text/javascript'|'200 text/javascript;'*|'200 application/javascript'|'200 application/javascript;'*)
      printf 'Verified %s and %s\n' "$path" "$asset"
      ;;
    *)
      printf 'Unexpected JavaScript asset response for %s: %s\n' "$asset" "$result" >&2
      exit 1
      ;;
  esac
done

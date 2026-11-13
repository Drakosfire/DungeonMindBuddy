#!/usr/bin/env bash
set -euo pipefail

origin=${1:?Pass the Buddy origin without a trailing slash}

html_file=$(mktemp)
trap 'rm -f -- "$html_file"' EXIT

for path in / /graph; do
  result=$(curl --connect-timeout 5 --max-time 15 -fsS -H 'Accept: text/html' -o "$html_file" -w '%{http_code} %{content_type}' "$origin$path")
  case "$result" in
    '200 text/html'|'200 text/html;'*) ;;
    *) printf 'Unexpected Buddy shell response at %s: %s\n' "$path" "$result" >&2; exit 1 ;;
  esac
  html=$(<"$html_file")
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
  result=$(curl --connect-timeout 5 --max-time 15 -fsS -o /dev/null -w '%{http_code} %{content_type}' "$origin$asset")
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

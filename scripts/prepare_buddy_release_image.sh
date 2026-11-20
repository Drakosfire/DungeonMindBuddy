#!/usr/bin/env bash
# Print the exact image ID for a clean, pinned Buddy release checkout.
set -euo pipefail

revision=${1:-}
if [[ ! "$revision" =~ ^[0-9a-f]{40}$ ]] || [[ $# != 1 ]]; then
  printf '%s\n' 'Supply the full approved Buddy release SHA.' >&2
  exit 2
fi
checkout=$(git rev-parse HEAD)
changes=$(git status --porcelain)
if [[ "$checkout" != "$revision" || -n "$changes" ]]; then
  printf '%s\n' 'Use a clean checkout at the approved Buddy release SHA.' >&2
  exit 1
fi

tag="dungeonmindbuddy:$revision"
existing=$(docker image ls --filter "reference=$tag" --format '{{.Repository}}:{{.Tag}}')
if [[ -z "$existing" ]]; then
  docker build --target api -f Dockerfile.production --label "org.opencontainers.image.revision=$revision" -t "$tag" . >&2
elif [[ "$existing" != "$tag" ]]; then
  printf '%s\n' 'Docker returned unexpected release tags.' >&2
  exit 1
fi

image=$(docker image inspect --format '{{.Id}}' "$tag")
label=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image")
if [[ ! "$image" =~ ^sha256:[0-9a-f]{64}$ || "$label" != "$revision" ]]; then
  printf '%s\n' 'Image revision does not match the approved release. Resolve the tag conflict before deployment.' >&2
  exit 1
fi
printf '%s\n' "$image"

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

review=${VITE_GUEST_RELEASE_REVIEW:-0}
page=${VITE_GUEST_RELEASE_PAGE:-0}
public_id=${VITE_GUEST_HOME_PUBLIC_ID:-}
if [[ ! "$review" =~ ^[01]$ || ! "$page" =~ ^[01]$ ]] || \
   [[ -n "$public_id" && ! "$public_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || \
   [[ -n "$public_id" && "$page" != 1 ]]; then
  printf '%s\n' 'Guest build flags must be 0 or 1; the optional public ID must be a canonical UUID and requires the guest page.' >&2
  exit 2
fi

config="review=$review;page=$page;home=$public_id"
tag="dungeonmindbuddy:$revision"
if [[ "$review" != 0 || "$page" != 0 || -n "$public_id" ]]; then
  config_hash=$(printf '%s' "$config" | sha256sum | cut -c1-16)
  tag="$tag-guest-$config_hash"
fi
existing=$(docker image ls --filter "reference=$tag" --format '{{.Repository}}:{{.Tag}}')
if [[ -z "$existing" ]]; then
  docker build --target api -f Dockerfile.production \
    --build-arg "VITE_GUEST_RELEASE_REVIEW=$review" \
    --build-arg "VITE_GUEST_RELEASE_PAGE=$page" \
    --build-arg "VITE_GUEST_HOME_PUBLIC_ID=$public_id" \
    --label "org.opencontainers.image.revision=$revision" \
    --label "org.dungeonmindbuddy.guest-build=$config" -t "$tag" . >&2
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
image_config=$(docker image inspect --format '{{index .Config.Labels "org.dungeonmindbuddy.guest-build"}}' "$image")
if [[ "$image_config" != "$config" ]]; then
  printf '%s\n' 'Image guest build configuration does not match the requested settings.' >&2
  exit 1
fi
printf '%s\n' "$image"

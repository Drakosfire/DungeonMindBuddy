# ONBOARD: preserve guest switches in production Compose

Status: ACTIVE under the owner's Sizzek goal and explicit merge/deployment authority.
Serial product slice based on `41dc7a097`, branch `codex/onboard-guest-compose-switches`.
Write lease: this handoff, `deploy/production/compose.production.yaml`, and
`Docs/Runbooks/RUNBOOK-buddy-production-deployment.md`. No live host, database,
World, port, or public release is leased by this source slice. The concurrent
serving work was checked for overlap with these paths.

Outcome: allow the standard production Compose package to pass all three guest
release switches from its protected environment file, defaulting each to off.
The live service previously lost the switches on recreation, returning 401 for
the public manifest. A reviewed same-image restart restored them. This change
does not itself update the host's custom Compose layers or establish that a
future deployment will consume this package. Verify actual Compose interpolation
for absent, explicitly enabled, and independently configured values; review the
cumulative diff and obtain independent review. Coordinate any subsequent live
configuration change with the owner of that deployment path.

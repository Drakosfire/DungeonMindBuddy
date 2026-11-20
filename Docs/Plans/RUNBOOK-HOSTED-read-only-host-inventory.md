# Read-only host inventory runbook

Run this on the intended host only after the operator selects it. This task did not run the inventory or contact a host.

## Run

From a reviewed Buddy checkout, run:

    bash scripts/host_inventory.sh

No sudo is used. The script reads local OS and capacity metadata, listening TCP addresses, running service unit names, filesystem capacity, and optionally the default local Docker context. It does not make remote network calls, inspect process environments or service configuration, open database connections, read application data, or print credentials.

## Review output before sharing

Output can include IP addresses, service and container names, image tags, ports, filesystem mount names or paths, and host details. An operator must inspect and redact it before sharing. Do not return environment dumps, .env files, service configuration, logs, database URLs, cookies, provider credentials, SSH material, private keys, campaign text, or unredacted internal hostnames.

Return only redacted facts:

- Date/time, OS, CPU/memory, listening-address summary, running service-unit summary, and approximate free capacity.
- Exact Buddy, DungeonMindServer, DungeonMind, and LandingPage release or immutable image pins.
- Whether Buddy and DMS bind privately, the public SPA route, and the private API upstream.
- Whether proxy buffering is disabled and streaming read timeouts are suitable.
- Whether Buddy application-state PostgreSQL and DungeonMind WorldGraph are distinct logical authorities with separate owners, migrations, backups, and restore evidence.
- Labels and outside-checkout/container status for managed World data, media, artifacts, recaps, session roots, and DB backups. Redact actual paths if needed.
- Migration heads, latest verified backup date, and last isolated restore-rehearsal date.

## Later staging prerequisites

This inventory is planning evidence only. A separate reviewed procedure must name the selected World, exact code and image pins, durable mount points, both database migration states, backup and isolated-restore evidence, proxy routing, health/readiness checks, account cohort, provider/capacity limits, and rollback or forward-repair owner. Do not apply migrations, change services, DNS, TLS, credentials, firewall or proxy settings, storage, or deployed data as part of this inventory.

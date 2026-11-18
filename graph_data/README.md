# Historical contribution-bundle recovery

The C1 and C2 bootstrap bundle copies have been retired from this checkout.
Admitted recap span reads resolve digest-bound database source bodies;
historical `graph-data://` provenance does not authorize opening checkout files.
Fixtures and their embedded provenance remain intact.

## Recover the last checkout bytes

The recovery pin is Buddy `7014b5de30e32b306893f4bc6315a086d34d4c18`:

- [C1 copy](https://github.com/Drakosfire/DungeonMindBuddy/tree/7014b5de30e32b306893f4bc6315a086d34d4c18/graph_data/approved_contribution_bundles/eldyrwild-longmont-c1-s1-s3-v1)
- [C2 copy](https://github.com/Drakosfire/DungeonMindBuddy/tree/7014b5de30e32b306893f4bc6315a086d34d4c18/graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1)

[Checksums](historical-contribution-bundles.sha256) identify all 13 files,
134,277 bytes in total. These bytes differ from the older validation versions
below. Recovery proves byte identity, not validation or permission to publish.

From the repository root, recover into a new directory on the approved local
Projects filesystem. Other executors must follow their explicitly authorized
storage policy; see [agent policy](../AGENTS.md#local-verification-standard-and-hosted-pause).
The command neither switches this checkout nor overwrites a bundle directory.
It removes its own incomplete output if retrieval or verification fails.

```bash
(
set -euo pipefail
pin=7014b5de30e32b306893f4bc6315a086d34d4c18
checksums="$PWD/graph_data/historical-contribution-bundles.sha256"
test -f "$checksums"
git cat-file -e "$pin^{commit}" 2>/dev/null || git fetch --no-tags origin "$pin"
test "$(findmnt -no UUID -T "$HOME/Projects/.codex" | tr -d '[:space:]')" = \
  48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8
recovered=$(mktemp -d "$HOME/Projects/.codex/buddy-c1c2-recovery.XXXXXX")
complete=false
trap 'if [[ "$complete" != true ]]; then rm -rf -- "$recovered"; fi' EXIT
git archive "$pin" graph_data/approved_contribution_bundles |
  tar -xf - -C "$recovered"
(cd "$recovered" && sha256sum -c "$checksums")
complete=true
printf 'Recovered files: %s\n' "$recovered"
)
```

Keep recovered copies outside the runtime checkout. Delete the task directory
when the historical investigation is finished.

## Historical validation contracts

Use a separate isolated checkout at the exact historical revision and its locked
environment. The recorded results below apply only to that revision's payloads;
they do not validate the recovery pin's different bytes.

| Contract | Historical Buddy pin | Procedure and recorded result |
| --- | --- | --- |
| C1 additive apply | `eb29b3397859be87c655d0e07bc3bf9df53f98fc` | The [dedicated C1 loader](https://github.com/Drakosfire/DungeonMindBuddy/blob/eb29b3397859be87c655d0e07bc3bf9df53f98fc/apps/live_control_server/services/c1_world_graph_additive_apply.py) hashes the ordered contribution files. Replay with `uv run --frozen python -m pytest tests/test_c1_world_graph_additive_apply.py -q`; the historical investigation passed five tests using disposable Worlds. |
| C2 initial bundle | `835c781b09d261708ed13308884c4ed269d228cd` | The [generic validator](https://github.com/Drakosfire/DungeonMindBuddy/blob/835c781b09d261708ed13308884c4ed269d228cd/scripts/validate_graph_contribution_bundle.py) hashes canonical manifest JSON excluding its digest field. Replay with `uv run --frozen python scripts/validate_graph_contribution_bundle.py --bundle graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1 --report-json "${VALIDATION_REPORT:?Set to an owned scratch report path}"`. The historical investigation returned exit 0 and `ok=true`; the four bootstrap CLI tests also passed. |

The generic validator rejected C1 at its original pin because the two formats
use different digest definitions. That mismatch does not invalidate the dedicated
C1 proof. At the later C1 pin the generic C2 validator also reported stale
contribution IDs; preserve these distinctions rather than changing sealed bytes
to obtain a passing result. The obsolete standalone validator is retired on
current main. [#3544](https://github.com/Drakosfire/DungeonMindBuddy/issues/3544)
retains the historical investigation and evidence limits.

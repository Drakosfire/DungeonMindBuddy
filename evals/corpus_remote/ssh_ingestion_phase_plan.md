# Deferred SSH Corpus Ingestion Phase

## Goal

Prepare a reproducible remote-corpus ingestion phase for benchmark expansion without blocking milestone-1 local correctness.

## Required Inputs

- SSH host, port, and authentication method for the desktop GPU server.
- Absolute remote corpus root path.
- Campaign grouping rules for remote documents.

## Run the snapshot wrapper

In the checkout's existing `.env.ssh`, configure `SSH_HOST`, `SSH_ALIAS`
(the SSH username), `CORPUS_SOURCE_HOST` (the label recorded in the snapshot),
and `CORPUS_REMOTE_ROOT` (the absolute path on the remote host). Run
`bash scripts/run_remote_snapshot_from_env.sh` from the repository root.
An optional first argument overrides the remote root. An optional second
argument sets the sample size, which defaults to 40.

For password authentication, set `CORPUS_SSH_PASSWORD` in the operator
environment or `.env.ssh`. The wrapper also accepts the legacy
`SSH_PRIVATE_KEY` variable as a password input. The Python process receives
the password in its environment. Verify the first live invocation against
the approved source host and check the generated inventory's source label
and sampled paths before using it in a benchmark.

## Required Output Artifacts

- `out/evals/corpus_remote/remote_inventory.json`
- `out/evals/corpus_remote/normalization_manifest.json`
- `out/evals/corpus_remote/reproducibility_report.json`

## Remote Inventory Contract

`remote_inventory.json` must contain:

- `snapshot_id`: stable snapshot identifier (timestamp + hash of remote file listing)
- `source_host`: host alias used for SSH
- `captured_at`: UTC timestamp
- `totals`: counts by extension and total bytes
- `documents`: list of sampled files with path, size, modified time

## Normalization Manifest Contract

Every sampled text document must include:

- `document_id`
- `remote_path`
- `source_class`
- `canon_layer`
- `campaign_id` (nullable; required when `canon_layer=campaign`)
- `campaign_group`

## Hard Gates for SSH Phase

- Fail if any sampled document is missing any manifest field.
- Fail if two runs against same `snapshot_id` produce different projection hashes.
- Fail if inventory and manifest sample sets diverge.


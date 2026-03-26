# Deferred SSH Corpus Ingestion Phase

## Goal

Prepare a reproducible remote-corpus ingestion phase for benchmark expansion without blocking milestone-1 local correctness.

## Required Inputs

- SSH host, port, and authentication method for the desktop GPU server.
- Absolute remote corpus root path.
- Campaign grouping rules for remote documents.

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


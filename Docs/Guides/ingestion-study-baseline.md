# Freeze ingestion study evidence

Use the existing evaluator CLI, without provider or database configuration:

```bash
PYTHONPATH=src python scripts/evaluate_ingestion.py baseline-freeze \
  --manifest /absolute/path/baseline-inventory.json \
  --baseline-output /absolute/path/new-private-directory
PYTHONPATH=src python scripts/evaluate_ingestion.py baseline-verify \
  --baseline-output /absolute/path/new-private-directory
```

The inventory schema is `dmb_ingestion_baseline_v1`, with `baseline_id` and
`categories`. Required category names are defined in
`ingestion_evaluation.baseline.CATEGORIES`. Each category is either:

```json
{"status": "retained", "artifacts": [{"path": "/absolute/file", "sha256": "exact SHA256"}], "limitations": []}
```

or `{"status": "unknown", "reason": "Specific missing evidence"}`.
Retained categories may also name limitations; retaining a partial measurement
does not make it complete. Keep raw, reviewed and publication assessments separate
in supplied score artifacts. Include actual runtime contents, rendered prompts,
effective settings, original/effective inputs, graph context and Gold bytes in
the inventory, not only pointers to mutable locations. Nested manifests are
ordinary artifacts: their referenced files must also be inventoried explicitly.
The tool cannot infer that a claimed category is substantively complete.

Freeze validates every pin, creates a private directory exclusively, deduplicates
copied bytes by hash, and writes completion only after retention. Verify needs no
original paths. A failed partial directory is evidence of failure, not a baseline;
inspect it and choose a new output rather than overwriting it. Completion and
receipt hashes detect accidental changes; they are not a cryptographic signature
or protection against an operator rewriting the entire archive. Pin the returned
receipt hash in the consuming experiment contract.

Historical capture manifests retain their original tooling identity. These offline
commands do not relax capture qualification, dispatch inference, or award quality
scores. Do not include credentials in an inventory. Preserve historical failures,
negative experiments and unknowns; do not re-execute them merely to fill a table.

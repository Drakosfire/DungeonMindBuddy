# Temporal shadow holdout cohort V15 (TL01G)

**ACTIVE — fresh TL01G certification cohort (provider-unobserved).**

This holdout/adversarial pair is authored for pre-live certification only. No provider
call, calibration artifact, or promotion matrix has been executed against these bytes.

**Certification SHA:** `0ea6c2a9ae127c348ac93ce302c2cc698926bcea`  
**Prior certifications invalidated:** `e59dd742…` (review cycle 1); `09da5f76…` (review cycle 2)  
**Certification report:** `Docs/Reports/REPORT-tl01g-v15-adv13-cohort-certification.md`  
**Disposition:** `CERTIFIED_FOR_EXECUTION` (asset certification only — not prompt readiness)

### What `sources/` means here

`sources/*.md` contains synthetic evaluation stimulus documents. Each file
supplies the exact owned evidence for one or more assertions in this cohort.

These files exist to support:

* deterministic evaluation inputs;
* evidence IDs, hashes, and line-range verification;
* comparison of model output against sealed gold;
* human debugging and retained regression evidence.

They are not:

* canonical campaign prose under `corpus/`;
* inputs to production World Supergraph ingestion;
* durable graph assertions or graph revisions;
* runtime application content;
* ChatGPT Project Sources.

Fixture flow:

```text
sources/*.md
  controlled evidence inputs
        ↓
base-contribution.json
  assertions being temporally evaluated
        ↓
temporal-case-tl01f.json / temporal-case-tl01g.json
  executable control and candidate cases
        ↓
gold-overlay.json + GOLD-AUDIT.md
  expected interpretation and human justification
        ↓
aggregate.json
  observed evaluation result (successor execution PR only)
```

## Seal protocol

* Provider-unobserved: this PR must not execute live model calls.
* Gold and fixture bytes are sealed at certification SHA once §7 proofs pass.
* No post-observation gold edits without invalidating certification SHA.
* Do not claim promotion readiness from certification alone — execution PR required.

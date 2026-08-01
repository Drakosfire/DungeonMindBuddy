# REPORT — Build PDF/OCR lineage pilot (BLD-09)

> **HISTORICAL / RESEARCH evidence (salvaged 2026-08-01 from PR #395 head `bb7e4eb7485ee0923b5c45c01abf93ba9f68040a`).**
> This is the completed BLD-09 PDF/OCR lineage pilot report (GO decision; 3/3 page-lineage reload trials; one canonical source identity; fail-closed OCR/page-map; zero graph promotions). It is preserved as durable historical evidence. It is **not** product authorization to land dormant PDF adapters.
> Current product successor / re-anchor gate remains [`Docs/Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md`](../Plans/HANDOFF-bld09-pdf-ocr-lineage-pilot.md) (still PREPARED/DRAFT pending BLD-08 re-anchor). Salvage ledger: [`REPORT-superseded-open-pr-salvage-2026-07-31.md`](REPORT-superseded-open-pr-salvage-2026-07-31.md).

- **Date:** 2026-07-22
- **Scope:** bounded PDF identity + OCR page map → page-lineage spans → ExtractionRun reload

## Decision

**GO** for admitting PDF/OCR page lineage into the existing SourceArtifact →
ExtractionRun → Graph Review path. Invalid OCR/page maps fail closed; duplicate
PDF+OCR digests reuse one canonical source identity.

## Aggregate metrics

| Metric | Value |
|---|---:|
| Trials requested | 3 |
| Trials completed | 3 |
| Passed (page lineage reload) | 3 |
| Failed | 0 |
| Distinct canonical source identities | 1 |
| Auto-promotion events | 0 |

Exact trial/run IDs remain local under `out/evals/pdf_lineage_pilot/`.

## Observations

- Every span carries `kind=pdf_page_region` with `page`, `region_id`, and parent
  PDF/OCR digests.
- Empty OCR and incomplete page maps are rejected before run registration.
- Publication remains Graph Review only; this pilot does not advance the graph head.

## Redaction inspection

- Report contains no PDF bytes, OCR prose, or model payloads.
- Fixture is a minimal redacted page-lineage contract string.

## Follow-ups

- Broader mechanical/statblock consumer integration.
- Bulk PDF admission remains deferred.

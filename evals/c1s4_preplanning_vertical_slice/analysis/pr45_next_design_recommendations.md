# PR45 Next Design Recommendations

## Immediate (next PR)
1. Add query-sensitive lane routing so route questions favor known gaps/worldbuilding and support-required questions favor support lanes.
2. Introduce lane budgets (not purely flat global budget) to reduce prior-memory over-admission.

## Near-term
3. Add rendering compression for prior-memory (cluster/summarize repetitive rows, preserve provenance links).
4. Add explicit ordering policy that elevates support cards and known gaps above generic recap rows when relevant.

## Follow-up instrumentation
5. Add quality metrics to benchmark outputs:
   - support burial depth
   - section token share
   - noisy-row density
   - relevance-weighted admitted ratio

## Defer
- Shadow LLM retrieval planning (defer until deterministic packet quality improves).
- Gold expansion (defer until quality metrics are available to avoid false confidence from pass-only signal).

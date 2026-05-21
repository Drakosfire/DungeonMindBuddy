# Post-PR60 Planning Recommendations

1. **PR61 — candidate merge-depth / alias-slot allocation repair.**
   Q1 Grishna’s useful summary record is alias-retrievable but falls outside the PR59 alias-slot merge window. Fix candidate-pool construction so required NPC-family records can enter the actual Step2C candidate pool.

2. **PR62 — renderer section repair.**
   Several admitted character records now preserve `presentation_lane=party_timeline` but still show rendered-section mismatch in the surface matrix. Once candidate/admission movement is stable, repair rendering/provenance section routing.

3. **PR63 — generalize preservation rules.**
   PR60 uses C1S4-scoped NPC-family preservation. Generalize only after the benchmark surfaces are stable.

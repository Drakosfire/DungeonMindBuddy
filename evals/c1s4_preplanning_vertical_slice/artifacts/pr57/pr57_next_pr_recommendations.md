# PR58 Planning Recommendations

1. **Materialization decision:** decide whether campaign corpus NPC/location hubs and dossiers should be ingested into the Step2C retrieval record universe; if yes, add explicit materialization wiring and verify source_kind/route metadata.
2. **Support miss diagnosis:** for support-enabled modes, trace why support cards reachable via direct retrieval probe are absent from Step2C retrieved/candidate surfaces (query text construction, mode filters, or packet assembly gates).
3. Keep admission/rendering/gold unchanged until the earliest failing surfaces above are resolved and re-audited.

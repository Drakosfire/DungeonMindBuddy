# PR57 recommendations

1. **Retrieval indexing**: verify index population for `session_memory`, `npc_hub`, `location_hub` sources used by Q1/Q3/Q5 required groups.
2. **Path/canonicalization audit**: validate source-path aliases for Stone Bridge, Mirathorn, and Hempholm to ensure retriever term/path hits.
3. **Guardrail diagnostic**: add a Step2C warning/error path when all three modes return zero retrieved context for benchmark questions.
4. **Admission tuning deferred**: do not tune lane budgets until candidate matches are non-zero for missing groups.
5. **Rendering tuning deferred**: do not tune section mapping until admitted matches are non-zero.

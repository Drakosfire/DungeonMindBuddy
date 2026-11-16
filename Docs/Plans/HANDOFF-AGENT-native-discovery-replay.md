# AGENT — Native source discovery hops in replay

Status: ACTIVE under the unified reply Details goal. Serial successor to
merged Buddy #3766 (`48530a09e`). The active branch is
`codex/buddy-native-discovery-replay` in the graph-timeline-layouts checkout.

Scope is the existing pinned native query producer, its optional host receipt
metadata, its first-attempt trace projection and the replay frame consumer.
Record a hop when a scoped admitted ABOUT relationship leads to a successfully
opened qualified source statement beyond the search result, or when a complete
seed read returns an admitted incoming assertion from a new subject. Keep exact endpoint
and assertion identity. Existing search, evidence, and controller authority stay
as designed. A bounded sample is enough to replay retained hops. Historical
query encoding stays compatible when the optional field is absent.

Verify the Core-backed candidate-open case, native query and trace contracts,
exact-commit frontend suites, and independent review. Deploy to 5202 and show
the saved hop, pruning reason, and evidence on a fresh Elderwyld reply.

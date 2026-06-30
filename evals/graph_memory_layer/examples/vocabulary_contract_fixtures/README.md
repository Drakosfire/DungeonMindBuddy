# Vocabulary Contract Fixtures

Status: hand-authored deterministic contract fixtures  
Authority class: `vocabulary_contract_fixture`  
Candidate graph comparison: no

These fixtures exist to validate the shape and JSON round-trip behavior of the contextual vocabulary contract models. They are not canon campaign memory, extraction gold, projection gold, or prompt inputs.

They must not be used for candidate graph extraction scoring, Stable Global Node truth, corpus promotion, or gameplay canon.

## Files

| File | Model | What it proves |
|---|---|---|
| `manifest.json` | Fixture manifest | Lists every contract fixture file, count, authority class, and non-goals. |
| `source_artifacts.json` | `SourceArtifactRef` | Source artifact reference shape for world and campaign scopes. |
| `lexical_observations.json` | `LexicalObservation` | Raw lexical observation shape, including `combat_encounter` kind hints and evidence refs. |
| `vocabulary_entries.json` | `VocabularyEntry` | Vocabulary entry shape for place, polity/collective, and combat encounter examples. |
| `alias_candidates.json` | `AliasCandidate` | Alias candidate shape, including needs-review and cross-type/place-polity risk flags. |
| `do_not_merge_decisions.json` | `DoNotMergeDecision` | Unreviewed do-not-merge warning shape. |
| `containment_hints.json` | `ContainmentHint` | Containment hint shape for parent/child labels and evidence refs. |
| `context_vocabulary_packet.json` | `ContextVocabularyPacket` | Lossy context packet shape with alias, do-not-merge, containment, type, predicate, and combat encounter hints. |

# Validate active graph bindings against native authority

MIND owns this serial V10 slice on Buddy main e3a1d3095dfcae796acbb8dd1bfb0746ca379ed7.
Predecessor PR #4256 merged at edb006f4b0837a29ab2138499d0a60aab8e10ad6
with exact reviewed source a874746b870f5a8deffa95f7dd400bb42a38710d
and final review 5996733142. Its 53 broad failures matched the parent;
the source passed 1,421 hosted tests and the build.

The mounted PUT native-graph-binding route still consults classic genesis,
head and revision authority when creating or reactivating a binding.
Validate the current native KnowledgeSpace and native head through the
established DungeonMind admission path. Preserve managed-to-native
identity checks, authorization, uniqueness, idempotency and CAS, including
FirstWorld activation and deactivation. Do not infer a binding from a name
or fall back to classic genesis when native admission fails.

Audit existing activation and current callers before edits. Scope to the
binding route/service and owning tests. Prove new and reactivated bindings,
missing/invalid native authority, stale CAS, no classic repository reads,
and unchanged authorized/idempotent and deactivation paths. Qualify and
independently review before merge. Retained receipt reads are separate.

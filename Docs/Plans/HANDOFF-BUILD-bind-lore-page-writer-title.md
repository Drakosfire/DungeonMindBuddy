# BUILD · Bind explicit lore titles at the writer boundary

Status ACTIVE. The AW10 goal authorizes this serial successor to merged
#4042. Base e99f477c92d2b256791f4a2dc72a337e5fee195a. Branch
codex/aw10-lore-title-binding runs in its own Projects checkout.
Provider qualification uses the disposable AW evaluator on 32787.

AW10 turn 7 reached standalone lore review. Its model-authored title failed
the host's existing exact title check. Derive the explicit title from the
author's instruction and constrain the native writer schema to that title. The live test then reached blank
body validation, so bind explicit blank requests to an empty body and a
required lore review in the same schema. Restrict populated lore reviews to
passage-backed claims and labeled proposals after the next live turn
exposed a mismatch with the existing completion validator. Keep host-added
limitations visible in conversation while excluding them from the saved body.
Reconstruct the same binding when verifying the serialized request. Preserve
historical request verification, ambiguity checks and revision-bound save.

Write scope is the existing lore review parser, Build writer work projection,
native writer request verification and schema, lore completion and saved
body projection, and their focused tests.
Verify explicit pivots, an unrelated/connected control, exact format
reconstruction and ordinary isolated replay. Keep Gold local.

# DOGFOOD: retain current readers in deployment recovery

Status ACTIVE. Alan explicitly authorized deployment of the conversation-to-page
fixes and actual signed-in app acceptance. The old serving reader cannot read
the new schema; prepare a compatible fallback before migration/cutover.

Serial single PR on `codex/dogfood-serving-reader-recovery`, exact parent/base
`codex/dogfood-serving-recovery-base@6fca711009799516bb349260dae6c6d050bef769`.
Review and merge this PR into that dedicated recovery base only, never `main`.
The normal candidate remains exact canonical `6fca711...`. This repository
checkout is the implementation lane. No unmerged behavioral dependency.

Expected exclusive writes: this handoff; `build_intentional_response.py` active
menu/default selection; the two corresponding imports in `build_jev_driver.py`;
`test_build_intentional_response.py` and `test_surface_native_build_decision.py`.
No DTO, schema, provider/model, frontend, authorization, source-opening or saved
page changes. Open Plan checkpoint #4433 and ranked-passage #3307 paths and all
other owners remain untouched. ONBOARDING was informed of the deployment lane
and is avoiding overlapping production changes; its live Worlds remain intact.

Adopt the previously independently reviewed #4414 recovery mechanism onto current
readers. Keep the complete WORK inventory and frozen menu registry so both
pending-Graph and source-only prior-citation rows still validate. Only new
controller decisions and the bare harness selector use the older authoring
menu. Existing source-only eligibility and reader fence0187 remain unchanged.
Retain current selector tie handling. This is a recovery artifact, not removal
of the feature from the normal candidate.

Validate exact-head focused menu/decision/native-body tests; independently
review the cumulative base-to-head diff; prove that retained current-source
Maelthor and source-only history/citations/pages reopen with this artifact and
that fresh supplied-context page creation still works. Use uniquely owned
disposable databases and output directories on the verified Projects filesystem.
No service port or shared database ownership is claimed by this PR.

The deployment assignment separately owns image build, host-local protected
backup/restore and migration rehearsals, then user-authorized cutover and actual
app acceptance. Those external results stay outside GitHub. Do not claim
production qualification from this recovery PR, overwrite canonical candidate
tags, or restore old schema markers. New production data must remain readable.

Predecessor settlement: #4429 source-only reuse is merged as7092e7bef5bb65d1ea3774bcc1b862c03905da9e;
its implementation lease is finished. Its frozen ACTIVE assignment is historical.
The normal main candidate also includes #4402 and the reviewed onboarding image
placement fix #4432. Earlier recovery #4414 qualified only its older release;
it is mechanism precedent, not compatibility evidence for0187.

# Temporal shadow adversarial cohort V12 (TL01G)

**RETIRED as independent TL01G promotion evidence.**

Adversarial V12 was sealed as TL01G promotion adversarial evidence after fixture
seal `cde3b48d5b95ba4fc1f7c779993c2497f66914f7`. Gold, sources, cases, and the
observed 18-attempt matrix are retained **unchanged** as incomplete / regression
material only — **do not patch gold** and **do not rerun** the promotion matrix
on this cohort.

**Seal SHA:** `cde3b48d5b95ba4fc1f7c779993c2497f66914f7` (retained)

## Observed gold defects (invalid promotion authority; do not patch)

1. **Gate E3 / value grounding — ungrounded valid-start raw_expression:**
   assertion *The Nightloom Archive has remained shuttered since the equinox flood*
   (`assertion:5ebdb8abe4bc43db`) resolves `valid_time.start.raw_expression` to
   `"since the equinox flood"`, but owned source `valid-start-textual.md` only
   contains `"became shuttered at the equinox flood"`. The gold value is absent
   from owned evidence.
2. **Gate E3 — end-boundary cue fidelity:**
   assertion *Pel Raith quit recording Ambercliff transit logs following the pier vote*
   (`assertion:8f5217fb6555d807`) uses source phrase `quit recording Ambercliff transit logs`,
   which does not carry an end-compatible boundary cue under the proposition-bound
   Gate E3 helper (`stopped` / `ceased` / `ended`).

Because observation (18 provider attempts) already occurred, the handoff forbids
repairing this gold and resealing/rerunning. Disposition for the V14/Adv V12
matrix is **`PROMOTION_EVIDENCE_INCOMPLETE`**.

## Next action

Author a genuinely fresh successor holdout/adversarial pair (V15 / Adv V13) with
pre-live Gate E3 + boundary-value grounding over every resolved annotation.
Do **not** treat this matrix as authority for `tl01h-v1`.

Holdout V14 is retired with this cohort (shared incomplete promotion matrix).

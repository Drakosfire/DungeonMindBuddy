# Magic Moment Dogfood — R0-A

**Date:** 2026-07-29  
**Operator:** GM (guided dogfood)  
**Repository SHA:** `686ccb7ed70fd1894212c22252c2567f68daa2b4`  
**World / campaign:** `eldyrwild` / `longmont-c2`  
**Graph revision:** `rev:480267555eda00356cdb6d843b08b93c` (exact Optional override; bootstrap status was `invalid_bundle` with null head)  
**Result:** `FAIL_PRODUCT`

## Intent

Prove the merged Workbench live path:
create ThreatDraft → real provider generate → edit → validate → revise → accept → reload with exact `(statblock_id, revision_id, digest)`.

## Starting state

- Three processes up; readiness `configured/available`, `downstream_status: ready`.
- Product door corrected mid-run: launcher → **Plan → Tools → Statblock** (not abandoned `/surface`).
- Workbench create chrome tidied mid-run (scope/slice moved under Optional & advanced).
- Graph head exists and projects; world-graph-bootstrap status did **not** report it.

## Steps actually taken

1. Opened `http://127.0.0.1:5173/` → Plan → Tools → Statblock.
2. Pasted Mireward Latchling description; first create failed: no bootstrap head.
3. Entered exact graph revision `rev:480267555eda00356cdb6d843b08b93c` in Optional & advanced.
4. Create succeeded → generate against DungeonMind `:7860`.
5. Generate terminated: UI showed `Couldn’t generate a candidate for Mireward Latchling: Generated definition failed validation`.
6. Stopped per operator decision (no retry loop).

## Durable identities

- retrieval session: n/a (R0-A Workbench path)
- selected node IDs: `[]` (create still does not capture Hermes provenance)
- admitted source anchors: `[]`
- draft ID/version: `7139872d-46f5-4af0-b033-1575e092f9d3` / `1`
- generation request_id: `a2834704-dfd5-4bf9-b871-6edd06e14c1a`
- candidate ID: **none**
- statblock ID/revision/digest: **none**
- Threat ID/binding ID: n/a
- placement / combat IDs: n/a

### Generate terminal (from Buddy tombstone)

| Field | Value |
|---|---|
| outcome | `terminal_failure` |
| failure_category | `downstream_validation_failed` |
| http_status | `422` |
| terminal_code | `validation_failed` |
| terminal_message | `Generated definition failed validation` |
| DMS route | `POST …/statblock-candidates:generate` (~17463 ms) |
| DMS outcome_code | `validation_failed` (`definition_invalid`) |

Stored draft description was **duplicated** end-to-end (operator paste / form friction) — noted but not treated as the sole root cause without field-level DMS details.

## What felt magical

- Plan toolbox → same Workbench module is the right product door once `/surface` is abandoned.
- Failures classified clearly enough to stop without inventing a mock path.
- Draft persisted even when generate failed (honest split: create ok / generate terminal).

## Friction and misses

1. Dogfood scripts still pointed at `/surface` — abandoned Live Control board.
2. Bootstrap `invalid_bundle` → null `currentHeadRevisionId` while real head projects — forced exact `rev:…` paste.
3. Create UI chrome was noisy (scope line + slice badge); tidied under Optional mid-session.
4. Generate failed closed with opaque “Generated definition failed validation” — operator does not see field/reference issues in UI.
5. No candidate means edit/validate/revise/accept/reload were unreachable.

## Failure / retry / reload observations

- Provider was reachable and answered; not `BLOCKED_DEPENDENCY`.
- Tombstone marks operation terminal (`operation_terminal`); Retry generation (same draft) is available but was **not** exercised by operator choice.
- No reload/accept proof possible without a candidate.

## Verdict

**`FAIL_PRODUCT`.** R0-A requires a real generated candidate through accept+reload. Live provider generate returned DMS `definition_invalid` → Buddy `downstream_validation_failed`. Workbench correctly refused to invent success. Gate does not pass.

Secondary product debt (does not alone fail R0-A if generate had worked): bootstrap head not authoritative for create; `/surface` dogfood door wrong.

## Required next slice

**Smallest enabling slice:** surface or persist **field-level** DMS generate validation issues for `definition_invalid` (and once visible, decide provider prompt/schema vs Buddy contract sync). Do not dispatch `SBW06d` / `AOW*` until a green R0-A generate→accept path exists.

Also keep booked:

- Fix dogfood entry docs to Plan → Tools → Statblock; backlog **Delete abandoned Live Control `/surface` board**.
- Bootstrap status should report real Eldyrwild head when projection head exists (or Workbench should fall back to projection head without Optional paste).

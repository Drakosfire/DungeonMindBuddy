# CLEANUP: remove prototype/product navigation coupling

Status: SETTLED by #4099 at98d3157a09790e5a53a851b9ea24a5de51bd2aa5.
Reviewed14ccffc887d938e1c90caf96b822f0c134282351 independently approved.
884sourcebytes removed, non-navJS/allotherlab bytes unchanged; three DOM modes
33targets pass. Focused16pass; hosted1411/build/validator pass; full8047pass
130fail2pending, explicitonecasepair only intendedresolution, no other omissions/
new failures/changed prefixes. Full qualification remains red.

Historical assignment: ACTIVE under the standing cleanup goal with independent review/merge
permission. Base ca3101a35dbb54d7edc5b58f764365ee7729c691. Serial after #4098;
no unmerged dependency. Existing isolated checkout, no live runtime/database.

## Boundary and critique

Native /combat belongs to AppChrome/CombatSurfacePage; #1550 removed prototype
aliases and imports. Static combat.html remains used by lab pages and historical
browser evidence. Its sole product-mode initNav caller still selects a copied
PRODUCT_NAV list, already out of sync with Home/Graph. Do not make lab JavaScript
an AppChrome owner or delete a useful prototype to satisfy a test. Remove that
unused product bridge and use PREP_NAV for all static lab pages, preserving local
HTML links and active Combat marker in HTTP and file previews. Historical report
captures stay pinned historical evidence, not an immutable current-file lease.

Exclusive writes: evals/c2_live_prep/mireward-prep/assets/prep.js (navigation only),
combat.html (initNav call only), existing combatTrackerProductNav.test.ts (lab
navigation contract; keep registered path), this brief, and prior projection-
capability-fixture brief for #4098 settlement. No Combat mechanics/state/storage,
saves, native route/chrome, Vite config, registry/classification or report edits.
All61 current open head/base diffs checked: no overlapping paths or introduced
product-mode callers. Current repository has only the static Combat caller and
its test. Preserve all other lab bytes; record hashes and nav bytes before/after.

## Verification

Run focused parent/current static navigation plus lab runbook/native Chrome
regressions under global frontend lock with external scratch. Check actual
rendered local links and active marker, including HTTP root/prefixed and file
preview behavior, and all targets exist. No model/provider/network writes.
Exact-head hosted/build/validator and full discovered diagnostic; explicitly pair
the one old/new nav case, no other omissions/new failures/changed remaining
leading messages versus byte-identical parent190971af136d9a1e003388e570cfc6186e0f065d.
Keep inherited131failures, conditional inventory differences and earlier quote
observation red. Independent exact-head source/raw-evidence review before merge.
No product navigation, native Combat acceptance or release qualification claim.

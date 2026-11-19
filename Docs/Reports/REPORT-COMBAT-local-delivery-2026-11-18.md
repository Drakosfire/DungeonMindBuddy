# Combat local delivery — 2026-11-18

This is an isolated local delivery of Combat with real application startup,
governed Graph storage and saved statblock HTTP integration. It is not a hosted
production deployment or a claim that the repository's full diagnostic is green.
Final delivery-PR review is still required.

## Delivered source and route

- Buddy immutable source: b4588d1eb750b4c1becc3c90a91df8e28c322eff, based on
  merged spotlight095311ca9. Its extra commit only pins handoff documentation.
  All8797 tracked files are SHA-256 recorded and checked before API startup.
- Normal FastAPI main:app/lifespan and normal Vite React App, no monkeypatches or
  substitute Combat transport. API8018, UI5219, loopback only.
- Open http://127.0.0.1:5219/combat?world=combat-delivery-synthetic-crossing and
  choose the saved encounter; the retained browser opens Play run
  c03c812f-8f2d-465a-8814-b9135d55b4f2 in the same synthetic World.
- Local delivery remains pinned to this exact accepted source. Later main Core
  artifact/command-adoption commits are separate accepted work, not evidence that
  this running bundle has their dependencies.

## State and provider ownership

All content is explicitly synthetic. No operator/live encounter, Graph, application
database or existing8001/5202/5218 service was changed. No model/inference calls or
production credentials were used.

| Boundary | Actual runtime |
| --- | --- |
| APP | Owned PostgreSQL33073, database dungeonbuddy_app_state_test_ffa68a2fded9, schema0166 |
| Graph | Owned buddy-combat-native-fc67 pgvector container33074; database dmb_combat_runtime_test_84719c143f; locked Corea9e308fe5b208f7ee447bf483a252d08ed04ea0b migrations0021 |
| Statblocks | Merged Server5c201c6238573f47fcdfffa022bbbccdf0803d03 statblock HTTP routes on8019; actual production Firestore repositories |
| Firestore | Official emulator buddy-combat-firestore-fc67 on33075; project buddy-combat-runtime-fc67; no remote Firestore |
| Generative features | Disabled in the statblock service; no provider key or substitute generation used |

Server routes are composed as the statblock module using its production factories,
not the full unrelated public Server app. Its existing local Python environment
was used; this consumer proof does not qualify a new Server release. Buddy uses
the fresh frozen Python environment and Node22.23.0/npm10.9.8 from its accepted
qualification lane. Mutable sessions/artifacts/World data/cache and dotenv roots
are explicit external task paths; session directory and private env files are
owner-private. No global configuration changes.

The synthetic Keeper was published through real Core source admission and
WorldKeeper prepare/commit, then verified binding activation. Saved Ironhide
mechanics passed real HTTP validation and explicit Buddy acceptance, yielding a
real acceptance journal, Server revision and governed World association. Identity
alone was honestly shown before that association existed. Tracker fields remain
the independent Crossing profile: Position, Resolve, Stress and Momentum; there is
no inferred D&D action economy or automatic healing.

## Observed behavior and retained evidence

Evidence root on verified Projects filesystem:
/home/drakosfire/Projects/.codex/buddy-check.LPopRI/runtime-delivery.

- accepted-source-manifest.json: complete immutable source identity/hash map.
- api-accepted.log and context.json: normal startup and actual storage/source.
- native-seed.json and native-migrations.log: real publication/activation and Core
  migration; Graph head remains unchanged by subsequent Combat actions.
- real-association-http.json and real-association-result.json: real validation,
  acceptance and association request/result. statblock-server/create-response.json
  also retains the direct producer create probe; that separate probe is not
  misrepresented as the Buddy acceptance locator.
- integrated-runtime-snapshot.json: raw read-only APP rows and exact Server read,
  plus assertions. Standalone5, prepared Plan2 and live2 each retain15actors; live
  actor/group identities are fresh, exact Keeper mechanics match in all three,
  and Plan/live Captain stress(-2/1), statuses and notes are independent.
- Browser: collapsed12unit group preserves chosen actor visibility; defeat clears
  spotlight, return does not choose one; source projection follows Keeper while a
  different participant acts; immediate reload recovers unsaved notes/status and
  Save commits them. Play initialization clears the selected spotlight while
  retaining prepared values/notes/status/groups/source. Run reload retains edits.
- Real statblock projection rendered in standalone, normal Plan and normal Play.
  All three narrow hosts measured document375px within390px viewport. Horizontal
  tables remain contained; screenshots retain actual surrounding product chrome.

Screenshots live in the chat visualization directory:
/home/drakosfire/.codex/visualizations/2026/11/18/01a1ef4e-ff74-7d11-bd9a-2a499da090ff.
Files combat-real-provider-{wide,narrow,plan,play}.png,
combat-real-{plan,play}-narrow.png and combat-delivered-play.png preserve those views.
The final cold reload after moving to the immutable source bundle again reopened
the saved run, retained live values and rendered the source revision.

## Qualification and limits

Spotlight #4022 was independently accepted at71edcec945e74a07de0d261950643db338a03640:
257backend and1410hosted passes; successful builds. Full default-discovered is RED:
7986pass159fail2skipped versus exact base7979pass159fail2skipped, seven added passes,
no omissions/removals, matching inherited failure causes/source frames/multiplicity.
These are predecessor receipts, not relabeled exact delivery-document-head checks.
This slice changes documentation only; it adds actual integrated runtime/browser
proof and requires its own exact-head hosted receipt and independent review.

Failed setup evidence is retained: the initial plain PostgreSQL image lacked
vector; local auth first had the wrong backend Host and a non-private session
directory. Corrected runtime settings fixed these without product changes. The
first template attempt refused a missing explicit test-admin DSN. Preserved APP
copy rows were checked equal before changing API provider configuration; no state
was reconstructed to imitate a browser action.

## Original prototype comparison

The original request to inspect both pages is fulfilled. After the initially
unhosted page had only been read as source, review correctly identified browser
inspection as unfinished work. A normal reversible HTTP preview on separate
loopback5220 served the exact frozen repository combat.html, assets and linked
markdown; no browser security interstitial or file:// restriction was bypassed.
The preview had no backend proxy and refused writes. Its new port isolated browser
local state from existing product origins. The temporary tab was closed and the
preview server stopped after inspection.

The browser rendered the Session26 Mireward wall-breach table from its retained
static save: initiative/AC/current-max HP/damage-heal/notes are editable in compact
rows, group headings summarize units, dead units remain recoverable, and floating
turn controls keep the current actor reachable. Group collapse worked, a Caelynn
name click opened the actual markdown statblock popup, and Next turn changed the
rendered actor to Meat Mind. Only preview-origin browser state changed; frozen
files and product data were not edited. Wide, popup and narrow screenshots are
combat-original-static-{wide,preview,narrow}.png in the same visualization directory.

The delivered design preserves compact roster scanning, stable ordering, individual
group state, persistent turn selection and quick exact source access. It makes
participation explicit, keeps source independent from tracker fields, and adds
ordered/side/free spotlight pacing and arbitrary typed fields/resources so those
strengths apply beyond D&D. The old narrow table measured about1014px wide in its
contained region; the new hosts preserve horizontal access with document375px at
viewport390px. This comparison does not turn old D&D HP/initiative assumptions into
universal rules. User table-play acceptance is not claimed.

## Retained local service handoff

The useful synthetic rehearsal stays running intentionally. The immutable bundle
and state live outside the author checkout. This is an explicit retained-runtime
handoff, not a cleanup-success claim. API/UI process handles46897/46361 and statblock
service69957 are transport handles; delivery-ownership.json records actual PIDs,
ports and container identities. Private runtime-env-delivery.json holds only local
disposable capabilities and must not be published. Nothing is exposed beyond
loopback. Do not prune its source/state while this delivery is in use.

To settle later, stop only the recorded owned API/UI/statblock processes, then
remove the two labeled runtime containers and their anonymous volumes, and drop
only the recorded disposable APP database. The earlier failed native database on
plain PostgreSQL was removed after checking that it had no active connections;
its exact identity and successful removal remain in the ownership receipt.
No prefix-wide deletion or shared PostgreSQL removal is authorized. Retain the
referenced receipts/screenshots; Git history owns superseded process notes.

# SERVER — isolated current-main runtime preparation

PRIME authorized a separate checkout and exact locked Buddy/UI environment,
existing launcher verification, and pinned launch/rollback recipes. This gate
grants no listener start, operator-runtime swap, provider call, model download,
private-configuration export, or APP/native database mutation.

Predecessor mounted proof PR #1095 was independently accepted and merged at
`fad78a85d710f560bc297f867b6e3c1fa4f0940e`, exact head
`bd53d6f2205ab49737efc9e09f0672c4bebd9763`, PRIME review `6129371710`.

## Pinned prepared candidate

- Checkout: `/tmp/buddy-runtime-candidate-20261012`, clean and detached at
  `fad78a85d710f560bc297f867b6e3c1fa4f0940e`, tree
  `a39554747936fdae84ebac319683ae48f7e8b3c5`.
- The intervening `0cc3cada` → `fad78a85` diff contains only the accepted #1095
  documentation. The built runtime and dependency inputs are unchanged.
- Independent environment: `/tmp/buddy-runtime-candidate-20261012/.venv`, a real
  directory, not a link to the live environment. Python 3.13.12; Core exact
  `13143455b304d748c249bd7bd628134c421bf6d9`; 100 unique installed packages.
- `uv.lock` SHA-256:
  `1f2747cad2934bc6f2e7ee5af7b83c0a227d01a75ddab507b3d29f254c9dfb8e`.
  Installed-package inventory SHA-256:
  `c6692bff57589d1c913a6e3c9f9c536f6bd89928b36fe2684438f3d31141e24a`.
- Hermes 0.18.2 was prepared from cached upstream commit
  `861d69c7bba8d2ea6a1cd170e989c901c74d32d1` and the checked-in patch
  `b86a45648bd323eaf58f73550725c2fb8d0442e58bc5471ee2c369fe82a53ada`.
  Prepared tree `0430126a406c559bb38b86990f513e19c2ec938e` passed verification.
- UI: Node v22.23.0, npm 10.9.8; exact package-lock SHA-256
  `860c764cbe376a7b996b77b6ee45f709f8debd9d4713de2f45dbf5817d87c5b2`.
  Build inventory SHA-256:
  `63629e0da6083d56adffb6753b3672f5339f5ea892f9f082ac4f656bc8524516`.
- Existing `run` launcher SHA-256:
  `e20dc73a68d210f2127025df4e7e8b462450cbe2f13c8eee85f62ee7b2803179`.

The [candidate receipt](evidence/server-isolated-runtime-prep-2026-10-12/candidate.json)
contains the complete version/pin inventory and build hashes. SHA-256:
`f7fff9ad26b213c95b01fc40d8f686f5bf188832a616440e38e1e4121a7747c0`.
It contains no credentials or provider/source bodies. Preserve this checkout and
environment until PRIME settles the candidate; it is not an active operator runtime.

## Verification and resource result

`uv sync --locked --offline --link-mode hardlink` found a concrete cache miss for
Core Git commit `13143455`. The authorized online `uv sync --locked` fetched that
exact ordinary dependency, then built Buddy, patched Hermes, and Core. Other
packages were cached. Cross-filesystem hardlinks fell back to copying. No model
weights or embedding assets were downloaded. Initial free space was 9.3 GB;
after preparation it was 8.1 GB. Candidate `.venv` is 249 MB, Hermes source 248 MB,
UI dependencies 258 MB, and built UI 4.2 MB, excluding the Git checkout.

The exact install passed `uv pip check` and `uv lock --check --offline`.
The first read-only sandbox checks could not acquire uv's cache lock; the same
checks passed with authorized cache access. `prepare_patched_hermes.py --verify`
and `bash -n run` passed. Provider-free import resolved the actual Buddy main
module to this candidate, found 191 mounted routes, and confirmed Core, FastAPI
0.136.3, Pydantic 2.13.4, and Hermes 0.18.2. No application lifespan/startup ran.

`npm ci --offline --no-audit --no-fund` installed 575 packages in the candidate.
`npm run build` passed TypeScript and Vite production build. Existing React 19 /
react-inspector peer warnings, deprecated transitive packages, and the large
bundle warning remain warnings; no dependency or source adjustment was made.

Six focused provider-free tests passed in this new environment: source request
typing, parent recap broker and exact provider inclusion, both unfrozen/frozen-V1
policy variants, runtime policy serialization, and locked Hermes AIAgent import.
No broad suites, live DB harness, provider, model warming, or listener were used.

## Live preservation result

The [post-preparation live receipt](evidence/server-isolated-runtime-prep-2026-10-12/live-after.json)
has SHA-256 `f350917f80260ff33b5a0694669c3830c4d93b3be6320c64b0a08829cd81da1e`.
Compared with the accepted #1095 planning receipt, these fields match exactly:
runtime checkout/head/tree/status, process ownership/cwds/executables, safe launch
settings, profile and lock/launcher hashes, continuity hashes, live environment
path and installed Core, Node, authority identities, and three health statuses.

The live API/UI remains `/tmp/buddy-automatic-chat-reconciliation@98f0c225066fff9ec836b05ac7d78e0de983e8ff`
with its original shared environment and Core `ba6069b9`. PGID 497628 still owns
5202/8000/7860; all return HTTP 200. The modified tracked Hermes pointer, untracked
environment link, and 16 private profile files remain intact. No secret config
was copied into the candidate. The collector performed no direct database query or state mutation.

## Explicit effective configuration and conditional recipes

PRIME independently accepted this preparation and merged PR #1096 at
`3e831bc367882ff41e8859c3367c6390c2581662`, exact head
`d77f73487d975678f5e9751b4e078fe81d71aef2`, review `6129657061`.
The final configuration preflight and explicit secure launch/rollback recipes are
recorded in `REPORT-SERVER-effective-config-preflight-2026-10-12.md`. They replace
the earlier recipe's assumption of an already populated operator shell.

Candidate environment/build preparation passes. Final runtime activation still
requires fresh quiet/draft/open-turn/action/state evidence and PRIME authority;
the full World product gate remains unproven. No operator dogfood invitation follows.

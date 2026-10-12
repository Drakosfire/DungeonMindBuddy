# SERVER — mounted recap source routes and rollout preparation

PRIME authorized this bounded read-only verification after broker PR #1094 merged
at `0cc3cadac5104c875a7453dbf32df74a208e3036`, following ARCH PASS and PRIME review
`6129042441` of `b8eb7df8a8cda60186cc62f5b0e9ba81f2422456` and its 42 focused tests.
The broker implementation lease is settled. This report changes no runtime implementation.

## Mounted owning-route result

At exact Buddy main `0cc3cadac5104c875a7453dbf32df74a208e3036`, the actual
`world_graph_retrieval.router` was mounted in an isolated FastAPI app and called
through `httpx.ASGITransport` from a synthetic loopback client. Authentication used
the real local-operator dependency with a synthetic process-local credential;
there were no service, Core, source-reader, or dependency overrides. No listening
port or application startup/lifespan was involved.

The native authority was the retained `eldyrwild` World at
`rev:62820bcd7eca116af9d889e128fabf4e`, PostgreSQL 127.0.0.1:54330,
database `dungeonmind_cutover_live_restore_20261011`. The connection URI and
`PGOPTIONS` enforced `default_transaction_read_only=on`; direct connection checks
confirmed both default and active transaction read-only settings. Every Core
connection used that URI. Installed Core matched main's exact pin
`13143455b304d748c249bd7bd628134c421bf6d9`.

- Unauthenticated index and read requests: HTTP 401 / `graph_auth_required`.
  An incorrect synthetic bearer also returned 401.
- Authenticated ordinary World scope (`campaignId=""`, `scopeMode="world"`, GM,
  exact revision, null none-focus): index HTTP 200, complete, 19 descriptors.
- S22 and S23 descriptors were returned by real Core, then opened by the mounted
  read route. Full source byte digests, descriptor equality, section digests,
  heading line 12 and section lines 13–38 were verified.
- Each section was read in ten pages capped at 1,000 characters. Offsets were
  contiguous; reassembled text equaled the full read and its SHA-256. S22 contained
  9,660 section characters; S23 contained 9,250. Invalid continuations returned
  HTTP 409 without content.
- Native head before and after was exactly
  `rev:62820bcd7eca116af9d889e128fabf4e`.

S22 source artifact `corpus:eldyrwild:session-22-recap` retained source digest
`06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083` and section digest
`c320260289bcf77aa1a90cca5ac6ca006352d1229bf348f2de26a60b5c2f68d1`.
S23 source artifact `corpus:eldyrwild:session-23-recap` retained source digest
`77ba5030b5c89e8888e8a3d900fe3fc07b94313af81a7ad5f888eb663d4c7782` and section digest
`06a706ffafdda0eb2297f747084c2fff9f3e166a49ead99c7f8242961fa7f268`.

The [metadata receipt](evidence/server-mounted-recap-route-proof-2026-10-12/receipt.json)
contains IDs, digests, ranges, lengths, statuses, and head before/after; no source
body, URI, or continuation token is retained. Its SHA-256 is
`1b6b54fcf476631ee092d5fc35c93c097eb35dabe25512ff957341de7ca99e1f`.
The [exact isolated probe](evidence/server-mounted-recap-route-proof-2026-10-12/probe.py)
has SHA-256 `57dbc903c03c41907a3e03b76cf4cc7f82da336ed418107759b817d799cbe2ee`.
It reused the existing SOURCE proof's retained authority and expected digests,
extending it through HTTP routing/auth and pagination rather than creating another harness.

## Exact launcher and rollback planning receipt

The [read-only launcher receipt](evidence/server-mounted-recap-route-proof-2026-10-12/launcher-rollback-receipt.json)
was captured at 2026-10-12 11:26 America/Denver. SHA-256:
`8093e35ff084df0527552aa3069d15bf7e466ab35112297fa150eb84e7216d76`.
Its [collector](evidence/server-mounted-recap-route-proof-2026-10-12/launcher_receipt.py)
reads only process metadata, safe environment paths, package metadata, file hashes,
Git identity, and existing health endpoints. It records no credentials or bodies.

Current-main candidate is `0cc3cadac5104c875a7453dbf32df74a208e3036`, tree
`d4da5357834332017cb2c7331cce9ec9f0043833`. Candidate and existing rollback `run`
launcher bytes agree at SHA-256
`e20dc73a68d210f2127025df4e7e8b462450cbe2f13c8eee85f62ee7b2803179`.

The active Buddy API/UI checkout is `/tmp/buddy-automatic-chat-reconciliation`,
head `98f0c225066fff9ec836b05ac7d78e0de983e8ff`, tree
`38164fd84da3ba9333eb672373053cf46bccc2cf`. This is the rollback basis, not the
obsolete permanent-runtime path in older rollout records. Listener ownership was
PGID 497628: UI PID 497672 on 5202, Buddy API PID 497657 on 8000, Web API PID 497651
on 7860. All three health endpoints returned HTTP 200. These PIDs are observations,
not standing authority to stop them later.

Preserved launch configuration selects the same operator profile, managed and
artifact roots in the primary Buddy data repository, Web API repository, and
ports. `RUN_NO_RELOAD=1` and `UV_NO_SYNC=1` are effective. The actual UI Node is
v22.23.0; Buddy Python is 3.13.12; Web API Python is 3.12. The exact paths and hashes
are in the receipt.

Two concrete gates prevent treating this as a ready live rollout:

1. The live Python environment still contains Core
   `ba6069b91e1a608f125548860502a69b4c3e3fc6`; current main requires
   `13143455b304d748c249bd7bd628134c421bf6d9`. Candidate lock SHA-256 is
   `1f2747cad2934bc6f2e7ee5af7b83c0a227d01a75ddab507b3d29f254c9dfb8e`, different
   from the runtime lock. A separately prepared candidate environment must match
   the exact accepted lock and pass provider-free import/preflight checks. Do not
   sync or repoint the live shared environment to hide this mismatch.
2. The active checkout contains operator continuity state: a modified tracked
   `hermes_thread_pointers.json`, an untracked `.venv` symlink, and untracked Hermes
   profiles. The pointer SHA-256 is
   `1a785a7e5754d04f8ba68fa0c27e4a7dd958cdceee431e3cd2185958269df1af`; 16 profile
   files have inventory SHA-256
   `bc304a57c799c6ecc4f12ce8918be36a7caf64ebd317a0d2de40acf0ec2ca197`.
   Preserve these and all APP/Plan/Run/source/native state under a fresh quiet
   snapshot and an explicit continuity-root plan before any switch. The existing
   checkout can remain intact as rollback; do not reset/clean it.

A later PRIME-approved quiet rollout must re-fetch and pin its exact candidate,
coordinate the existing #1014 rollout lane, revalidate process ownership and
profile/environment/state hashes, prove no open Agent turns or Plan actions,
preserve all operator state, and obtain explicit runtime authority. Launch only
through the reviewed `./run` procedure with the verified environment and profile.
Rollback returns to the preserved `98f0c225` checkout and original environment;
it requires newly verified process ownership and identical state evidence. No
stop/switch/restart/rollback command was executed in this verification.

## Limits and next gate

This closes the mounted source-route auth/native-byte-read seam. It does not
prove a live Agent/provider answer or complete the full World product gate.
The current operator runtime has not been upgraded. No operator dogfood
invitation, provider call, APP/native DB write, migration, source mutation, or
listening-port change is implied by this receipt. PRIME owns the next funded
verification and any separate quiet rollout authority.

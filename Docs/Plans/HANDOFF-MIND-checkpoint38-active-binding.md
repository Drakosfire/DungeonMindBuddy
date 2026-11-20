# MIND handoff: checkpoint-38 active binding

Status: `MERGED` for PR #1049 at `b02622b03683d52344d3cfd5df833676483d2339`. A subsequent MIND implementation lane is preparing the six-session execution contract on the three paths named below. Code review and the exact execution packet must complete before any private-data run.
Scope: checkpoint-38 verification and an explicit, packet-bound continuation for frozen ordinals 39–44. The runner never creates an identity decision; the human decision remains a prerequisite.

## Accepted basis

- Buddy PR #1048 is merged at `f21d92798457497350a5aa58a11273c791b1a10`; the guarded Core publication path is pinned at `33ad2983385e8c4e80afb64b07fdb538f9c89901`.
- The preserved checkpoint contains 38 accepted sessions and ends at `rev:dfe5ad1c967a365d3f7748b38faa1a9c`. The continuation report SHA-256 is `a6ca378e8055862e41c003808c10a5cf04710d5afd5576a05806636bfe3696d2`. The exported current head matches that revision; the revision payload hash is `8bef219e30478a9c5f2efccbd53541fc5ffd979a9796958851839a80a7661250`.
- The eight pinned row exports were hash-verified against the accepted evidence packet: 39 graph revisions, 1 head, 38 reviews/publications, 77 contribution rows, 39 source artifacts, 39 source revisions, and 0 identity decisions. The 77 contribution rows are not 77 accepted publications.
- Private evidence root: `/home/drakosfire/.local/state/dungeonmindbuddy/recovery/full-corpus-20261008`; report is in `continuation-run-01/`, exports in `exports/`. SHA-256 pins:
  - `after-continuation-run-01-graph_revisions.jsonl`: `35b91ecdbfb2db15fa3fd31131c6869d0bd65ef0dc6061237c69f83cd461e5cc`
  - `after-continuation-run-01-world_graph_heads.jsonl`: `77571c2ef4a83c59f8dfc9f70d8bde804e78004c5ebde881a94b953b611a1ea4`
  - `after-continuation-run-01-graph_contributions.jsonl`: `b87cabb2ef37063953cc45429334e66f85ab4268fca48539c75ed1c096bd652d`
  - `after-continuation-run-01-contribution_reviews.jsonl`: `3f7e85a8914c7d2796c5df529a72dbe9623ea19c8d618021d8b6cf5bd0403422`
  - `after-continuation-run-01-finalized_review_publications.jsonl`: `9d3ee9f07efb79edbbbf748a0c0286407eeaf06f7704daae21dac1c18a65cf91`
  - `after-continuation-run-01-source_artifacts.jsonl`: `a3057bf024ce165347a8fa0cc8e004aa986a7f4ec1b77e5d4a09694e7d03f437`
  - `after-continuation-run-01-source_revisions.jsonl`: `9872b71f71456d8f81371615bd4f9ecb72288eb28b788ac734f9ba46a5f2f5a2`
  - `after-continuation-run-01-identity_decisions.jsonl` (empty): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- S22 is ordinal 39, the first of the six remaining accepted sessions. Its frozen candidate digest is `143e1f9df81a85e47037651ecb70c7b12bc3347dc220a6964f1a1a66f500e726`; the candidate file SHA-256 is `ceee5df3a55b137d29f86e1e036fddd09b02eff11b2c1440b5c708d98a314816`. The immutable source is `artifact:recap:longmont-c2:session-22:06c978131f31`, revision `sha256:06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083`.

## Proposed S22 reviewed binding — not yet a decision

The candidate node is `node:thrin-branchborn`, with resolved NPC corpus key `thrin_branchborn`, campaign `longmont-c2`. The exact checkpoint payload contains canonical NPC object `npc_thrin`:

- target fingerprint: `eda071794473d178d251b6f439bbffc08f97b146792dcd0c6db546e64af188ea`
- existence-evidence fingerprint: `7ffd15dd2e7460a836f6e74e4a290e6f38688127afeff0c8f52d77aa7371b758` (three refs)
- complete evidence source closure: artifact `artifact:recap:longmont-c2:session-17:6f01fc518dea`, revision `sha256:6f01fc518deabfd705cfc76ba9754a72de6061f4e3e8443a0df2dbf8e088f97a`; artifact fingerprint `6f28dae77456341df2f73a5cbb0b67a114c6802639987961e68676b358122f6c`, revision fingerprint `d032bcd9bd7d7964fe545e634caf28ea9b7e5185f2930a12d7fb9c5cbeaaa68c`.

The default known-party resolver returned zero native matches for `thrin_branchborn`; it did not prove that this candidate already resolves to `npc_thrin`. The values above are therefore a proposed human-reviewed link, not an automatic mapping. No trusted operator-review principal is established in the checkpoint evidence; `reviewer_id` and `decision_id` remain unset. Do not fabricate them or append a decision until an authenticated human GM/operator explicitly approves this exact link.

## Source gate and proof obligations

`_Authority.checkpoint38_binding` must call the existing `load_production_mutation_context` for the exact World, checkpoint revision, and DSN. It must require context world, revision, and current head all equal the pinned checkpoint; exactly one typed binding for the frozen S22 digest/campaign; and exactly one typed `IdentityDecisionRecordV2` that is ACTIVE `human_override`, names the candidate node and bound target, and has `actor == binding.reviewer_id`. The decision ID must be nonblank and already trimmed; the canonical Core decision-record SHA-256 must equal the exact lowercase 64-hex CLI pin. Do not normalize, fall back, parse the carrier a second time, or accept injected authority/seams.

This gate is read-only preflight. Buddy's existing confirm path and Core's guarded transaction remain responsible for rechecking publication authority at commit time. Passing the source gate alone does not authorize the six-session run.

`--verify-checkpoint38-binding-only` runs the preflight and returns `CHECKPOINT38_BINDING_VERIFIED_READ_ONLY` before output-directory creation. Ordinary checkpoint-38 continuation remains held. `--execute-checkpoint38 --execution-packet <private JSON>` is the only execution mode. It validates the complete packet, the authenticated decision through the existing production context, exact checkpoint head, every suffix input, and a fresh complete PostgreSQL backup before calling the existing admission/confirm path. This code path is not an instruction to run it before review and a real human identity decision.

## Six-session execution packet (new bounded contract)

The private JSON object has schema `dmb_checkpoint38_six_session_execution_v1` and exactly these fields: `schema`, `world_id`, `checkpoint_head`, `checkpoint_report_sha256`, `manifest_digest`, `source_head`, `binding_decision_id`, `binding_decision_sha256`, `output`, `accepted_root`, `retained_root`, `checkpoint38_report`, `target`, and `suffix`. `output` is an absolute, previously unclaimed direct child of the pinned private recovery root. `target` is `{host, port, database}` and must match the runner's fixed isolated PostgreSQL endpoint. `source_head` is the exact Buddy execution checkout commit. The binding fields identify one existing, ACTIVE, human-reviewed Core decision; they are not invented by the runner.

`suffix` is an ordered array of exactly six objects for manifest ordinals 39–44. Each object has exactly `ordinal`, `campaign_id`, `session_id`, `source_artifact_id`, `source_revision_id`, `original_sha256`, `candidate_digest`, and `candidate_file_sha256`. The runner checks these against the accepted manifest/ledger and the candidate file bytes. The packet's raw SHA-256 enters the command digest and report, so an incomplete output can never be relabeled with a changed packet. The packet is private evidence, not a checked-in corpus artifact.

The runner creates `checkpoint38-before.dump` in the newly claimed output, requires a nonempty valid PostgreSQL custom archive, records its SHA-256, and rechecks current head, unclaimed suffix sources, and reviewed binding before the first confirm. It does not overwrite an old backup or auto-resume an incomplete output. Resource/capacity observation and later independent restore proof remain execution-operator obligations under the existing private recipe; this source change does not claim either was performed.

## Execution boundary, once separately released

- Execute only frozen ordinals 39–44, sequentially, with no model/provider calls. Keep the 38-row prefix and accepted inputs immutable. Preserve the failed `continuation-run-01` STOP; never resume or reuse its output directory. A later authorized attempt needs a new private output directory and fresh exact-head/capacity checks.
- Existing preserved database dumps remain immutable: post-checkpoint dump SHA-256 `a7d9daf0b688afe4b2c0d2354a0f361740e73ffe38220fe01f61ab54b3b5de5e`; earlier C1S2 dump SHA-256 `8ad98b722049e26dba9d915f7d05038cff2a306bbc8e3f7b4d8f1686289d2284`. Make and verify a fresh backup under a separately approved execution packet before any future writes; do not overwrite either artifact.
- No database reset, restore, truncation, deletion, or rollback. Published revisions are durable; on any ambiguous confirm or post-commit proof failure, stop, preserve the exact output, and reconcile actual head/receipt before another action. Recheck resource capacity immediately before an authorized run; historical snapshots are not reservations.
- No S28, full-world readiness claim, live Buddy/SDK sync, provider operation, source/candidate rewrite, or World binding. Final44 remains pending.

## Review and completion

The source slice is limited to the continuation runner, its focused test, and this handoff. Review the exact cumulative diff and focused checkpoint-38 gate tests. Existing prefix/production-PostgreSQL proof is reused; do not create a new PostgreSQL fixture or claim it was rerun. The original semantic question remains open: is `node:thrin-branchborn` the same person as `npc_thrin`? No authenticated approval, `reviewer_id`, or decision ID has been established. The full six-session execution packet, target capacity, real backup, restore witness, and private-data confirms remain pending after this code review.

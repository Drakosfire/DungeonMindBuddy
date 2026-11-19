# Elderwyld native serving

Status: activation in progress under HANDOFF-BUDDY-v9-live-native-activation.md.
This runbook will record actual qualified launch/restart/rollback commands and
receipts after execution. It does not claim that5202 is serving yet.

Accepted runtime is Buddy1c7ddcd (test-only successor4f4ed526), Core4b6516e2;
qualification4041 merged d2166f5bfde17e9d595daf108ee5d817eb105ebf. Do not silently
substitute later main. Live authority is existing Core54330 and separate APP54331,
not the606-revision rehearsal restore. Preserve latest live head and binding.

Planned serving mapping: local operator UI5202 → owned API18292. API8000 belongs
to another lane and must remain untouched. Secrets stay in owner-private external
profiles. Database/schema migrations are explicit and never run on API startup.

Before activation require fresh snapshot/restore parity, required external-file
availability, immutable source/assets/import manifest, allowed migration effects,
head/parent read-artifact equivalence and ordinary source authorization proof.

Rollback uses a separately qualified same-version process on latest migrated
persistence. Never downgrade schemas or overwrite live authority with an old dump.
Recovery is a separate explicit procedure. Retain backups and exact receipts;
no fake permanent World node is created to manufacture live-write evidence.

Current proof: Docs/Reports/V9-live-native-activation-v1.json. V10 retirement and
V11 deployed measurements remain separate. Never rerun the frozen classic baseline.

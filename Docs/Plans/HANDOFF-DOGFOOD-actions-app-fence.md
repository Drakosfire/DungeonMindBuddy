# DOGFOOD: Actions transport for an approved App reader-fence packet

ACTIVE serial delivery successor to merged runtime4708/f4ab0a41949b92f265854b78717f5b41a4db9c52.
Alan explicitly requires Actions for every production cutover and authorizes the
writer/context repair, reviewed concrete-progress merges, deployment and necessary
backups. DOGFOOD authors/adopts this bounded delivery contract. Goal remains open.

Base maine9defa5f17df2763951cedc444cc626ca9c762ec (merged4707 trace UI); branch
codex/dogfood-actions-app-fence-packets, existing dogfood-ci-one-app checkout.
Remote/open work rechecked;4707/4704 own frontend diagnostics,4703/4705/4706 guest
serving adoption. No path overlap with this slice. Do not change those leases.
Current production d58/image66ec remains healthy, APP211. Local owned App is212.
Normal fetch has a preexisting invalid Codex capture ref; main matches remote.

Outcome: Actions can invoke a separately reviewed, sealed, root-owned App-fence
packet under the SAME production lock. No remote arbitrary path, command, script,
credential or uploaded code. Fixed packet path is selected by exact candidate SHA;
request pins and packet digest must match trusted manifest, release config and
accepted qualification. Scripts and immutable receipt are hashed. Ordinary image
workflow and its recovery behavior stay unchanged. The packet, separately qualified,
owns drain, fresh backup, restore proof, migration, compatible forward recovery and
configuration preservation. Transport success alone does not prove those steps.

Exclusive writes: new deploy/production/deploy-buddy-app-fence helper;
deploy/production/deploy-buddy-release for a distinct fixed request grammar only;
new .github/workflows/deploy-buddy-app-fence.yml using existing environment/key and
queue; focused helper/dispatcher tests; one ci/test-classification.json entry for the
new credential-free test (4707 inspected; no overlapping lease); this brief and
Actions runbook instructions.
Do not change SSH recipients, credentials, sudoers, branch/environment protections,
normal stage/activate helpers, product runtime, database or production config here.

Failure critique: stale serving identity, mismatched schema/recovery qualification,
mutable/symlink/writable/unowned packet, extra/missing manifest keys, tampered code,
missing inherited lock, prepare/apply failure and false LIVE must all refuse.
Root installation authorizes a packet's exact code; callers cannot install it.
Only root installs reviewed helper/packet files under the lock after checksum and
source review. Packet cannot replace the evidence required by production runbooks.

Verification: minimum focused real-file trust/hash/shape tests, exact pin and
stale-serving rejection before pull/execute, single-lock subprocess protocol,
failure/no-LIVE controls, fixed request grammar and shared Actions queue checks.
No App clones, DB contents scans, broad backend or frontend contracts. Independent
exact cumulative review then commit/push/PR to main. Merge under existing user
reviewed-progress authority. Do not install or dispatch before review/qualification.

Next serial step after this merges: pin current healthy serving source, prepare
APP211->212 packet/candidate and compatible forward recovery, restore/check on the
same exclusively owned App, review actual evidence, publish through Actions and
submit exact release. Publisher serving-parent requirements still apply:4708 has
parent a102 (cold restore), while actual source is d58; do not change rollback pins
alone or publish an incompatible lineage. Prepare a reviewed serving adoption if
production has not advanced. Signed-in briefing, ambiguous-creation/no-search,
citations and saved-page acceptance remain required after actual cutover.

Working-tree evidence:32 focused transport checks pass0.20s. The first run had
five fixture permission failures because inherited umask made test directories
group-writable; corrected fixtures explicitly use0700/0600, while production
trust checks remain strict. Positive packet loading then passes; negative trust
cases assert their exact rejection, not unrelated setup errors. Real descriptor
contention verifies FD9 remains exclusively locked. Tampering during either
operator phase, stale serving, wrong published image and phase failures cannot
produce LIVE. No production config/packet installed, image pulled or App changed.
Actual operator signal/recovery behavior remains the separately reviewed packet's
responsibility; transport tests do not establish a migrated release qualification.

Exact initial source0e50:35focused checks passed0.21s and independent
source/security-contract review PASS. Main then advanced only in4707 frontend
trace paths. Rebase preserves those changes; no frontend behavior is edited by
this slice. Requalify the exact new head at the affected transport boundary,
not by running unrelated frontend suites.

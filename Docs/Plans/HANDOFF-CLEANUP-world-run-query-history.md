# CLEANUP: World-scoped Play query history

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. Serial one PR; base
`01be5519d44d705165e27b4e5f283fb417fe2460`, branch
`codex/world-run-query-history`, reused isolated checkout. No runtime resources.

## Bounded lease and predecessor

Writes: this handoff; only `keeps /play?run= across Ingest navigation and back` in
`apps/live-control-ui/src/test/appNavigation.test.tsx`; completed
`HANDOFF-CLEANUP-local-surface-navigation.md` for predecessor removal. All59open
PR paths and complete #3824 cached paths at unchanged76c31187 checked; only
#2405's obsolete wrapper mock/setup seam overlaps and remains untouched. Shared
fixtures, World admission, Play runtime, compatibility and classification excluded.

#4143 merged at this base, tree identical to reviewedbe30a89a0fd18a54a151a57e0711b34946d1b86c:
fresh parent8145pass105fail2pending→head8146pass104fail2pending, mapped one-for-one
Surface journey; localhosted1406/build/validator and three Agent owner controls
passed. Git history preserves its completed assignment and superseded evidence.

## Invariant, fixture and critique

Current owner d254e29d7b7020de5d6c4e14de32c975e5c7d5dc verifies bare exact Run
links before mounting Play. The old test supplies a404 for that lookup, so it
correctly stops at World-selection refusal instead of its intended Play-missing
screen. Do not weaken that guard or invent a Run-only ownership response.

Test query retention within an explicitly verified World: case-local typed World
list, actual SelectedWorldProvider, native World Run read returning404. Require
native read arguments and no legacy Run read. Play's exact World+Run query must
survive Ingest navigation and Back; Ingest retains World but drops Run. Back must
restore the actual missing-Run screen as well as the exact query. Restore spies
in finally. Keep all other test bytes and this case's ID unchanged.

The first focused0bda25459eeaba427b109048fc7e2ce6b85679ec attempt correctly
reached native Play but failed Ingest's World-projection mismatch guard. Preserve
that raw failure. Supply the existing owning test's projection shape with matching
world_id/campaign_id/session0; verify the actual World-scoped read arguments and
managed welcome heading. Do not weaken the guard or assert an error page as ready.

The9ed7bace5 focused case passed, but the complete module exposed a test cleanup
bug: spying/restoring an existing mock replaced the function expected by later
beforeEach setup. Override and restore the existing mock's resolved value instead.
Retain the failed module evidence. The same run also saw an unchanged first-Plan
cold import remain at Loading Plan past the default assertion deadline; keep that
observation open and compare a same-executor parent/head module control before
calling it inherited or fixed. Do not increase timeouts or preload product pages.

Bare Run-only inference remains a supported separate contract, not retired by
this fixture change. Existing owner controls for managed inference, C2 legacy
admission and refusal of unverifiable Runs remain untouched; all three passed
the retained current baseline and must stay green. No real provider or auth claim.

## Verification

Use a focused isolated exact-source diagnostic first because the managed-World
fixture is new to this module; honor the global frontend lock and verified
Projects storage, retain raw results and remove owned scratch. Then exact-head
hosted/build/validator and full discovered comparison, owning controls, docs and
independent cumulative review. Baseline be30frontend8146pass104fail2pending,
8252reported/8250inventory; full qualification stays red. No keys, user data,
service, API, deployment or selection-rule change is authorized by this slice.

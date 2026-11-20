# GRAPH: one mounted extract preparation authority

Status: ACTIVE. Owner: PRIME under operator cleanup/demolition authority.
Base: origin/main@0aca7c9ccb4a40eb00f76a53ceeab3f782392cf7.
Branch: codex/retire-mounted-file-prepare. Reuse buddy-context-loop checkout.
Topology: serial GRAPH successor to merged/delivered2054; parallel-independent
of2055@ae973e3851745a63049d0da5e5a068fe0c09d23e (catalogue/profile/test/handoff paths).
Older1855,1868 and1235 PR file scopes inspected: no expected-path overlap.
No unmerged behavioral dependency or implementation runtime/provider/DB lease.

## One outcome and boundary

Mounted config.world_graph_authority_mode only returns dungeonmind or raises
WorldGraphAuthorityConfigurationError. Remove prepare's impossible filesystem
else and its redundant non-native PC-proof comparison. Invoke the parser once
at the same admission stage, then use the existing native preparation body.
Preserve the exact native body, parent/revision/PC proof checks, identity ledger,
managed target and exception handling. Do not call the retired root producer,
restore file authority, add fallback/shim or infer a current deployed failure.

Exclusive expected writes:
- apps/live_control_server/services/extract_promote.py
- Docs/Plans/HANDOFF-GRAPH-retire-mounted-file-prepare.md
- Docs/Plans/HANDOFF-GRAPH-retire-worldbuilding-store-adapter.md
- Docs/Plans/HANDOFF-INGEST-runtime-predicate-families.md

The last two paths truthfully settle already delivered2054/2053 leases. This
explicitly adopts the previously optional2053 settlement path; it is disjoint
from2055's fixed five-file lease. No runtime/catalogue/profile/Gold/source/model/
migration/native mapper changes. Do not absorb the five optional root fallbacks
in lower pure helpers: some root parameters still carry historical package
metadata and require separate caller analysis. No tests rewritten or deleted.

## Validation and delivery

Existing14 mounted selector/managed-target tests passed before the change. Run
the same tests afterward with synthetic state, preserving warnings/failures.
AST-compare every native-body statement before/after and all other module
functions/classes; prove only dead branching and duplicate parser comparison
were removed, with the parser still invoked before native work. Existing parser
matrix must reject retired/unknown modes with the same error. New mirrored
source/deletion tests are unnecessary. Inspect cumulative diff and Ruff; obtain
independent Bugbot review and CI, commit/push/open one PR, then merge/deliver under
standing PRIME authority and re-anchored runtime lease. Primary state must be
conserved; tests do not establish full publication/dogfood/model quality.

## Author verification

The same14 existing mounted-selector/managed-target tests pass before and after;
the existing Pydantic schema-shadowing warning is unchanged. No tests rewritten.
AST proof compares the actual native preparation body before/after and every
other module function/class: unchanged after removing only the impossible else
and duplicate mode guard, retaining the parser call. Ruff --no-cache and diff
checks pass. Evidence: mounted-prepare-branch-{baseline,after}.log and ast-proof.json
in the established private runtime-evidence root. These are bounded verification
results; independent review, CI, merge and conserved delivery remain pending.

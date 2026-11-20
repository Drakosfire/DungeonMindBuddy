# World ownership and action grants: core contract

Status: local implementation checkpoint; hosted routes remain unbound.

## Authority and records

Buddy's existing file-backed `WorldContainerRegistryDocument` remains the
authority. Ownership and explicit grants live on each `WorldContainerRecord`
and are changed under the registry's existing mutation lock and compare-and-
swap write. There is no parallel ACL file or production grant map.

New owned Worlds store the exact verified principal subject supplied by a
future server route as `owner_subject`. DMS sign-in supplies an identity for
lookup; it grants no World access by itself. The owner receives all four
actions implicitly. New local-mode records may remain unowned for
compatibility; an unowned record never authorizes hosted use. Existing v1/v2
records normalize to v3 in memory as unowned with no grants. Reads preserve the source bytes;
the next authorized registry mutation writes v3. There is no ownership
assignment or transfer operation in this slice.

No retained World identity is verified or assigned an owner by this slice.

## Action semantics

| Action | Meaning in later route policy |
| --- | --- |
| `read` | Read World-bound resources and results. |
| `write` | Change World-bound content or stateful play state. |
| `manage` | Reserved World administration. It implies no other action. |
| `share` | Create or revoke explicit grants. It implies no other action. |

An owner can grant any explicit set of actions. A non-owner needs `share` and
can delegate only `read`/`write` actions they already hold. They can change or
revoke only grants they created. Losing `share` removes grants they created;
losing a delegated `read`/`write` action prunes that action from downstream
grants. Unknown actions, missing subjects, missing Worlds, unowned Worlds,
and absent grants deny with the same generic access error.

## Route and worker integration is a separate slice

`install_hosted_request_boundary(application)` currently installs an empty
resolver map. It selects resolvers by exact `(HTTP method, request.url.path)`.
That does not match a route-template key such as `/api/worlds/{world_id}` to a
concrete request path such as `/api/worlds/world-a`; each later resolver
must be registered for the actual path shape using an explicit matcher or
route-aware lookup. Until that boundary is resolved and reviewed, do not add
hosted routes to the map. Client-selected World IDs remain consistency checks,
never resource authority. The `DMB_HOSTED_WORLD_ACCESS_JSON` subject mapping
is not this action-grant model and must not be translated into owner or
all-action grants.

For route activation, derive the World from the requested resource using
server-owned registry/resource state, compare it to any client selector, then
check the action against the trusted DMS principal subject. Stateful jobs,
worker callbacks, provider-input assembly, persistence, polling, and result
retrieval must repeat the relevant permission check so revocation takes
effect during a long-running operation. Session/account revocation behavior
remains a separate DMS integration concern.

Before hosted pilot activation, an operator must verify the retained World
record and select the exact owner subject through an authorized assignment
process. No owner or guest grant is presumed here.

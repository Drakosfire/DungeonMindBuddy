# [IDEA] Campaign-scoped Recap Contributor

**Captured:** 2026-11-14  
**Status:** Unscheduled product idea. Not an implementation handoff.

The player who already writes session recaps should be able to sign in, browse approved recaps, draft one, and run extraction without seeing GM worldbuilding. The GM reviews the proposed Events and relationships and publishes to the same World graph. The two users share approved recaps and claims, not unrestricted access.

## Smallest pilot

- Reuse DungeonMind sign-in and Buddy's hosted request boundary. Add one owner-approved, revocable grant in the existing World catalog, bound to the verified account, World, and campaign. Give the contributor a direct Recaps link, not broad World actions or access to Graph or Build. Resolve source, draft, and run scope on the server; check current grant and ownership through launch and result recovery.
- Reuse Build recap extraction's saved revision, content digest, and idempotent launch. Use only the contributor's draft as source input: no GM session supplements, private identity matching, or raw run diagnostics. Return the draft's candidate Events and relationships for correction and submission, not a canonical write.
- Keep GM review, private identity resolution, and canonical publication on the existing path. Canonical recap admission is GM-only today. Add explicit player-safe sharing for approved source revisions and reopen citations with the grant's campaign and player audience. Do not broaden old source visibility or expose private claims when the same entity is visible to both people.

## Dogfood proof before inviting anyone

Use a disposable campaign and two accounts. Seed a known character with a private fact. A contributor submits a draft mentioning that character and runs extraction; assert the fact is absent from actual model input and contributor responses. Approve the recap as GM, then verify both accounts see the same approved Event and reopen the same exact shared citation, without revealing private edges or references. Deny foreign draft/run reads and check that a revoked contributor cannot recover an in-flight run's results. Replaying the submission must not start a second extraction or advance the graph twice.

Prove shared source admission, exact player citation reopening, and canonical publication together before building a fuller editor. No new auth provider, general shared World browser, direct contributor publication, or bulk changes to existing recaps.

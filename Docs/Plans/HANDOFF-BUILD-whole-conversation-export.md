# BUILD: whole retained conversation export

PRIME activates this bounded UI slice from db3926ada in the existing Buddy checkout,
branch codex/whole-conversation-export. Topology: parallel-independent with held
#1792 (backend routing metadata, no overlapping writes or behavior dependency).
#1764 stays parked. External diagnostic permission holds remain in force.

Settle predecessor #1794: independently approved e90041250, merged/UI db3926ada;
API aa2c10157 unchanged.22 component and8 focused integration/activity checks plus
actual tsc/Vite passed. Protected UI adoption preserved3425 APP rows, native data,
27 frozen components and89 product files. Ordinary reload retained saved page,
table, Origin and newer unsent composer; terminal light trace opened and closed.
Running animation and previous-attempt visibility still need ordinary dogfood;
mounted tests cover those behaviors. Its UI write lease is settled here.

Deliver menu export of the full selected retained conversation, not only mounted
history: readable Markdown and optional diagnostic JSON. Reuse authenticated
conversation library pagination (which includes every physical retry turn), name,
trace and exact prompt reads. Export current or archived conversation by pinned
World/conversation identity. No model calls, writes to history, active-pointer
changes, backend/public contract or compatibility execution path.

Traverse every page until exhausted; enforce decreasing cursor, distinct IDs and
sequences, complete retained count. Refuse a broken/failed transcript read rather
than download a silently partial transcript. After collecting the selected format’s data, repeat the full paginated transcript
read for both formats (after trace/prompt reads for diagnostics), refusing download if
any projected turn changed (completion does not update conversation metadata).
Recheck conversation metadata before download; reject changed ownership/count/
name/status metadata and explain retry.
Label the collection interval without implying an atomic cross-endpoint snapshot.
For diagnostics, include captured traces and bound exact prompt payloads when
available; explicitly record missing/failed captures and incomplete/running state.
Never treat observation as saved authored page content. Readable output includes
questions, reply text, retry grouping metadata and labels/source links for page
objects; full editable page objects are not promised by the transcript projection.

Use one reusable export control in conversation menu and archived library reader.
No work starts until click. Freeze selection for the operation; suppress download
and notices after unmount or selection/World change. Keep composer/drafts intact.
No arbitrary transcript cap, new polling owner or remote export/upload service.

Exclusive writes: this handoff; new agentInteraction/conversationExport.ts,
conversationExport.test.ts, ConversationExport.tsx, ConversationExport.test.tsx;
WorldPlanAgentConversation.tsx and ConversationLibrary.tsx; their existing mounted
integration tests only as needed. Reuse existing API contracts unchanged.

Verify >50-turn multi-page transcript including earlier failed attempts; cursor,
identity, missing-page/read failure and scope retirement; no trace reads for
readable export; bound prompt capture and explicit diagnostic gaps. Verify actual
menu/library mounting and download through ordinary controls without sending a
message. Actual tsc/build, exact cumulative independent Bugbot review and PRIME
merge precede protected UI-only delivery and retained-state verification.

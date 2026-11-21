# COMBAT Play preview statblocks

ACTIVE under the Old Bath House goal. Serial successor to merged #4319.
Base 199755f7f96fa25f7de164f7d9ad40f544f683e0, branch
codex/combat-play-preview-statblocks, isolated fc67 checkout. No hosted
writes or shared runtime. Current open PR file census found no overlap
on RunSceneEncounter, runEncountersApi or session_encounters.

Own the Play encounter preview service, client and owning tests. Show
the distinct exact saved mechanics snapshots from the session's captured
template before starting. Reuse Combat's statblock viewer and its saved
portrait bindings. Include snapshots only in the preview response. The
existing template pin already covers them, and retained Start request
digests must remain valid across rollout. Respect existing session/World
admission and avoid producer reads or encounter writes on inspection.

Verify one captured revision after subsequent Plan template edits, actor
copies with shared mechanics, no writes before Start, and exact optional
response handling for old servers. Run isolated Play/Combat persistence
contracts, exact frontend verification and discovered comparison, then
request independent review. Conversation proposals and portrait binding
remain required in the Old Bath House goal.

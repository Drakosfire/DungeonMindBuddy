# Play history pagination test

ACTIVE: user requested diagnostic repairs and Trace deployment. Serial branch `codex/frontend-play-history-pagination`, based on `origin/main` at `f56991887`, follows #4813. Scope: the shared conversation Play pagination integration case and this brief.

The current transcript paginates the lightweight active-messages endpoint. Supply valid exclusive-cursor pages to that endpoint rather than an overlapping legacy full-history fixture. Preserve scroll anchoring, order/no duplication, cursor exhaustion, and exact World/cursor checks; assert no eager full-history read. Verify the affected case, clean exact-SHA hosted and independent review; next integrated full discovery includes this slice.

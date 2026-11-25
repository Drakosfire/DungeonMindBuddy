# ONBOARD: open the guest adventure source in Build

Status: ACTIVE under the owner's one-shot goal and review, merge, and deployment authority. Serial slice based on serving revision ddff9805036faa54ec9060cad17657f8c968ebde; branch codex/sizzek-prepared-guest-adventure. Scope: Build workspace document controller, focused tests, and this handoff. No live database or service lease for implementation. Existing guest Build serving PRs #4696 and #4693 were inspected; this slice only selects an already seeded document in the existing UI.

Outcome: a fresh guest entering bare Build opens the released Sizzek's Apprentice source in the normal editor. An explicit destination and signed-in entry retain their existing behavior. This depends on the already deployed guest source bundle and is one independent part of the wider goal; prepared Plan, Play, Combat, Home, Graph verification, and reset acceptance remain required.

Verify the focused controller behavior for guest default, explicit destination, and signed-in bare entry; review the exact cumulative diff and request independent review. Recheck the production serving parent before integrating and deploying. Verify the deployed editor and document picker in a fresh guest session after release.

# ONBOARD: carry the guest Graph to serving

Status: ACTIVE. The owner authorized merge and deployment. This serial serving
slice carries the reviewed guest product Graph from Buddy main PR #4579 (merge
`42a524ade2e48c8a1a8c354b0b56d86f48b99a72`) onto the merged Build serving
lineage at `6bd01431b3ec373815bfbf7742749059a548199e` (PR #4581). The current
live image was still at parent `a23847ff03d5b49525119d47ab927882c445e136` when
this branch was created. Recheck the live image and active release ownership
before activation; do not overwrite another deployment.

Scope: carry exactly the guest Graph behavior and its tests, plus this handoff
and truthful predecessor sync. The published guest copy is read-only in the
actual Graph; create/connect/reset there and access to Build, Plan and Play are
successor slices. No production database or public-copy mutation is included.

Verify the cumulative serving diff against `6bd01431b3ec373815bfbf7742749059a548199e`,
exact-SHA hosted and discovered frontend evidence against the serving baseline,
independent Bugbot review, and a production image built from that exact SHA.
Use the existing targeted engine deployment procedure, preserving and verifying
rollback and coordinating against the live image under its locks. Check the
anonymous home and Graph, private-route isolation, desktop and mobile, and
signed-in access after deployment. Retain inherited failures and report their
limits; a red discovered suite is not full release qualification.

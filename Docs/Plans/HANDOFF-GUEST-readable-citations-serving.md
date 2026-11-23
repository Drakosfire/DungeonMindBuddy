# Guest citation previews: serving integration

Status: ACTIVE. User authorized merge and deployment. Parent product PR #4521 merged to main as f0caef2d9246b32ccdde07382979a3bebaaef283. This serial integration is based on serving branch 8e6bf45f3cd65b37648e6d5ee6553c61bae64b5c, whose deployed image has schema 20261123_0200. Cherry-pick the reviewed product change and keep its runtime files identical to main.

Scope: the guest citation preview frontend files and tests carried from #4521, its handoff, and this integration handoff. Exclude migrations, API, released data, model behavior, and authentication. Existing 0200 reader remains compatible for image rollback; do not roll back to a pre-0200 image.

Validation: exact-head hosted frontend, full discovered failure-identity comparison to serving base, Bugbot review, and image-only cutover preserving the guest flags. Verify the published guest copy, private endpoint denial, and rendered citation previews on desktop/mobile after deployment. Record inherited diagnostic failures without claiming a green suite.

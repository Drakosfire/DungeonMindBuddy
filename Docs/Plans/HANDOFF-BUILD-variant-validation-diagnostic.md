# Build statblock review validation diagnostic

ACTIVE. Alan authorized fixing and verifying ordinary signed-in statblock variant review for Old Bath House. This serial backend slice uses `codex/build-variant-validation-diagnostic` from `75aefc7fa217b9422ee56731e5036177b458af42` in the existing isolated Combat checkout.

Write lease covers this brief, `apps/live_control_server/services/conversation_variant_save.py` and `tests/test_statblock_definition_validation.py`. No schema, frontend, writer policy or hosted data changes. The statblock owner remains the validation authority.

The hosted Old Bath House candidate matched the validator's logged digest, but the conversation retained only Markdown. The current client suppresses integration errors before review creation. Record controlled failure categories without candidate text, receipts, credentials, identifiers or exception messages. Preserve exact receipt binding and rejection behavior. Verify with a provider-free transport failure and a valid receipt. Hosted verification remains a separate operator-mediated step.

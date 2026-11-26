# Jev gateway identity

Status: ACTIVE, serial successor to pending-retry PR #4829. Base:
`codex/build-placement-app0213-base` at `5951192ed4694d713da2c5e73c74cc8d4b82b239`.
The goal authorizes the provider correction, focused local verification,
review, merge and deployment.

The retained failed Build turn shows Vercel rejected `jev-1.14.0` as an
unknown model. A minimal independent Vercel TypeSafe request for
`typesafe-ai/jev-1.14.0` succeeded. New Build and shared retrieval dispatches
must authorize and send that exact model. Stored older records retain their
original identity; request and response replay checks must use the model
bound to their original policy and authorization, not the current default.
Never rewrite stored evidence, normalize provider responses, weaken identity
checks or add a fallback route.

This change spans the common Build/Plan/Play decision codecs because they
share retrieval and proof validation; splitting the new wire from its owner
checks would make ordinary dispatch fail. Review the new dispatch identity,
the historical binding and each affected continuation together. Verify the
provider wire and retained model mismatch rejection, the pending Build retry,
and the affected Graph, image, prose and Plan/Play boundaries. Record any
unproven old-identity persisted continuations explicitly. Keep primary data
and the working conversation unchanged.

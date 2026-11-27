# CI: serving restricted-role migration fixture

ACTIVE under the user's release-repair instruction. Serial successor to serving candidate caf73b129697376a6d2db78db6b0b62d024757fb; this isolated slice owns only `tests/application_state/test_authored_pages_postgres.py` and this brief. The already-migrated serving database includes the 0211 schema change and a branched predecessor history. Stamping only 0198 falsely causes Alembic to replay the sibling table-creation branch and later schema-changing migrations with a deliberately restricted role.

Start the test from the actual already-installed 0211 schema boundary, run the subsequent 0212/0213 reader-only migrations with unchanged restricted grants, and assert the exact final head. This proves existing-schema startup and version-table updates, not restricted-role DDL. Preserve all permission checks; make no schema or production grants change. Verify in disposable PostgreSQL, exact-head hosting, and independent review.

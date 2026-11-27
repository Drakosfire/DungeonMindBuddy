# Setext heading corpus diagnostic repair

ACTIVE: user requested frontend diagnostic repair and Trace deployment. Serial test-only slice `codex/frontend-setext-corpus`, based on `origin/main` at `9437e0ebd598ac1c0ed911a819cee99472d158ab`, follows merged #4773. Scope: `markdownIngressCorpus.test.ts` and this brief.

The settled Setext source-recovery contract admits level-one and level-two Setext headings and preserves semantics using canonical ATX export. The corpus still lists those same inputs as adversarial and expects a blocking diagnostic. Move both existing cases into the supported corpus, which checks clean import, serialization safety, and reimported model equality; do not delete coverage, change the parser, or relax any other adversarial case.

Run the complete Markdown corpus and existing Setext roundtrip tests, exact-head hosted and discovered diagnostics, comparison with the prior integrated baseline, and independent exact-head review. Other frontend failures remain later serial slices.

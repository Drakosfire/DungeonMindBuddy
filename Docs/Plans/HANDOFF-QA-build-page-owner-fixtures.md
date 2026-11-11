# QA: verify proposal guards against the Page owner

ACTIVE serial test-only slice from 168d19f983d08e388f8735b426e56ba829eefbbb.
The retained writer replay work merged in #2391. Its comparison uses a frozen
offline plan and has no write dependency on this slice. #2390 landed Build
interaction changes without touching the two proposal test modules below.

The proposal tests create database-owned Pages. File reads now fail before
they can check committed Page invariants, and a file write cannot simulate
author revision drift. Use the existing Page read and save fixtures at those
sites and retain the same scope, CAS, retry and content assertions.

Write lease covers this handoff, the merged QA predecessor handoff, and
tests/test_build_proposal_review.py and tests/test_build_insertion_tool.py.
Verify both suites locally with mocked model transports and disposable
PostgreSQL databases, then obtain independent exact-head review. No
product behavior, provider dispatch or primary database writes.

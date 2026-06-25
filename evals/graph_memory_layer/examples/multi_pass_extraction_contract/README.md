# Multi-pass extraction contract fixture

This directory contains the contract-only Graph Memory multi-pass extraction specification for Session 23.

It defines the required pass order, pass output schemas, evidence-alignment requirements, Candidate Graph Preview assembly gates, and future gold-comparison report shape. It does not call an LLM, execute extraction, produce extractor output, write graph memory, approve writes, execute graph queries, scan or mutate corpus, connect `/plan`, or connect Agent Interaction.

Files:

- `multi_pass_extraction_contract.json` — top-level contract manifest.
- `session_23_contract_fixture.json` — static pass contract definitions.
- `session_23_expected_pass_outline.json` — Session 23 scoring checklist.
- `session_23_gold_comparison_contract.json` — future comparison/report contract.

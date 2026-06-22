# Recap-Ingestion Explicit Real-Artifact Dogfood Fixture

This directory contains one manually curated real-derived dogfood artifact bundle for eval-only Graph Memory recap-ingestion checks.

All inputs are admitted through `dogfood_manifest.json` with explicit relative file paths only. The loader must not scan this directory, glob files, discover files by naming convention, scan corpus files, mutate corpus files, connect `/plan`, connect Agent Interaction, perform retrieval, infer entities, resolve aliases, infer relationships, promote facts, or promote canon.

The fixture input files may contain dogfood text, but reports and projection payloads must not copy full raw file contents.

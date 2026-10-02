# HERMES synthetic co-GM prose pairs — REVIEW

Authority: the operator's provisional Hermes-tuning program, with PRIME controlling bounded leases, independent review, and merge. The worker-phase experiment closed at Buddy main `364dc98534208c3fc2f40dad0f3e3f80da032377`; this slice was pinned at `origin/main@6de8d831ab82308086677fb3038122936ab9a756` and rebased onto `origin/main@c3904bc1e08df689b92d5a0b710b546f77af4600` before final review. It grants no permanent steward mandate and changes no product inference policy.

## One question

Does one concise voice instruction make the same GPT-6 Luna Hermes conversation-only answers more useful and pleasant for co-GM planning while preserving grounding and uncertainty? Compare current request behavior against the same request plus the existing fixed sentence in `evals/hermes_tuning/scenario.json`: “Write as a calm, practical co-GM: direct, warm, and specific; avoid generic dramatic flourishes.” Do not change the product system prompt, runtime, model, provider, tool policy, or source authority in this slice.

Use 12 fully synthetic evidence/question cases, one matched pair per case through the same in-process Hermes route with fresh session IDs. Keep base facts, question, task constraints, model, policy and system prompt equal within a pair; record hashes and verify the only input difference is the fixed voice sentence. Alternate or seeded-randomize arm order and preserve the seed. No direct-API comparison arm is needed. Capture raw answers, wall/provider-call timings, calls/tools, token usage and estimated cost. Non-streaming output leaves TTFT unknown.

For each answer, apply deterministic length/format gates and evidence-keyed factual/uncertainty/actionability gates. A failed hard gate cannot win on voice. Prepare a label-blinded packet with evidence, question, answer key and paired outputs in randomized order; PRIME and an independent reviewer score grounded passing answers for task fit, clarity, natural co-GM voice and concision using anchored 1–5 scales, plus A/B/tie preference. Store scores before unblinding. Report paired wins/ties/losses and descriptive score/cost/latency differences, with all failures and raw outputs. Twelve pairs are exploratory and cannot establish a general or production quality improvement. If one arm wins, a separate runtime handoff is needed before adopting a product prompt change.

## Lease and gates

Owner: provisional Hermes-tuning subagent. Branch `codex/hermes-prose-pairs`, rebased from the pinned revision onto `origin/main@c3904bc1e08df689b92d5a0b710b546f77af4600` in the isolated Hermes worktree. Exclusive repository write set: this handoff; new `evals/hermes_tuning/run_style_pairs.py`; new `evals/hermes_tuning/style_cases.json`; `evals/hermes_tuning/README.md`; new `tests/test_hermes_tuning_style_pairs.py`; and one final synthetic result artifact under `evals/hermes_tuning/artifacts/`. A transient blinded packet was written under `/tmp` and omitted arm mapping and credentials. No other repository file was edited. At final collision check, open PRs #844/#843/#842, paused #826, and unrelated backlog/UI/Rules lanes did not touch the lease. Product runtime, Graph service, personal corpus and database remain unchanged.


## Execution result

One 12-pair synthetic cohort completed on `openai-api` / `gpt-6-luna`: 24 successful turns, one observed model call per turn, zero tool events, 21,344 total tokens, and $0.0045904 estimated cost. The first-two-pair check-in was sent before the remaining ten calls. Raw answers are in `evals/hermes_tuning/artifacts/style-pairs-20261002T085003Z.json` and were preserved unchanged during score joins.

The deterministic uncertainty-marker screen rejected both `council-bell` answers, so its actual pass count was 22/24, not 23/24. Both locked blind reviews independently adjudicated both council answers as preserving uncertainty; record this as a lexical false negative without rewriting raw gate fields. Both reviewers also identified unsupported facts in the control answers for `northfield-well` and `gloam-orchard`, leaving ten pairs where both answers passed human hard gates.

After blind scoring was locked, arm mapping was joined by exact answer text. PRIME's preferences across ten eligible pairs were control 4, voice-sentence 5, tie 1. The independent reviewer's were control 4, voice-sentence 6, tie 0. Mean natural co-GM voice scores were 4.2/4.2 (PRIME) and 4.0/3.9 (independent) for control/voice sentence; results are mixed and do not establish a quality improvement. The artifact records SHA-256 `c25badfd47ec695d22a92ad689632edd70cc56c98dab0e4f522e7e4a79188e4e` for PRIME's locked blind scores and `09d310ddc897fc11b57d2f6697d16ccc6f71a01c59a3e9d6f454e093ed135762` for the independent reviewer. Non-streaming output leaves TTFT unknown. No private C2 packet or live Graph was used.

Offline tests: `uv run pytest -q tests/test_hermes_tuning_style_pairs.py` (3 passed); Ruff check and format checks passed. PR link and exact pushed head will be recorded after the draft PR is opened. Do not merge; PRIME owns review and merge decisions.

During the provider run, Hermes emitted plugin-registration compatibility warnings and asynchronous `FileNotFoundError` logging traces as generated temporary Hermes home directories were cleaned up. All 24 typed turn results and observed calls succeeded; timings remain descriptive and may include setup/logging work. The artifact records this limitation without raw logger output.

# HERMES synthetic co-GM prose pairs — COMPLETE

## Authority

PRIME merged Buddy PR [#850](https://github.com/Drakosfire/DungeonMindBuddy/pull/850) at exact merge commit `84a853ae9c95117d91ed5a634bbdce9c565da00d`. The experiment branch was based on pinned `origin/main@6de8d831ab82308086677fb3038122936ab9a756` and rebased onto `origin/main@c3904bc1e08df689b92d5a0b710b546f77af4600` before review. The implementation changed no product runtime, model policy, Graph service, personal corpus, or database.

## Experiment

The experiment asked whether one concise co-GM voice sentence improves GPT-6 Luna Hermes conversation-only answers while preserving grounding and uncertainty. It compared twelve fully synthetic matched cases through the same Hermes route with fresh sessions. The only within-pair input change was the sentence already present in `evals/hermes_tuning/scenario.json`: “Write as a calm, practical co-GM: direct, warm, and specific; avoid generic dramatic flourishes.” System prompt hashes matched within pairs; arm order was seeded and recorded. No direct API arm or Graph tool was used.

## Results

The final raw artifact is `evals/hermes_tuning/artifacts/style-pairs-20261002T085003Z.json`. All 24 turns returned `ok`, each had one observed model call and zero tool events, with 21,344 total tokens and $0.0045904 estimated cost. The run emitted Hermes plugin-registration compatibility warnings and asynchronous `FileNotFoundError` logging traces while generated temporary Hermes home directories were cleaned up; all typed turn results and observed calls still succeeded. Timings remain descriptive and may include setup/logging work.

The deterministic uncertainty-marker screen passed 22/24 answers. It rejected both `council-bell` answers, though both blinded reviewers independently judged that they preserved uncertainty; this was a lexical false negative, and the original gate values remain unchanged. Both reviewers independently found unsupported claims in the control answer for `northfield-well` (resident attribution) and the voice-sentence answer for `gloam-orchard` (an unaffected comparison row). Those two pairs were excluded, leaving ten eligible pairs where both answers passed human hard gates.

After reviewers locked their ratings, each blinded answer was mapped to exactly one raw arm by its unchanged answer hash. PRIME's control/voice/tie preferences across ten eligible pairs were 4/5/1; the independent reviewer's were 4/6/0. Mean natural co-GM voice scores were 4.2/4.2 for PRIME and 4.0/3.9 for the independent reviewer (control/voice sentence). The results are mixed and do not establish a quality improvement. The artifact preserves both locked score hashes, case-level mappings, recomputed summaries, and raw answers.

## Verification and limits

The bounded verification passed: `uv run pytest -q tests/test_hermes_tuning_style_pairs.py` (4 tests), Ruff check, Ruff format check, and cumulative diff check. The regression test verifies each blind-answer hash maps to exactly one raw arm, checks the Northfield and Gloam rejected-arm attribution, and recomputes both reviewers' eligible-pair tallies and means.

This twelve-pair synthetic result is exploratory; it does not establish general prose quality or justify a product prompt change. Non-streaming responses leave TTFT unknown. No private C2 evidence, personal corpus, live Graph, or provider reroute was used.

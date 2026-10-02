> Research note, moved from `~/Documents/` on 2026-10-01. Its model, price, and provider claims are dated hypotheses, not adopted Buddy policy; reverify them before use.

# Tuning Hermes for DungeonMindBuddy

**My recommendation is to keep Hermes, expose its existing tuning controls through Buddy, and evaluate “good co-GM prose” as a product capability—not just a personality prompt.** Keep the current Luna route as the control, test Sonnet 5.5 as the prose challenger, and test Gemini 3.8 Flash and Haiku 4.5 for responsiveness.

The biggest finding is that **Buddy’s embedded Hermes is substantially different from a normal Hermes installation**. Some popular advice is already implemented; other advice would have no effect because Buddy deliberately isolates its configuration.

I reviewed the user stories, current design decisions and demo roadmap, Buddy’s adapter and model policy, and the pinned upstream Hermes implementation at repository snapshot `012ff01…`. The external research covered official Hermes and provider documentation, upstream issue reports, and firsthand writing-workflow reports. I did not run paid model comparisons or change the repository.

## 1. What the repository says we should optimize

### The target is a useful co-GM, not an autonomous research assistant

The campaign-authoring stories describe an agent that selects meaningful developments, investigates threats, collaborates on drafts, asks only consequential questions, and promotes knowledge only through deliberate confirmation. Evidence should support the interaction without overwhelming the answer.

I would translate those stories into these tuning targets:

| Story | What a good response does | What tuning must not sacrifice |
|---|---|---|
| “What changed in the latest recap?” | Selects the few developments that change pressure, stakes, or preparation. | Distinguishes no change, missing evidence, and failed retrieval. |
| “Tell me about this threat.” | Connects relevant facts and relationships instead of dumping records. | Distinguishes established facts, interpretations, and unknowns. |
| “What does Lysandra know?” | Answers about her knowledge, not everything the system knows. | Does not infer personal awareness merely from world facts. |
| “Help develop this statblock.” | Moves toward a useful draft with minimal interruption. | Uses the typed generation/validation path; does not turn improvised mechanics into authoritative rules. |
| “Make this part of the world.” | Presents a reviewable change and a clear confirmation. | Keeps drafting, confirmation, and durable publication separate. |
| “Work with this Plan.” | Uses the correct saved document or explicitly selected draft. | Never confuses committed content, unsaved edits, conversation, and graph knowledge. |

The Lysandra example is explicitly developed in the context-compilation decision. The saved-versus-unsaved Plan distinction is also exercised in the latest demo witness. These should become evaluation cases, not merely prompt instructions.

### Four implementation findings materially change the advice

**First: the checked-in Agent model is already `gpt-6-luna`.** `MODEL_POLICY.json` maps `hermes_graph_agent` to `agent_conversation`, which resolves to Luna. Older reports describing Codex are not the current policy; the environment override can still change the effective model.

**Second: OpenRouter is not selectable through the reviewed product resolver.** It requires `OPENAI_API_KEY` and returns OpenAI’s endpoint and provider identity. Adding an OpenRouter key or changing `~/.hermes/config.yaml` will not reroute these Buddy turns. That needs an intentional adapter/model-policy change.

**Third: the usual “disable unnecessary Hermes stuff” advice is largely already applied.** Buddy constructs Hermes with `skip_memory=True`, `skip_context_files=True`, an isolated profile, restricted toolsets, and runtime tool whitelisting. Do not undo those boundaries to obtain personality, memory, or convenience features.

**Fourth: the pinned Hermes already exposes useful controls that Buddy does not explicitly pass.** Its constructor supports `reasoning_config`, `max_tokens`, `max_iterations`, provider-routing controls, `request_overrides`, and `stream_delta_callback`. This is an adapter-extension opportunity before it is an upstream-upgrade project. The dependency remains pinned to `861d69c7…`, with an exact OpenAI SDK dependency.

There is also an important capability boundary: the October 1 roadmap records successful saved-Plan Ask behavior, but the connected native-graph successor remains separately gated. **A model cannot be prompted into using graph context that its current product route does not supply.** That must not be diagnosed as a prose or intelligence problem.

## 2. What the user reports actually teach us

The most useful reports explain mechanisms. “Model X feels fast” is much weaker evidence than a request dump showing unnecessary input, an extra recovery call, or buffered streaming.

| Firsthand report | Evidence and limitations | Lesson for Buddy |
|---|---|---|
| **Fixed prompt overhead, April 1** | A Hermes 0.6.0 user inspected six requests and reported roughly 13,935 fixed tokens: tool definitions plus system/skills content. This was a broad messaging deployment, not Buddy’s restricted adapter. | Measure the complete outgoing request. Do **not** assume Buddy has this same overhead—or can recover the same savings. [GitHub](https://github.com/NousResearch/hermes-agent/issues/4379) |
| **Extra post-tool recovery round** | An upstream report reproduced structured-reasoning handling that caused an unnecessary model round trip, estimated at 3–5 seconds and about 400 tokens, on particular Qwen/OpenRouter combinations and historical Hermes versions. | Count recovery/nudge calls. A fast model with one unnecessary retry can lose to a slower, compatible model. [GitHub](https://github.com/NousResearch/hermes-agent/issues/34655) |
| **Buffered “streaming,” September 23** | A Copilot-ACP report showed responses being collected and replayed only after completion. Its minutes-long results involved another transport and substantial additional context. | Verify that tokens reach Buddy’s UI while generation is occurring. A streaming flag or animated response replay is not sufficient. This does **not** establish that Buddy has the same bug. [GitHub](https://github.com/NousResearch/hermes-agent/issues/120550) |
| **Worse prose through Hermes than direct chat** | A storytelling user reported awkward grammar and word choice through Hermes, despite better direct-chat output from the same model; adding a style file helped little. No controlled comparison was provided. | Compare the same evidence and request through a minimal API call and through Hermes. Investigate prompt composition before blaming the underlying writer. [Reddit](https://www.reddit.com/r/hermesagent/comments/1vefa3b/interactive_story_telling/) |

My synthesis is:

> **The first tuning target should be unnecessary work and conflicting context—not a longer prompt demanding intelligence, creativity, or thoroughness.**

That aligns with Anthropic’s engineering guidance to curate the whole model context—tools, history, instructions, and retrieved material—rather than treating the system prompt as the only control surface. [Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

## 3. The highest-value speed improvements

### A. Give routine questions a genuinely short execution path

Buddy’s graph policy already says that a retrieval session arrives with deterministic candidates and accepted claims; Hermes should expand only when needed. It also explicitly permits accepted graph facts without reading their source again, reserving source reads for quotations, exact details, conflicts, or required verification.

I would turn that policy into observable behavior:

**When the supplied evidence answers the question, answer from it.** Do not require a graph call merely to demonstrate activity.

**When a relationship is missing, retrieve that relationship.** Prefer the existing bounded neighborhood operation over a sequence of individually discovering every connected entity.

**When evidence remains insufficient, stop honestly.** Do not repeatedly search slight variations to avoid saying that something is unknown.

For evaluation, I would initially target one model call for already-supported simple questions, and a small number of additional calls for genuine investigation. Those are experimental targets, not universal caps: broad threat investigations should not be forced into the budget of a name lookup.

I would **not** add a mandatory planner, critic, prose editor, or “humanizer” call to every turn. Each would need to demonstrate a quality improvement worth its additional serial latency.

Independent read operations can be candidates for batching, but only after confirming that Buddy’s retrieval-session handling is safe for concurrency and every read remains pinned to the same authorized revision.

### B. Set reasoning effort explicitly, by task

For the first experiment, I would use **low effort for routine conversation and short grounded synthesis**, then compare medium effort on multi-entity interpretation and difficult investigations.

This is especially important for Sonnet 5.5: Anthropic recommends low or medium for latency-sensitive chat and warns that effort levels are recalibrated relative to Sonnet 5. A familiar setting name does not imply a familiar amount of computation. [Claude Platform](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)

Two implementation traps matter:

**Hiding reasoning is not disabling it.** OpenRouter’s `reasoning.exclude` only removes it from the returned response; those tokens remain billed.

**A small output cap can consume the entire allowance on reasoning.** On most providers, reasoning and visible output share the completion budget. A cap chosen for a 150-word answer can therefore produce an empty or truncated answer rather than a quick one. Validate supported reasoning settings per model, and leave room for both reasoning and the final response. [OpenRouter](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)

My proposed starting profiles—not existing Buddy configuration—would be:

| Profile | Initial behavior to test |
|---|---|
| **Quick answer** | Low/minimal supported reasoning; direct answer; roughly 60–150 words unless the question needs less. |
| **Campaign sensemaking** | Low versus medium experiment; two or three paragraphs; select consequential developments. |
| **Investigation** | More retrieval and reasoning permitted; scope set by the actual question, not a universal “be exhaustive” instruction. |
| **Authored material** | Length and voice determined by the requested artifact; preserve draft/validation boundaries. |

These should not require another user-facing mode picker or an extra classification-model call on every request.

### C. Wire real answer streaming through the product boundary

The pinned Hermes provides `stream_delta_callback`; Buddy’s reviewed constructor supplies tool callbacks and API-observation hooks, but not that callback. That is a specific seam to investigate.

The desired path is:

```text
Provider answer delta
  → Hermes adapter
  → typed AgentRuntime event
  → server transport
  → visible text in the existing Agent surface
```

Measure **time to first useful visible text**, separately from time to a status message and time to completion.

Stream answer content, not internal reasoning. Keep evidence/provenance receipts separate. Where output requires validation before display or application, preserve that requirement rather than exposing unvalidated structured changes.

### D. Implement the context-compilation direction already in the repo

The October 1 context decision is unusually well aligned with this problem: smallest sufficient semantic context, explicit query references first, deterministic product-state resolution, deduplication, and bounded expansion rather than campaign-wide preloading. It is a design direction, not proof that every part is implemented.

I would prioritize:

**Remove irrelevant material before aggressively abbreviating relevant material.** The current Scene should not consume most of the prompt when the question is about an unrelated named NPC.

**Render semantic meaning rather than internal bookkeeping.** Keep revision identities, authority checks, and diagnostics in the application. Include identifiers in model context where the model actually needs them for a tool argument.

**Bound tool responses as well as initial context.** A small opening prompt followed by several huge tool results is not a small-context interaction.

**Keep continuity distinct from evidence.** A conversation summary may preserve the user’s intent, selected draft, and unresolved question. It must not become an alternative campaign database.

Importantly, the current tool contract requires `retrievalSessionId`. Token optimization does not authorize deleting required fields; hiding those from the model would require a deliberate server-bound tool-contract change.

### E. Preserve reusable prompt prefixes and measure caching

I would organize the model input conceptually as:

```text
Stable Buddy authority/capability policy
Stable, compact voice instructions
Stable tool definitions
──────────────────────────────────────
Turn-specific scope and evidence
Relevant current work
Necessary conversation continuity
Current question
```

That creates a reusable prefix without pretending that current evidence is static.

OpenRouter documents cache-aware sticky routing, cache-read/write usage fields, and an explicit `session_id` option for workflows whose opening messages change. Manual provider ordering overrides its normal sticky behavior, so provider pinning and caching need to be evaluated together. [OpenRouter](https://openrouter.ai/docs/guides/best-practices/prompt-caching)

I would not assume that Buddy’s Hermes session identifier is automatically sent as OpenRouter’s session identifier. Verify the outgoing request.

Nor would I pad short prompts to reach cache thresholds. Cache savings are useful only when they exceed additional input and cache-write costs. Prefix caching also does not make old graph evidence current; scope, visibility, revision, and document identity still need their normal validation.

### F. Measure initialization and queueing without removing isolation

Buddy’s wrapper performs plugin rediscovery and manipulates process-global import/profile state under a lock. Its own documentation warns that it is process-exclusive rather than a generally safe multi-tenant in-process runtime.

Measure lock wait, worker initialization, plugin discovery, retrieval, provider latency, and rendering separately. Reuse safe worker-level initialization where justified, but **do not “optimize” by removing the lock or sharing mutable profiles across conversations**.

## 4. Improving prose without creating prettier hallucinations

### The existing prose policy is a good starting point

Buddy already asks for co-GM sensemaking, two or three short paragraphs on recap-change questions, consequential developments rather than encounter replay, and evidence diagnostics outside the frontstage answer. It also bans several kinds of report scaffolding and unsolicited follow-up menus.

I would preserve that direction. The next improvement should be **examples, evaluation, and task-sensitive voice**, not another layer of personality instructions.

### Use a small set of approved examples

Anthropic’s current prompting guidance specifically recommends relevant, diverse examples to steer tone, structure, and consistency. [Claude Platform](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

For Buddy, I would curate examples of:

- A compelling recap-change answer.
- A direct factual answer that stops when finished.
- An investigation that identifies a meaningful uncertainty.
- A proposed creative addition clearly separated from established lore.
- Read-aloud prose that sounds different from advice to the GM.

Keep the complete collection in the evaluation suite. Experiment with a compact subset in the prompt rather than shipping every example on every turn.

Use synthetic or appropriately scoped examples, clearly marked as examples—not stray campaign facts that could contaminate an answer.

### Separate co-GM voice from in-world prose

I would define two output contracts.

**Co-GM voice:** clear, selective, conversational, comfortable with causal interpretation, and precise about uncertainty. It should help you decide what matters.

**Authored prose:** appropriate to the requested block—read-aloud description, NPC speech, encounter introduction, or other material. It may invent when invention is explicitly the task, but remains a proposal until accepted.

Here is the kind of compact voice instruction I would test alongside—not instead of—the existing authority policy:

> Write to the GM as a capable co-GM. Answer the actual question first. Prefer concrete developments and their consequences over an inventory of facts. Distinguish established events from interpretations and proposed additions in ordinary language. For recap-change questions, select the developments that materially change the situation and explain why they matter. Do not add atmosphere merely to sound creative. When asked for authored prose, write the requested material rather than explaining how to write it. Ask a question only when its answer would materially change the result.

An illustrative example, **not campaign canon**:

**Less useful**

> Available evidence establishes damage to the gate. There is insufficient evidence regarding Lysandra’s awareness of this development.

**More useful**

> We know the gate is damaged, but not whether Lysandra has heard. For prep, the useful question is who tells her—and what she can do once she knows.

The second response adds usefulness without claiming an unsupported event occurred.

### Treat temperature as a secondary experiment

I would leave sampling at supported vendor defaults during the first model and prompt comparison. Then vary it separately on authored-prose cases.

I would not use high temperature as the primary creativity intervention, or low temperature as a substitute for grounding. The first question is whether the model is receiving the right evidence, a clear task, and a usable example of the desired voice.

Also avoid importing old prompt tricks blindly. For example, current Claude documentation says assistant prefills are unsupported on newer model families; a historical “start the assistant response for it” technique can become a transport error rather than a prose improvement. [Claude Platform](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

### Test a separate writer only for the cases that justify it

A two-stage approach is worth testing for substantial authored material:

```text
Grounded interpretation / evidence packet
  → prose generation using only that packet and the requested creative brief
```

But I would not make it the default for ordinary conversation. It introduces another call and another opportunity to embellish or lose a qualification.

The acceptance question is: **does the separate writer produce enough additional usable prose to justify its latency and fidelity risk?**

## 5. How I would use the OpenRouter account

### Start with a small, purposeful model comparison

These are candidates for testing, not a claim that one has already won your workload.

Prices below are the standard input/output rates displayed on October 1, 2026, per million tokens; cache and other charges are separate.

| Model | Role in the experiment | Input / output |
|---|---|---:|
| **GPT-6 Luna** — `openai/gpt-6-luna` | Current-model control. Test direct OpenAI versus OpenRouter separately from testing other models. | **$0.10 / $0.50**. [OpenRouter](https://openrouter.ai/openai/gpt-6-luna) |
| **Claude Sonnet 5.5** — `anthropic/claude-sonnet-5.5` | My first prose-and-synthesis challenger, starting at low effort. Its advertised writing improvements are a reason to test, not proof of better co-GM output. | **$2 / $10**. [OpenRouter](https://openrouter.ai/anthropic/claude-sonnet-5.5) |
| **Gemini 3.8 Flash** — `google/gemini-3.8-flash` | Responsiveness/throughput challenger for everyday questions and synthesis. | **$0.75 / $3.75**, currently a **50% promotion** against $1.50 / $7.50. [OpenRouter](https://openrouter.ai/google/gemini-3.8-flash) |
| **Claude Haiku 4.5** — `anthropic/claude-haiku-4.5` | Older-generation, low-latency comparison, including a non-thinking configuration where appropriate. | **$1 / $5**. [OpenRouter](https://openrouter.ai/anthropic/claude-haiku-4.5) |

Sonnet 5.5 was released on **September 28**, only three days before this report. That makes compatibility and task-specific evaluation particularly important; it does not yet deserve an automatic production promotion. [OpenRouter](https://openrouter.ai/anthropic/claude-sonnet-5.5)

My provisional expectation is that Sonnet is the most interesting prose challenger, while Luna may remain difficult to displace on cost and acceptable short-answer quality. That is a hypothesis to test.

### Route for the kind of speed you need

Hermes distinguishes:

**`latency`**: prioritize time to first token.

**`throughput`**: prioritize output tokens per second.

Those are different objectives. I would begin with latency routing for interactive Agent conversation and compare throughput routing for longer authored output. `require_parameters=True` is also valuable because it excludes providers that do not support requested controls. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing)

A useful **outgoing OpenRouter request fragment** would look like this:

```json
{
  "model": "anthropic/claude-sonnet-5.5",
  "stream": true,
  "reasoning": {
    "effort": "low"
  },
  "provider": {
    "sort": "latency",
    "require_parameters": true,
    "data_collection": "deny",
    "allow_fallbacks": true
  }
}
```

This is **not a drop-in Buddy configuration**. The adapter must deliberately resolve the OpenRouter credential and endpoint, translate the chosen profile, and demonstrate that these fields reach the provider request. Hermes documents its routing controls and their mapping to the OpenRouter provider object. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing)

For private campaign content, review retention as well as training restrictions. OpenRouter offers a separate `zdr` control for restricting requests to zero-data-retention endpoints; it is not synonymous with `data_collection: "deny"`. Privacy filtering may reduce the available provider pool. [OpenRouter](https://openrouter.ai/blog/insights/zero-data-retention/?utm_source=chatgpt.com)

During controlled tests, fix the model and endpoint when possible. During normal operation, allow only compatible, approved fallbacks and record which endpoint actually served the request. Do not silently change the writer model and then attribute the resulting prose difference to a prompt change.

Finally, any auxiliary model calls need their own routing/privacy review; Hermes documents auxiliary-task routing separately from main-agent routing. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing)

## 6. The experiment I would actually run

### First isolate the harness from the writer

The most revealing initial comparison is:

> **Same model, same evidence, same user request, and equivalent generation settings: minimal API call versus embedded Hermes.**

Do this with fixed evidence packets before involving variable retrieval.

If minimal API output is consistently better, inspect Hermes’s actual assembled prompt, tool definitions, history, and recovery behavior. If both are weak, work on model selection and the output contract.

Then run the same candidates through real retrieval. This prevents a prose comparison from accidentally becoming a comparison of different evidence.

### Build the evaluation set from the stories

Start with a small screening cohort, then expand the finalists into a multi-turn suite. I would include these cases:

| Case | Required behavior |
|---|---|
| Latest recap with several developments | Select meaningful changes without replaying every beat. |
| Latest recap with no relevant change | Say no relevant change—not “I could not retrieve it.” |
| Missing or unreadable evidence | State the limitation without inventing a substitute. |
| NPC knowledge question | Separate world truth from that NPC’s demonstrated knowledge. |
| Threat investigation | Connect relationships and expose consequential gaps. |
| Request for a creative addition | Produce a useful proposal without silently canonizing it. |
| Saved Plan versus dirty editor draft | Use only the authorized content basis for that operation. |
| Promotion and subsequent retrieval | Preserve confirmation and verify the resulting authoritative state. |
| Conversation or document switch during a turn | Reject stale completion/application targets. |

The saved-Plan witness already supplies a useful regression pattern: the answer used a saved “seven rings at dusk” fact and excluded an unsaved “nine rings at dawn” edit. Preserve that kind of exact test while changing providers or prompts.

### Score prose and speed separately, with hard correctness gates

I would judge prose through blinded pairwise comparison: which answer would you rather receive during actual preparation or play?

The rubric should ask whether the response answers first, selects important information, explains consequences, sounds natural, respects uncertainty, and contains material you can use without rewriting. Do not reward extra length by default.

For speed and cost, record:

| Measurement | Why it matters |
|---|---|
| First useful visible text and total completion time | Separates responsiveness from total work. |
| Model calls, tool calls, and recovery calls | Exposes unnecessary agent-loop work. |
| Input, cached-input, output, and reasoning tokens | Shows what is consuming the budget. |
| Actual provider, model, API mode, and fallback | Makes comparisons reproducible. |
| Retrieval, initialization, lock wait, and rendering time | Distinguishes model latency from application latency. |
| Grounding failures, truncated output, and invalid tool calls | Prevents “fast but broken” from winning. |

Buddy already has request-scoped model-observation hooks and tool-event timing. Extend that existing trace path rather than introducing another disconnected monitoring mechanism. Preserve its distinction between structural telemetry and separately governed raw forensic logging.

Unknown reasoning usage must remain **unknown**, not zero. Preserve provider-required reasoning/tool-continuation structures internally when changing transports; OpenRouter specifically documents this requirement for reasoning models using tools. [OpenRouter](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)

### Implement in this order

| Priority | Change | Acceptance evidence |
|---|---|---|
| **1** | Add a Buddy-owned inference profile covering provider, model, effort, routing, budgets, and supported transport settings. | Tests prove the effective outgoing configuration and fail closed on invalid combinations. Other model-policy actions remain unchanged. |
| **2** | Establish baseline traces and verify end-to-end streaming. | Measured first-useful-text timing; no buffered replay masquerading as streaming. |
| **3** | Add the prose examples and story-derived evaluation set. | Blind comparison against the current policy, including uncertainty and draft/canon cases. |
| **4** | Compare Luna, Sonnet, Flash, and Haiku under controlled conditions. | Better prose or latency without weakening hard correctness gates. |
| **5** | Reduce redundant retrieval, context, and initialization work. | Fewer calls/tokens or lower latency with equivalent evidence and behavior. |
| **6** | Consider a separate writer, more elaborate routing, or a Hermes upgrade. | A demonstrated need that the simpler configuration does not meet. |

I would leave weight fine-tuning, autonomous skill accumulation, and harness migration outside this first effort. There are too many directly exposed, currently untested controls to justify those as the opening move.

## Bottom line

**The best next version of this agent is not “Hermes, but more agentic.” It is Hermes doing less unnecessary work, receiving a better-selected evidence packet, and writing to a tested co-GM standard.**

Your repository already has the right conceptual ingredients: shared behavioral policy, restricted tools, deterministic context preparation, explicit authority boundaries, and tracing. The immediate work is to make inference choices explicit, connect the available controls, and use your actual stories to decide which combinations are worth keeping—not to adopt somebody else’s impressive-looking Hermes configuration wholesale.

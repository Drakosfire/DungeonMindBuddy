from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from src.llm.api_client import DungeonMindApiClient

_SYNTHESIS_PROFILE_ENV = "DMB_SYNTHESIS_PROFILE"
_SYNTHESIS_VERBOSITY_ENV = "DMB_SYNTHESIS_VERBOSITY"
_TWO_STEP_SYNTHESIS_ENV = "DMB_TWO_STEP_SYNTHESIS"
_CITATION_STRUCTURE_ENV = "DMB_SYNTHESIS_CITATION_STRUCTURE"

EXTRACTION_PROMPT = """You are a factual extraction assistant.
Given a block of campaign context, extract every distinct factual claim as a numbered bullet list.
Include entity names, specific details, exact phrases, and terminal outcomes.
Do NOT answer any question. Do NOT summarize. Just list facts.
Output ONLY the numbered list."""

_CITATION_APPENDIX = """
Answer structure:
1. TL;DR: (1-2 sentences)
2. Evidence: bullet list of grounded facts from context, each citing the entity name
3. Analysis: (optional) only if facts conflict or require interpretation

Rule: Every claim in TL;DR must have a corresponding Evidence bullet. Do not state anything without a grounded source.
""".strip()

SYSTEM_PROMPT = """You are a Game Master's assistant for a tabletop RPG campaign.

Answer the GM's question using ONLY the facts provided in the projection context below.
When facts come from different truth states, distinguish them:
- CANON: established world truth
- PREP: GM planning notes (may not have happened yet)
- OBSERVED: what actually happened in play

If facts conflict on the same attribute, explain which version is current and why.
Do not invent information beyond what is stated in the projection.
If the projection doesn't contain enough to answer, say so explicitly.

Start with a "TL;DR:" line (1-2 sentences) that directly answers the GM's question.
Cite entity names when referencing facts.
Aim for 100-200 words. Exceed only when the projection contains conflicting truth
states that require explanation.

Terminal outcome rule: when the projection contains phrases describing a terminal
outcome (death, destruction, condition resolution — e.g. "killing blow",
"decapitated", "oily sheen in eyes fades", "secret passage revealed"),
you MUST include those exact phrases verbatim in your answer. Do not paraphrase
terminal outcomes; the GM needs the canonical phrasing for session continuity.

Output contract for snapshot-style answers:
- Include a "Key Attributes" section.
- If notable attributes (history, geography, demographics, economy, defenses) are
  present in the projection, list them briefly.
- Do not enumerate attributes that are absent from the context.
"""

SYSTEM_PROMPT_WIKI = """You are a Game Master's assistant for a tabletop RPG campaign.

Answer the GM's question using ONLY the facts provided in the context below. The context may
include LLM-authored wiki articles for important entities and structured attribute listings for others.
When facts come from different truth states, distinguish them:
- CANON: established world truth
- PREP: GM planning notes (may not have happened yet)
- OBSERVED: what actually happened in play

If facts conflict on the same attribute, explain which version is current and why.
Do not invent information beyond what is stated in the context.
If the context doesn't contain enough to answer, say so explicitly.

Start with a "TL;DR:" line (1-2 sentences) that directly answers the GM's question.
Cite entity names when referencing facts.
Aim for 100-200 words. Exceed only when the context contains conflicting truth
states that require explanation.

Terminal outcome rule: when the context contains phrases describing a terminal
outcome (death, destruction, condition resolution — e.g. "killing blow",
"decapitated", "oily sheen in eyes fades", "secret passage revealed"),
you MUST include those exact phrases verbatim in your answer. Do not paraphrase
terminal outcomes; the GM needs the canonical phrasing for session continuity.

Some entities have full wiki articles; others use structured attribute lines. Use both.
Do not require a separate "Key Attributes" section when the wiki article already covers attributes in prose.
"""

_PROFILE_APPENDIX = {
    "mirathorn": """
Corpus profile: Mirathorn campaign notes and recaps.
- Preserve corpus-specific names and phrases exactly when present.
- Expand acronyms on first mention when expansion is explicit in context.
- For hazard/encounter questions, enumerate all grounded hazards in concise bullets.
""".strip(),
}


def _resolve_synthesis_profile(value: str | None) -> str:
    resolved = (value or os.getenv(_SYNTHESIS_PROFILE_ENV, "")).strip().lower()
    return resolved


def _resolve_verbosity(value: str | None) -> str:
    resolved = (value or os.getenv(_SYNTHESIS_VERBOSITY_ENV, "default")).strip().lower()
    if resolved not in {"default", "compact", "verbose"}:
        return "default"
    return resolved


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _resolved_system_prompt(
    profile: str,
    verbosity: str,
    *,
    citation_structure: bool = False,
    wiki_mode: bool = False,
) -> str:
    base = SYSTEM_PROMPT_WIKI if wiki_mode else SYSTEM_PROMPT
    parts = [base]
    appendix = _PROFILE_APPENDIX.get(profile, "")
    if appendix:
        parts.append(appendix)
    if verbosity == "compact":
        parts.append("Verbosity mode: compact. Keep answer concise (80-140 words) while preserving required exact phrases.")
    elif verbosity == "verbose":
        parts.append("Verbosity mode: verbose. Provide fuller detail (180-320 words), explicitly covering each grounded subpoint.")
    if citation_structure:
        parts.append(_CITATION_APPENDIX)
    return "\n\n".join(part for part in parts if part.strip())


def _resolve_model(model: str | None) -> str:
    if model:
        return model

    policy_candidates = [
        Path(__file__).resolve().parents[2] / "MODEL_POLICY.json",
        Path(__file__).resolve().parents[3] / "MODEL_POLICY.json",
    ]
    for policy_path in policy_candidates:
        if policy_path.exists():
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            role = policy.get("actions", {}).get("retrieval_synthesis", "retrieval_synthesis")
            return policy.get("models", {}).get(role, "gpt-5.3-chat-latest")
    return "gpt-5.3-chat-latest"


def _load_api_key() -> str | None:
    project_root = Path(__file__).resolve().parents[2]
    env_candidates = [
        project_root / ".env.development",
        project_root.parents[0] / ".env.development",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            try:
                load_dotenv(env_file, override=True)
            except OSError:
                continue
    return os.getenv("OPENAI_API_KEY")


def _extract_response_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for chunk in content:
                text = getattr(chunk, "text", None)
                if text:
                    parts.append(str(text))
                elif isinstance(chunk, dict) and chunk.get("text"):
                    parts.append(str(chunk["text"]))
            return "\n".join(parts).strip()
    except Exception:
        pass
    return ""


async def synthesize_answer_async(
    formatted_context: str,
    question: str,
    *,
    model: str | None = None,
    openai_client: Any | None = None,
    synthesis_profile: str | None = None,
    verbosity: str | None = None,
    two_step: bool | None = None,
    citation_structure: bool | None = None,
    synthesis_meta_out: dict[str, Any] | None = None,
    wiki_mode: bool | None = None,
) -> str:
    """Send projection context + question to LLM asynchronously."""
    model_id = _resolve_model(model)

    client = openai_client
    is_async_client = False
    if client is None:
        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for synthesis.")
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("OpenAI SDK is required for synthesis.") from exc
        client = AsyncOpenAI(api_key=api_key)
        is_async_client = True
    api_client = DungeonMindApiClient.wrap(client)

    profile = _resolve_synthesis_profile(synthesis_profile)
    verbosity_mode = _resolve_verbosity(verbosity)
    use_two = (
        bool(two_step)
        if two_step is not None
        else _env_truthy(_TWO_STEP_SYNTHESIS_ENV)
    )
    use_cite = (
        bool(citation_structure)
        if citation_structure is not None
        else _env_truthy(_CITATION_STRUCTURE_ENV)
    )
    use_wiki = (
        bool(wiki_mode)
        if wiki_mode is not None
        else _env_truthy("DMB_USE_WIKI")
    )
    resolved_prompt = _resolved_system_prompt(
        profile,
        verbosity_mode,
        citation_structure=use_cite,
        wiki_mode=use_wiki,
    )

    if use_two:
        ext_kwargs = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Campaign context:\n"
                        f"{formatted_context}\n\n"
                        "Extract all factual claims as instructed."
                    ),
                },
            ],
        }
        if is_async_client:
            ext_resp = (await api_client.chat_completions_create_async(action="synthesis.extract_claims", **ext_kwargs)).response
        else:
            ext_resp = api_client.chat_completions_create(action="synthesis.extract_claims", **ext_kwargs).response
        extracted = _extract_response_text(ext_resp)
        if not extracted:
            raise RuntimeError("Extraction step returned an empty response.")
        if synthesis_meta_out is not None:
            synthesis_meta_out["two_step"] = True
            synthesis_meta_out["extracted_claims"] = extracted
        user_prompt = (
            "Extracted factual claims from the campaign context (numbered list):\n"
            f"{extracted}\n\n"
            f"GM question:\n{question}\n\n"
            "Answer using ONLY these extracted claims; if they contradict, say so. "
            "Follow the output contract from the system prompt exactly."
        )
    else:
        if synthesis_meta_out is not None:
            synthesis_meta_out["two_step"] = False
        ctx_label = "Campaign context (wiki articles and/or structured projection)" if use_wiki else "Projection context"
        user_prompt = (
            f"{ctx_label}:\n{formatted_context}\n\n"
            f"GM question:\n{question}\n\n"
            "Return a grounded answer based only on the context above. "
            "Follow the output contract from the system prompt exactly."
        )

    answer_kwargs = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": resolved_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if is_async_client:
        response = (await api_client.chat_completions_create_async(action="synthesis.answer", **answer_kwargs)).response
    else:
        response = api_client.chat_completions_create(action="synthesis.answer", **answer_kwargs).response
    text = _extract_response_text(response)
    if not text:
        raise RuntimeError("Synthesis model returned an empty response.")
    return text


def synthesize_answer(
    formatted_context: str,
    question: str,
    *,
    model: str | None = None,
    openai_client: Any | None = None,
    synthesis_profile: str | None = None,
    verbosity: str | None = None,
    two_step: bool | None = None,
    citation_structure: bool | None = None,
    synthesis_meta_out: dict[str, Any] | None = None,
    wiki_mode: bool | None = None,
) -> str:
    """Send projection context + question to LLM, return grounded prose."""
    return asyncio.run(
        synthesize_answer_async(
            formatted_context,
            question,
            model=model,
            openai_client=openai_client,
            synthesis_profile=synthesis_profile,
            verbosity=verbosity,
            two_step=two_step,
            citation_structure=citation_structure,
            synthesis_meta_out=synthesis_meta_out,
            wiki_mode=wiki_mode,
        )
    )

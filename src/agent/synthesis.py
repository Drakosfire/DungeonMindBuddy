from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

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
            load_dotenv(env_file, override=True)
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

    user_prompt = (
        f"Projection context:\n{formatted_context}\n\n"
        f"GM question:\n{question}\n\n"
        "Return a grounded answer based only on the projection context. "
        "Follow the output contract from the system prompt exactly."
    )
    payload = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    response = await payload if is_async_client else payload
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
) -> str:
    """Send projection context + question to LLM, return grounded prose."""
    return asyncio.run(
        synthesize_answer_async(
            formatted_context,
            question,
            model=model,
            openai_client=openai_client,
        )
    )

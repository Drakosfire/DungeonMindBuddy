"""Synthesis agent helpers for projection-driven QA."""

from src.agent.context_formatter import format_projection_context
from src.agent.synthesis import SYSTEM_PROMPT, synthesize_answer

__all__ = ["format_projection_context", "SYSTEM_PROMPT", "synthesize_answer"]

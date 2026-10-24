"""Prepared, offline accounting dependency for Buddy's ordinary Jev factory."""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path

from application_state.agent_conversation.rules_authority_policy import rules_capability

from .build_jev_accounting import ExperimentalAccounting
from .build_jev_harness import BuildJevHarness

ASSET_ENV = "DUNGEONBUDDY_JEV_TOKENIZER_FILE"
ASSET_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
TOKENIZER_VERSION = "0.14.0"
# MIT License
#
# Copyright (c) 2022 OpenAI, Shantanu Jain
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# o200k_base configuration from tiktoken_ext.openai_public (tiktoken 0.14.0).
# Construct its public Encoding directly: get_encoding/load helpers can fetch
# assets and write a temporary cache. Neither behavior belongs in a turn.
PATTERN = "|".join(
    [
        r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
        r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
        r"\p{N}{1,3}",
        r" ?[^\s\p{L}\p{N}]+[\r\n/]*",
        r"\s*[\r\n]+",
        r"\s+(?!\S)",
        r"\s+",
    ]
)
SPECIAL_TOKENS = {"<|endoftext|>": 199999, "<|endofprompt|>": 200018}


class BuildJevRuntimeUnavailable(ValueError):
    """Fixed capability error, never include filesystem or credential content."""


def load_offline_accounting(path: Path) -> ExperimentalAccounting:
    import tiktoken

    if version("tiktoken") != TOKENIZER_VERSION:
        raise BuildJevRuntimeUnavailable("tokenizer_dependency_version")
    if not path.is_absolute():
        raise BuildJevRuntimeUnavailable("tokenizer_asset_path")
    # Read a bounded snapshot once; no file/cache access is used by the counter.
    with path.open("rb") as stream:
        data = stream.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != ASSET_SHA256:
        raise BuildJevRuntimeUnavailable("tokenizer_asset_digest")
    ranks = {
        base64.b64decode(token, validate=True): int(rank)
        for token, rank in (line.split() for line in data.splitlines() if line)
    }
    encoding = tiktoken.Encoding(
        name="o200k_base",
        pat_str=PATTERN,
        mergeable_ranks=ranks,
        special_tokens=SPECIAL_TOKENS,
    )
    counter = ExperimentalAccounting(
        TOKENIZER_VERSION,
        lambda text: len(encoding.encode(text, disallowed_special=())),
    )
    counter.estimate({"preparation": "🐐 café 中文 <|endoftext|>"})
    return counter


@dataclass(frozen=True)
class PreparedBuildJevRuntime:
    accounting: ExperimentalAccounting | None = field(default=None, repr=False)
    unavailable_reason: str | None = "tokenizer_not_prepared"

    def create(self) -> BuildJevHarness:
        if self.accounting is None:
            raise BuildJevRuntimeUnavailable(
                self.unavailable_reason or "tokenizer_not_prepared"
            )
        return BuildJevHarness(
            world_context=True,
            named_citations=True,
            accounting=self.accounting, rules_capability=rules_capability(graph=True)
        )


def prepare_default_build_runtime() -> PreparedBuildJevRuntime:
    """Called once by each API lifespan; unavailable capability leaves API usable."""
    configured = os.environ.get(ASSET_ENV, "").strip()
    if not configured:
        return PreparedBuildJevRuntime(
            unavailable_reason="tokenizer_asset_unconfigured"
        )
    try:
        accounting = load_offline_accounting(Path(configured))
    except BuildJevRuntimeUnavailable as exc:
        return PreparedBuildJevRuntime(unavailable_reason=str(exc))
    except OSError:
        return PreparedBuildJevRuntime(unavailable_reason="tokenizer_asset_unreadable")
    except (ImportError, ValueError):
        return PreparedBuildJevRuntime(
            unavailable_reason="tokenizer_dependency_unavailable"
        )
    return PreparedBuildJevRuntime(accounting=accounting, unavailable_reason=None)
